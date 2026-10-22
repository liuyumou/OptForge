//! Leased ADR-0040 sparse products. Host bounds and certification retain authority.
#![allow(missing_docs)]
use optimizer_cuda_sys::{
    Argument as A, Context, DeviceBuffer, LaunchConfig, Module, Stream, launch,
};
use optimizer_lp::quant::{Format, Operator, Oracle as ProductOracle, Promotion};
use std::{path::PathBuf, rc::Rc};
fn device(e: impl std::fmt::Display) -> String {
    format!("device:{e}")
}
pub fn code_object_path() -> PathBuf {
    crate::tuned::code_object_path().with_file_name("lp_pdhg_quant.cubin")
}
#[derive(Clone, Debug, Default)]
pub struct Counters {
    pub launches: u64,
    pub upload_bytes: u64,
    pub readback_bytes: u64,
    pub peak_bytes: u64,
}
pub struct Oracle<'o> {
    op: &'o Operator,
    module: Module,
    stream: Stream,
    original: DeviceBuffer<f64>,
    codes: DeviceBuffer<u8>,
    line: DeviceBuffer<u32>,
    group: DeviceBuffer<u32>,
    tiles: DeviceBuffer<u32>,
    ids: DeviceBuffer<u32>,
    inputs: DeviceBuffer<u32>,
    exponents: DeviceBuffer<i32>,
    promoted: DeviceBuffer<u32>,
    vector: DeviceBuffer<f64>,
    output: DeviceBuffer<f64>,
    guards: DeviceBuffer<u32>,
    mask: Vec<bool>,
    pub counters: Counters,
}
impl<'o> Oracle<'o> {
    pub fn new(
        context: Rc<Context>,
        op: &'o Operator,
        image: &[u8],
        cap: u64,
    ) -> Result<Self, String> {
        let _cost = optimizer_core::lp_cost::scope("quant_device_prepare");
        if std::env::var("AI_OPTIMIZER_GPU_LEASE").ok().as_deref() != Some("inherited") {
            return Err("shared host lease required".into());
        }
        if (
            context.device().capability_major,
            context.device().capability_minor,
        ) != (12, 0)
        {
            return Err("quant_requires_sm120".into());
        }
        let mut line = vec![0u32];
        let mut group = vec![0u32];
        let (mut tiles, mut ids, mut inputs) = (vec![], vec![], vec![]);
        for (t, lines) in [(false, &op.row_groups), (true, &op.column_groups)] {
            for gs in lines {
                for g in gs {
                    tiles.push(g.tile as u32);
                    for &id in &g.ids {
                        ids.push(id as u32);
                        inputs.push(if t { op.row_of[id] } else { op.column_of[id] } as u32);
                    }
                    group.push(ids.len() as u32);
                }
                line.push(tiles.len() as u32);
            }
        }
        let codes = if op.settings.format == Format::Fp16 {
            op.codes
                .iter()
                .flat_map(|c| c.to_le_bytes())
                .collect::<Vec<_>>()
        } else {
            op.codes.iter().map(|&c| c as u8).collect()
        };
        let exponents = op.tiles.iter().map(|t| t.exponent).collect::<Vec<_>>();
        let size = op.rows.max(op.columns).max(1);
        let bytes = (op.values.len().max(1) * 8
            + codes.len().max(1)
            + (line.len()
                + group.len()
                + tiles.len().max(1)
                + ids.len().max(1)
                + inputs.len().max(1)
                + 2 * op.tiles.len().max(1))
                * 4
            + size * 20) as u64;
        if bytes > cap || cap > 1 << 30 || bytes > context.memory_info().map_err(device)?.0 {
            return Err("device_memory_limit".into());
        }
        let module = context.load_module(image).map_err(device)?;
        let stream = context.stream().map_err(device)?;
        fn upload<T: Copy + Default>(
            c: &Rc<Context>,
            s: &Stream,
            v: &[T],
        ) -> Result<DeviceBuffer<T>, String> {
            let zero = [T::default()];
            let v = if v.is_empty() { &zero } else { v };
            let mut b = c.allocate(v.len()).map_err(device)?;
            b.copy_from(v, s).map_err(device)?;
            Ok(b)
        }
        Ok(Self {
            op,
            original: upload(&context, &stream, &op.values)?,
            codes: upload(&context, &stream, &codes)?,
            line: upload(&context, &stream, &line)?,
            group: upload(&context, &stream, &group)?,
            tiles: upload(&context, &stream, &tiles)?,
            ids: upload(&context, &stream, &ids)?,
            inputs: upload(&context, &stream, &inputs)?,
            exponents: upload(&context, &stream, &exponents)?,
            promoted: upload(&context, &stream, &vec![0u32; op.tiles.len()])?,
            vector: upload(&context, &stream, &vec![0.; size])?,
            output: upload(&context, &stream, &vec![0.; size])?,
            guards: upload(&context, &stream, &vec![0; size])?,
            mask: vec![],
            counters: Counters {
                peak_bytes: bytes,
                upload_bytes: bytes,
                ..Counters::default()
            },
            module,
            stream,
        })
    }
}
impl ProductOracle for Oracle<'_> {
    fn product(
        &mut self,
        op: &Operator,
        state: &Promotion,
        t: bool,
        v: &[f64],
    ) -> Result<Vec<f64>, String> {
        let _cost = optimizer_core::lp_cost::scope("quant_device_product_transfer");
        if !std::ptr::eq(self.op, op) {
            return Err("stale_operator".into());
        }
        state.validate(op)?;
        if v.len() != if t { op.rows } else { op.columns } {
            return Err("vector_shape".into());
        }
        let count = if t { op.columns } else { op.rows };
        if count == 0 {
            return Ok(vec![]);
        }
        if self.mask != state.mask {
            let mut p = state.mask.iter().map(|&x| u32::from(x)).collect::<Vec<_>>();
            if p.is_empty() {
                p.push(0);
            }
            self.promoted.copy_from(&p, &self.stream).map_err(device)?;
            self.counters.upload_bytes += (p.len() * 4) as u64;
            self.mask = state.mask.clone();
        }
        let mut input = vec![0.; op.rows.max(op.columns).max(1)];
        input[..v.len()].copy_from_slice(v);
        self.vector
            .copy_from(&input, &self.stream)
            .map_err(device)?;
        self.counters.upload_bytes += (input.len() * 8) as u64;
        let ptr = |x| A::DevicePtr(x);
        launch(
            &self.module.function("quant_product").map_err(device)?,
            LaunchConfig {
                grid: (count as u32).div_ceil(8),
                block: 256,
                shared_memory: 0,
            },
            &[
                ptr(self.original.as_device_ptr()),
                ptr(self.codes.as_device_ptr()),
                ptr(self.line.as_device_ptr()),
                ptr(self.group.as_device_ptr()),
                ptr(self.tiles.as_device_ptr()),
                ptr(self.ids.as_device_ptr()),
                ptr(self.inputs.as_device_ptr()),
                ptr(self.exponents.as_device_ptr()),
                ptr(self.promoted.as_device_ptr()),
                ptr(self.vector.as_device_ptr()),
                ptr(self.output.as_device_ptr()),
                ptr(self.guards.as_device_ptr()),
                A::U32(count as u32),
                A::U32(if t { op.rows as u32 } else { 0 }),
                A::U32(match op.settings.format {
                    Format::Fp16 => 0,
                    Format::E4m3 => 1,
                    Format::E5m2 => 2,
                    Format::Fp64 => 3,
                }),
            ],
            &self.stream,
        )
        .map_err(device)?;
        self.counters.launches += 1;
        let mut output = vec![0.; input.len()];
        let mut guards = vec![0; input.len()];
        self.output
            .copy_to(&mut output, &self.stream)
            .map_err(device)?;
        self.guards
            .copy_to(&mut guards, &self.stream)
            .map_err(device)?;
        self.counters.readback_bytes += (output.len() * 12) as u64;
        if guards[..count].iter().any(|&x| x != 0) {
            return Err("product_range_guard".into());
        }
        output.truncate(count);
        Ok(output)
    }
}
