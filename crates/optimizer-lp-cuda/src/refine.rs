//! ADR-0037 leased sparse products; all numerical authority remains on the host.
#![allow(missing_docs)]
use optimizer_cuda_sys::{
    Argument as A, Context, DeviceBuffer, DeviceError, LaunchConfig, Module, Stream, launch,
};
use optimizer_lp::refine::{InnerOperator, ProductOracle, ProductWidth};
use serde_like::Counters;
use std::{path::PathBuf, rc::Rc};
// Local plain fields avoid extending any historical diagnostic wire type.
mod serde_like {
    #[derive(Clone, Debug, Default, PartialEq, Eq)]
    pub struct Counters {
        pub phases_ns: std::collections::BTreeMap<String, u64>,
        pub launches: u64,
        pub upload_bytes: u64,
        pub readback_bytes: u64,
        pub allocations: u64,
        pub peak_bytes: u64,
        pub synchronizations: u64,
    }
}
pub fn code_object_path() -> PathBuf {
    crate::tuned::code_object_path().with_file_name("lp_pdhg_refine.cubin")
}
fn device(e: DeviceError) -> String {
    format!("device:{e}")
}
struct Resident {
    module: Module,
    stream: Stream,
    coefficients: DeviceBuffer<f64>,
    coefficients32: DeviceBuffer<f32>,
    fp32_admitted: bool,
    diagonal: DeviceBuffer<f64>,
    ro: DeviceBuffer<u32>,
    ri: DeviceBuffer<u32>,
    co: DeviceBuffer<u32>,
    ci: DeviceBuffer<u32>,
    perm: DeviceBuffer<u32>,
    input: DeviceBuffer<f64>,
    output: DeviceBuffer<f64>,
    guards: DeviceBuffer<u32>,
    generation: String,
}
pub struct Oracle {
    context: Rc<Context>,
    image: Vec<u8>,
    resident: Option<Resident>,
    pub counters: Counters,
    cap: u64,
}
impl Oracle {
    pub fn new(context: Rc<Context>, image: Vec<u8>, cap: u64) -> Result<Self, String> {
        if std::env::var("AI_OPTIMIZER_GPU_LEASE").ok().as_deref() != Some("inherited") {
            return Err("shared host lease required".into());
        }
        if (
            context.device().capability_major,
            context.device().capability_minor,
        ) != (12, 0)
        {
            return Err("refine_requires_sm120".into());
        }
        Ok(Self {
            context,
            image,
            resident: None,
            counters: Counters::default(),
            cap,
        })
    }
}
fn upload<T: Copy + Default>(
    context: &Rc<Context>,
    stream: &Stream,
    data: &[T],
    c: &mut Counters,
) -> Result<DeviceBuffer<T>, String> {
    let zero = [T::default()];
    let values = if data.is_empty() { &zero } else { data };
    let mut buffer = context.allocate(values.len()).map_err(device)?;
    buffer.copy_from(values, stream).map_err(device)?;
    c.allocations += 1;
    c.upload_bytes += std::mem::size_of_val(values) as u64;
    c.synchronizations += 1;
    Ok(buffer)
}
impl ProductOracle for Oracle {
    fn observe(&mut self, phase: &str, ns: u64) {
        *self.counters.phases_ns.entry(phase.into()).or_default() += ns;
    }
    fn bind(&mut self, op: &InnerOperator) -> Result<(), String> {
        if self
            .resident
            .as_ref()
            .is_some_and(|r| r.generation == op.generation())
        {
            return Ok(());
        }
        let fbytes = (op.coefficients().len().max(1) + op.rows().max(1) + 2 * op.columns().max(1))
            as u64
            * 8;
        let ibytes = (op.offsets().len().max(1)
            + op.indices().len().max(1)
            + op.column_offsets().len().max(1)
            + op.column_indices().len().max(1)
            + op.permutation().len().max(1)
            + op.columns().max(1)) as u64
            * 4;
        let bytes = fbytes
            .checked_add(ibytes)
            .and_then(|x| x.checked_add(op.coefficients().len().max(1) as u64 * 4))
            .ok_or("device_memory_overflow")?;
        if bytes > self.cap
            || bytes > 1 << 30
            || bytes > self.context.memory_info().map_err(device)?.0
        {
            return Err("device_memory_limit".into());
        }
        self.resident = None;
        let bind_start = std::time::Instant::now();
        let module = self.context.load_module(&self.image).map_err(device)?;
        let stream = self.context.stream().map_err(device)?;
        let c = &mut self.counters;
        let resident = Resident {
            coefficients: upload(&self.context, &stream, op.coefficients(), c)?,
            coefficients32: upload(
                &self.context,
                &stream,
                &op.coefficients()
                    .iter()
                    .map(|&a| a as f32)
                    .collect::<Vec<_>>(),
                c,
            )?,
            fp32_admitted: op
                .coefficients()
                .iter()
                .all(|&a| optimizer_lp::precision::narrow(a).is_ok()),
            diagonal: upload(&self.context, &stream, op.diagonal(), c)?,
            ro: upload(&self.context, &stream, op.offsets(), c)?,
            ri: upload(&self.context, &stream, op.indices(), c)?,
            co: upload(&self.context, &stream, op.column_offsets(), c)?,
            ci: upload(&self.context, &stream, op.column_indices(), c)?,
            perm: upload(&self.context, &stream, op.permutation(), c)?,
            input: upload(&self.context, &stream, &vec![0.0; op.columns().max(1)], c)?,
            output: upload(&self.context, &stream, &vec![0.0; op.columns().max(1)], c)?,
            guards: upload(&self.context, &stream, &vec![0_u32; op.columns().max(1)], c)?,
            generation: op.generation().clone(),
            module,
            stream,
        };
        c.peak_bytes = c.peak_bytes.max(bytes);
        self.resident = Some(resident);
        self.observe("device_bind", bind_start.elapsed().as_nanos() as u64);
        Ok(())
    }
    fn apply(
        &mut self,
        op: &InnerOperator,
        t: bool,
        input: &[f64],
        width: ProductWidth,
    ) -> Result<Vec<f64>, String> {
        let r = self.resident.as_mut().ok_or("unbound_operator")?;
        if r.generation != op.generation() {
            return Err("stale_generation".into());
        }
        if input.len() != if t { op.rows() } else { op.columns() } {
            return Err("vector_dimensions".into());
        }
        if width == ProductWidth::F32 && !r.fp32_admitted {
            return Err("conversion_lost_or_nonfinite".into());
        }
        let count = if t { op.columns() } else { op.rows() };
        if count == 0 {
            return Ok(vec![]);
        }
        let mut padded = vec![0.0; op.columns().max(1)];
        padded[..input.len()].copy_from_slice(input);
        let transfer_start = std::time::Instant::now();
        r.input.copy_from(&padded, &r.stream).map_err(device)?;
        self.counters.upload_bytes += (padded.len() * 8) as u64;
        self.counters.synchronizations += 1;
        *self
            .counters
            .phases_ns
            .entry("vector_upload".into())
            .or_default() += transfer_start.elapsed().as_nanos() as u64;
        let kernel_start = std::time::Instant::now();
        let ptr = |v: u64| A::DevicePtr(v);
        let (offset, indices) = if t { (&r.co, &r.ci) } else { (&r.ro, &r.ri) };
        launch(
            &r.module.function("refine_product").map_err(device)?,
            LaunchConfig {
                grid: (count as u32).div_ceil(8),
                block: 256,
                shared_memory: 0,
            },
            &[
                ptr(r.coefficients.as_device_ptr()),
                ptr(r.coefficients32.as_device_ptr()),
                ptr(offset.as_device_ptr()),
                ptr(indices.as_device_ptr()),
                ptr(r.perm.as_device_ptr()),
                ptr(r.diagonal.as_device_ptr()),
                ptr(r.input.as_device_ptr()),
                ptr(r.output.as_device_ptr()),
                ptr(r.guards.as_device_ptr()),
                A::U32(count as u32),
                A::U32(op.original_columns() as u32),
                A::U32(u32::from(t)),
                A::U32(u32::from(width == ProductWidth::F32)),
            ],
            &r.stream,
        )
        .map_err(device)?;
        self.counters.launches += 1;
        let mut output = vec![0.0; op.columns().max(1)];
        let mut guards = vec![0; op.columns().max(1)];
        r.output.copy_to(&mut output, &r.stream).map_err(device)?;
        r.guards.copy_to(&mut guards, &r.stream).map_err(device)?;
        self.counters.readback_bytes += (output.len() * 12) as u64;
        self.counters.synchronizations += 2;
        *self
            .counters
            .phases_ns
            .entry("kernel_and_readback".into())
            .or_default() += kernel_start.elapsed().as_nanos() as u64;
        if guards[..count].iter().any(|&x| x != 0) {
            return Err("product_range".into());
        }
        output.truncate(count);
        Ok(output)
    }
}
