//! ADR-0044 resident sparse products, guards, and FP64 updates under the lease.
#![allow(missing_docs)]
use optimizer_cuda_sys::{
    Argument as A, Context, DeviceBuffer, Function, LaunchConfig, Module, Stream, launch,
};
use optimizer_lp::{
    Engine,
    control::Fp64State,
    tensor_cost::{
        Counts, Format, Generation, Layout, Operator, Oracle as WindowOracle, Product, Window,
    },
};
use std::{collections::BTreeMap, path::PathBuf, rc::Rc, sync::Arc};
pub fn code_object_path() -> PathBuf {
    crate::tuned::code_object_path().with_file_name("lp_pdhg_tensor_cost.cubin")
}
fn device(e: impl std::fmt::Display) -> String {
    format!("device:{e}")
}
#[derive(Clone, Debug, Default)]
pub struct Counters {
    pub launches: u64,
    pub upload_bytes: u64,
    pub readback_bytes: u64,
    pub peak_bytes: u64,
    pub windows: u64,
    pub state_uploads: u64,
    pub reference_updates: u64,
    pub reference_launches: u64,
    pub reference_readback_bytes: u64,
    pub host_product_scans: u64,
    pub product_vector_transfers: u64,
}
#[allow(dead_code)]
pub struct Oracle<'o, 'm> {
    op: &'o Operator,
    stream: Stream,
    functions: BTreeMap<&'static str, Function<'m>>,
    reference_values: DeviceBuffer<f64>,
    reference_indices: DeviceBuffer<u32>,
    reference_offsets: DeviceBuffer<u32>,
    reference_bad: DeviceBuffer<u32>,
    pub host_audit: bool,
    original: DeviceBuffer<f64>,
    represented: DeviceBuffer<f64>,
    residual: DeviceBuffer<f64>,
    codes: DeviceBuffer<u8>,
    low_error: DeviceBuffer<f64>,
    native_error: DeviceBuffer<f64>,
    line: DeviceBuffer<u32>,
    group: DeviceBuffer<u32>,
    tiles: DeviceBuffer<u32>,
    ids: DeviceBuffer<u32>,
    inputs: DeviceBuffer<u32>,
    entries: DeviceBuffer<u32>,
    exponents: DeviceBuffer<i32>,
    promoted: DeviceBuffer<u32>,
    constants: DeviceBuffer<f64>,
    bounds: DeviceBuffer<f64>,
    scales: DeviceBuffer<f64>,
    packed_values: DeviceBuffer<f64>,
    vectors: Vec<DeviceBuffer<f64>>,
    invariant: Vec<DeviceBuffer<f64>>,
    norm: DeviceBuffer<f64>,
    control: DeviceBuffer<u32>,
    flags: DeviceBuffer<u32>,
    stats: DeviceBuffer<u64>,
    collected: DeviceBuffer<u64>,
    tq: DeviceBuffer<i64>,
    tx: DeviceBuffer<i64>,
    txe: DeviceBuffer<i32>,
    tae: DeviceBuffer<i32>,
    tr: DeviceBuffer<u32>,
    tc: DeviceBuffer<u32>,
    selected: DeviceBuffer<i32>,
    active: DeviceBuffer<u32>,
    parts: DeviceBuffer<f64>,
    part_flags: DeviceBuffer<u32>,
    twork: DeviceBuffer<u64>,
    tcollected: DeviceBuffer<u64>,
    loaded_generation: Option<Arc<()>>,
    loaded_restarts: Option<u64>,
    pub counters: Counters,
}
pub fn buffer_bytes(op: &Operator) -> Result<u64, String> {
    let n = op.rows.max(op.columns).max(1) as u128;
    let z = op.values.len().max(1) as u128;
    let l = (op.rows + op.columns).max(1) as u128;
    let scalar = 8 * (3 * z + op.ids.len().max(1) as u128 + 3 * l + 2 * l + 16 * n + 3)
        + 4 * (op.line.len()
            + op.group.len()
            + op.group_tiles.len().max(1)
            + op.ids.len().max(1)
            + op.inputs.len().max(1)
            + op.entries.len()
            + 2 * op.tiles.len().max(1)
            + 4
            + (op.rows + op.columns).max(1)) as u128
        + 8 * (7 * l + 11)
        + if op.values.is_empty() {
            1
        } else {
            z * op.settings.format.width() as u128
        };
    let nt = op.dense_exponents.len().max(1) as u128;
    let blocks = n.div_ceil(32);
    let tensor = 8 * op.dense.len().max(1) as u128
        + 8 * blocks * 32
        + 12 * blocks
        + 12 * nt
        + 4 * op.selected.len().max(1) as u128
        + 384 * nt
        + 16 * nt
        + 8;
    u64::try_from(scalar + tensor + 8 * z + 8 * blocks * 32 + 24 * z + 4 * l + 12)
        .map_err(|_| "device_memory_overflow".into())
}
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
impl<'o, 'm> Oracle<'o, 'm> {
    pub fn new(
        c: Rc<Context>,
        op: &'o Operator,
        module: &'m Module,
        cap: u64,
        e: &Engine<'_>,
    ) -> Result<Self, String> {
        let _cost = optimizer_core::lp_cost::scope("resident_device_prepare");
        if std::env::var("AI_OPTIMIZER_GPU_LEASE").ok().as_deref() != Some("inherited") {
            return Err("shared host lease required".into());
        }
        if (c.device().capability_major, c.device().capability_minor) != (12, 0) {
            return Err("resident_requires_sm120".into());
        }
        let bytes = buffer_bytes(op)?;
        if bytes > cap || cap > 1 << 30 || bytes > c.memory_info().map_err(device)?.0 {
            return Err("device_memory_limit".into());
        }
        if op
            .preparation_bytes
            .checked_add(bytes.checked_mul(2).ok_or("preparation_memory_overflow")?)
            .is_none_or(|v| v > 2 << 30)
        {
            return Err("preparation_memory_limit".into());
        }
        let stream = c.stream().map_err(device)?;
        let size = op.rows.max(op.columns).max(1);
        let lines = (op.rows + op.columns).max(1);
        let codes = if op.settings.format == Format::Fp16 {
            op.codes
                .iter()
                .flat_map(|v| v.to_le_bytes())
                .collect::<Vec<_>>()
        } else {
            op.codes.iter().map(|&v| v as u8).collect()
        };
        let exponents = op.tiles.iter().map(|t| t.exponent).collect::<Vec<_>>();
        let scales = op
            .row_scale
            .iter()
            .chain(&op.column_scale)
            .copied()
            .collect::<Vec<_>>();
        let values = op
            .ids
            .iter()
            .map(|&id| op.values[id as usize])
            .collect::<Vec<_>>();
        let vectors = (0..11)
            .map(|_| upload(&c, &stream, &vec![0.; size]))
            .collect::<Result<Vec<_>, _>>()?;
        let (xl, xu) = e.scaled_column_bounds();
        let (yl, yu) = e.scaled_row_bounds();
        let invariant = [e.scaled_objective(), xl, xu, yl, yu]
            .into_iter()
            .map(|v| {
                let mut pad = vec![0.; size];
                pad[..v.len()].copy_from_slice(v);
                upload(&c, &stream, &pad)
            })
            .collect::<Result<Vec<_>, _>>()?;
        let names = [
            "qr_reset",
            "qr_clear",
            "qr_begin",
            "qr_norm",
            "qr_product",
            "qr_primal",
            "qr_dual",
            "qr_collect",
            "qr_tuned_spmv",
            "spmv_warp32",
            "primal_step",
            "dual_step",
            "halpern",
            "tc_ref_product",
            "tc_ref_primal",
            "tc_ref_dual",
        ];
        let names = names.into_iter().chain([
            "tn_norm",
            "tn_pack",
            "tn_int8",
            "tn_fp16",
            "tn_bf16",
            "tn_simt",
            "tn_product",
            "tn_work_reset",
            "tn_work_collect",
        ]);
        let functions = names
            .map(|n| Ok((n, module.function(n).map_err(device)?)))
            .collect::<Result<BTreeMap<_, _>, String>>()?;
        let blocks = size.div_ceil(32);
        let mut active = vec![0u32; blocks * 2];
        for (&r, &col) in op.dense_rows.iter().zip(&op.dense_columns) {
            active[r as usize] = 1;
            active[blocks + col as usize] = 1;
        }
        let (rv, cv) = e.scaled_matrix();
        let reference_values = rv.iter().chain(cv).copied().collect::<Vec<_>>();
        let mut reference_indices = Vec::with_capacity(reference_values.len());
        let mut reference_offsets = Vec::with_capacity(op.rows + op.columns + 2);
        for (view, count) in [
            (e.program().row_major(), op.rows),
            (e.program().column_major(), op.columns),
        ] {
            for j in 0..count {
                reference_offsets.push(view.offset(j) as u32);
                reference_indices.extend_from_slice(view.line(j).0);
            }
            reference_offsets.push((reference_values.len() / 2) as u32);
        }
        Ok(Self {
            reference_values: upload(&c, &stream, &reference_values)?,
            reference_indices: upload(&c, &stream, &reference_indices)?,
            reference_offsets: upload(&c, &stream, &reference_offsets)?,
            reference_bad: upload(&c, &stream, &[0u32])?,
            host_audit: false,
            tq: upload(&c, &stream, &op.dense)?,
            tx: upload(&c, &stream, &vec![0i64; blocks * 32])?,
            txe: upload(&c, &stream, &vec![0i32; blocks])?,
            tae: upload(&c, &stream, &op.dense_exponents)?,
            tr: upload(&c, &stream, &op.dense_rows)?,
            tc: upload(&c, &stream, &op.dense_columns)?,
            selected: upload(&c, &stream, &op.selected)?,
            active: upload(&c, &stream, &active)?,
            parts: upload(&c, &stream, &vec![0.; op.dense_exponents.len().max(1) * 32])?,
            part_flags: upload(
                &c,
                &stream,
                &vec![0u32; op.dense_exponents.len().max(1) * 32],
            )?,
            twork: upload(
                &c,
                &stream,
                &vec![0u64; op.dense_exponents.len().max(1) * 2],
            )?,
            tcollected: upload(&c, &stream, &[0u64])?,
            original: upload(&c, &stream, &op.values)?,
            represented: upload(&c, &stream, &op.represented)?,
            residual: upload(&c, &stream, &vec![0.; size.div_ceil(32) * 32])?,
            codes: upload(&c, &stream, &codes)?,
            low_error: upload(&c, &stream, &op.low_error)?,
            native_error: upload(&c, &stream, &op.native_error)?,
            line: upload(&c, &stream, &op.line)?,
            group: upload(&c, &stream, &op.group)?,
            tiles: upload(&c, &stream, &op.group_tiles)?,
            ids: upload(&c, &stream, &op.ids)?,
            inputs: upload(&c, &stream, &op.inputs)?,
            entries: upload(&c, &stream, &op.entries)?,
            exponents: upload(&c, &stream, &exponents)?,
            promoted: upload(&c, &stream, &vec![0u32; op.tiles.len().max(1)])?,
            constants: upload(&c, &stream, &vec![0.; 3 * lines])?,
            scales: upload(&c, &stream, &scales)?,
            bounds: upload(&c, &stream, &vec![0.; lines])?,
            packed_values: upload(&c, &stream, &values)?,
            norm: upload(&c, &stream, &[0.; 3])?,
            control: upload(&c, &stream, &[0u32; 4])?,
            flags: upload(&c, &stream, &vec![0u32; lines])?,
            stats: upload(&c, &stream, &vec![0u64; 7 * lines])?,
            collected: upload(&c, &stream, &[0u64; 11])?,
            vectors,
            invariant,
            functions,
            op,
            stream,
            loaded_generation: None,
            loaded_restarts: None,
            counters: Counters {
                upload_bytes: bytes,
                peak_bytes: bytes,
                ..Counters::default()
            },
        })
    }
    fn submit_reference(
        &mut self,
        name: &'static str,
        grid: u32,
        args: &[A],
    ) -> Result<(), String> {
        self.submit(name, grid, args)?;
        self.counters.reference_launches += 1;
        Ok(())
    }
    fn submit(&mut self, name: &'static str, grid: u32, args: &[A]) -> Result<(), String> {
        let _component = optimizer_core::lp_cost::scope(name);
        launch(
            &self.functions[name],
            LaunchConfig {
                grid: grid.max(1),
                block: 256,
                shared_memory: 0,
            },
            args,
            &self.stream,
        )
        .map_err(device)?;
        self.counters.launches += 1;
        Ok(())
    }
    fn v(&self, i: usize) -> A {
        A::DevicePtr(self.vectors[i].as_device_ptr())
    }
    fn upload_vector(&mut self, i: usize, v: &[f64]) -> Result<(), String> {
        let mut pad = vec![0.; self.vectors[i].len()];
        pad[..v.len()].copy_from_slice(v);
        self.vectors[i]
            .copy_from(&pad, &self.stream)
            .map_err(device)?;
        self.counters.upload_bytes += (pad.len() * 8) as u64;
        Ok(())
    }
    fn read_vector(&mut self, i: usize, len: usize) -> Result<Vec<f64>, String> {
        let mut v = vec![0.; self.vectors[i].len()];
        self.vectors[i]
            .copy_to(&mut v, &self.stream)
            .map_err(device)?;
        self.counters.readback_bytes += (v.len() * 8) as u64;
        v.truncate(len);
        Ok(v)
    }
    pub fn probe(&mut self, g: &Generation, t: bool, v: &[f64]) -> Result<Product, String> {
        if !g.matches(self.op) {
            return Err("stale_operator".into());
        }
        if v.len() != if t { self.op.rows } else { self.op.columns } {
            return Err("vector_shape".into());
        }
        self.bind_generation(g)?;
        self.submit(
            "tn_work_reset",
            (self.twork.len() as u32).div_ceil(256),
            &[
                A::DevicePtr(self.twork.as_device_ptr()),
                A::U32(self.twork.len() as u32),
            ],
        )?;
        self.upload_vector(if t { 1 } else { 4 }, v)?;
        self.submit(
            "qr_reset",
            (self.stats.len() as u32).div_ceil(256),
            &[
                A::DevicePtr(self.stats.as_device_ptr()),
                A::DevicePtr(self.flags.as_device_ptr()),
                A::DevicePtr(self.control.as_device_ptr()),
                A::U32((self.op.rows + self.op.columns).max(1) as u32),
            ],
        )?;
        self.product(g, t)?;
        self.submit(
            "qr_collect",
            1,
            &[
                A::DevicePtr(self.stats.as_device_ptr()),
                A::DevicePtr(self.control.as_device_ptr()),
                A::DevicePtr(self.collected.as_device_ptr()),
                A::U32(self.op.rows as u32),
                A::U32(self.op.columns as u32),
            ],
        )?;
        let mut stats = [0u64; 11];
        self.collected
            .copy_to(&mut stats, &self.stream)
            .map_err(device)?;
        let mut flags = vec![0u32; self.flags.len()];
        self.flags
            .copy_to(&mut flags, &self.stream)
            .map_err(device)?;
        let mut bounds = vec![0.; self.bounds.len()];
        self.bounds
            .copy_to(&mut bounds, &self.stream)
            .map_err(device)?;
        self.counters.readback_bytes += (88 + flags.len() * 4 + bounds.len() * 8) as u64;
        let count = if t { self.op.columns } else { self.op.rows };
        let start = if t { self.op.rows } else { 0 };
        let output = self.read_vector(if t { 5 } else { 6 }, count)?;
        let mut component = Counts::default();
        self.component_counts(&mut component)?;
        Ok(Product {
            output,
            flags: flags[start..start + count].to_vec(),
            bounds: bounds[start..start + count].to_vec(),
            counts: Counts {
                low: stats[0],
                high: stats[1],
                guard_products: 0,
                residual_products: stats[10],
                nonzero_t: stats[2],
                nonzero_f: stats[3],
                coarse_pass: stats[4],
                detailed_pass: stats[5],
                detailed_fail: stats[6],
                component_products: component.component_products,
                mma_instructions: component.mma_instructions,
                padded_products: component.padded_products,
                ..Counts::default()
            },
        })
    }
    fn bind_generation(&mut self, g: &Generation) -> Result<(), String> {
        if !g.matches(self.op) {
            return Err("stale_operator".into());
        }
        let token = g.identity();
        if self
            .loaded_generation
            .as_ref()
            .is_none_or(|old| !Arc::ptr_eq(old, &token))
        {
            let mut mask = g
                .promotion()
                .mask
                .iter()
                .map(|&v| u32::from(v))
                .collect::<Vec<_>>();
            if mask.is_empty() {
                mask.push(0);
            }
            self.promoted
                .copy_from(&mask, &self.stream)
                .map_err(device)?;
            let mut constants = g
                .constants()
                .iter()
                .flat_map(|c| [c.alpha, c.beta, c.tiny])
                .collect::<Vec<_>>();
            if constants.is_empty() {
                constants = vec![0.; 3];
            }
            self.constants
                .copy_from(&constants, &self.stream)
                .map_err(device)?;
            self.counters.upload_bytes += (mask.len() * 4 + constants.len() * 8) as u64;
            self.loaded_generation = Some(token);
        }
        Ok(())
    }

    fn product(&mut self, g: &Generation, t: bool) -> Result<(), String> {
        self.product_mode(g, t, 0)
    }
    fn product_mode(&mut self, g: &Generation, t: bool, mode: u32) -> Result<(), String> {
        if mode != 0 {
            return Err("tensor_unguarded_mode_refused".into());
        }
        let op = self.op;
        let p = |x| A::DevicePtr(x);
        let count = if t { op.columns } else { op.rows };
        let start = if t { op.rows } else { 0 };
        let input = if t { 1 } else { 4 };
        let output = if t { 5 } else { 6 };
        let native = u32::from(g.promotion().native);
        self.submit(
            "tn_norm",
            1,
            &[
                self.v(input),
                p(self.norm.as_device_ptr()),
                p(self.control.as_device_ptr()),
                A::U32(if t { op.rows } else { op.columns } as u32),
                A::U32(native),
            ],
        )?;
        let blocks = op.rows.max(op.columns).max(1).div_ceil(32);
        self.submit(
            "tn_pack",
            (if t { op.rows } else { op.columns } as u32).div_ceil(256),
            &[
                self.v(input),
                p(self.tx.as_device_ptr()),
                p(self.residual.as_device_ptr()),
                p(self.txe.as_device_ptr()),
                p(self.active.as_device_ptr() + if t { 0 } else { blocks as u64 * 4 }),
                p(self.control.as_device_ptr()),
                p(self.norm.as_device_ptr()),
                A::U32(if t { op.rows } else { op.columns } as u32),
                A::U32(native),
            ],
        )?;
        let name = match op.layout {
            Layout::Int8 => "tn_int8",
            Layout::Fp16 => "tn_fp16",
            Layout::Bf16 => "tn_bf16",
            _ => "tn_simt",
        };
        let grid = if op.layout == Layout::Simt || !op.layout.tensor() {
            (op.dense_exponents.len() as u32 * 32).div_ceil(256)
        } else {
            (op.dense_exponents.len() as u32 * 64).div_ceil(256)
        };
        self.submit(
            name,
            grid,
            &[
                p(self.tq.as_device_ptr()),
                p(self.tae.as_device_ptr()),
                p(self.tr.as_device_ptr()),
                p(self.tc.as_device_ptr()),
                p(self.tx.as_device_ptr()),
                p(self.txe.as_device_ptr()),
                p(self.parts.as_device_ptr()),
                p(self.part_flags.as_device_ptr()),
                p(self.twork.as_device_ptr()),
                p(self.norm.as_device_ptr()),
                p(self.control.as_device_ptr()),
                A::U32(op.dense_exponents.len() as u32),
                A::U32(u32::from(t)),
                A::U32(native),
            ],
        )?;
        self.submit(
            "tn_product",
            (count as u32).div_ceil(256),
            &[
                p(self.original.as_device_ptr()),
                p(self.represented.as_device_ptr()),
                p(self.residual.as_device_ptr()),
                p(self.tx.as_device_ptr()),
                p(self.line.as_device_ptr()),
                p(self.group.as_device_ptr()),
                p(self.tiles.as_device_ptr()),
                p(self.ids.as_device_ptr()),
                p(self.inputs.as_device_ptr()),
                p(self.selected.as_device_ptr()),
                p(self.promoted.as_device_ptr()),
                p(self.constants.as_device_ptr()),
                p(self.bounds.as_device_ptr()),
                p(self.scales.as_device_ptr()),
                self.v(input),
                self.v(output),
                p(self.norm.as_device_ptr()),
                p(self.control.as_device_ptr()),
                p(self.flags.as_device_ptr()),
                p(self.stats.as_device_ptr()),
                p(self.parts.as_device_ptr()),
                p(self.part_flags.as_device_ptr()),
                A::U32(count as u32),
                A::U32(start as u32),
            ],
        )?;
        Ok(())
    }
    fn component_counts(&mut self, counts: &mut Counts) -> Result<(), String> {
        self.submit(
            "tn_work_collect",
            1,
            &[
                A::DevicePtr(self.twork.as_device_ptr()),
                A::DevicePtr(self.tcollected.as_device_ptr()),
                A::U32(self.twork.len() as u32),
            ],
        )?;
        let mut work = [0u64];
        self.tcollected
            .copy_to(&mut work, &self.stream)
            .map_err(device)?;
        self.counters.readback_bytes += 8;
        if self.op.layout == Layout::Simt {
            counts.component_products = work[0] * 1024;
            return Ok(());
        }
        counts.mma_instructions = work[0];
        counts.padded_products = work[0]
            * if self.op.layout == Layout::Int8 {
                4096
            } else {
                2048
            };
        // Component products count nonpadding matrix/vector slice multiplications.
        counts.component_products = if self.op.layout == Layout::Simt {
            0
        } else {
            work[0]
                / match self.op.layout {
                    Layout::Int8 => 16,
                    Layout::Fp16 => 32,
                    Layout::Bf16 => 112,
                    _ => 1,
                }
                * 1024
                * if self.op.layout == Layout::Bf16 {
                    196
                } else {
                    64
                }
        };
        Ok(())
    }
}
impl WindowOracle for Oracle<'_, '_> {
    fn reference(&mut self, e: &Engine<'_>, s: &Fp64State) -> Result<(Vec<f64>, Vec<f64>), String> {
        if self.host_audit {
            return optimizer_lp::precision::correction(e, s).map_err(str::to_string);
        }
        let _scope = optimizer_core::lp_cost::scope("device_reference_audit");
        self.counters.reference_updates += 1;
        let before_readback = self.counters.readback_bytes;
        let (ps, ds) = (e.step() / s.weight, e.step() * s.weight);
        if !ps.is_finite() || !ds.is_finite() || ps == 0. || ds == 0. {
            return Err("update_step_range".into());
        }
        let toward = (s.since_restart + 1) as f64 / (s.since_restart + 2) as f64;
        let back = 1. / (s.since_restart + 2) as f64;
        self.reference_bad
            .copy_from(&[0u32], &self.stream)
            .map_err(device)?;
        self.counters.upload_bytes += 4;
        let p = |v| A::DevicePtr(v);
        let product = |this: &mut Self, transpose: bool, input: usize, output: usize| {
            this.submit_reference(
                "tc_ref_product",
                (if transpose {
                    this.op.columns
                } else {
                    this.op.rows
                } as u32)
                    .div_ceil(256),
                &[
                    p(this.reference_values.as_device_ptr()),
                    p(this.reference_indices.as_device_ptr()),
                    p(this.reference_offsets.as_device_ptr()),
                    this.v(input),
                    this.v(output),
                    p(this.reference_bad.as_device_ptr()),
                    A::U32(if transpose {
                        this.op.columns
                    } else {
                        this.op.rows
                    } as u32),
                    A::U32(if transpose { this.op.rows + 1 } else { 0 } as u32),
                    A::U32(if transpose { this.op.values.len() } else { 0 } as u32),
                ],
            )
        };
        product(self, true, 8, 5)?;
        self.submit_reference(
            "tc_ref_primal",
            (self.op.columns as u32).div_ceil(256),
            &[
                self.v(7),
                self.v(5),
                p(self.invariant[0].as_device_ptr()),
                p(self.invariant[1].as_device_ptr()),
                p(self.invariant[2].as_device_ptr()),
                self.v(2),
                self.v(10),
                self.v(9),
                p(self.reference_bad.as_device_ptr()),
                A::U32(self.op.columns as u32),
                A::F64(ps),
                A::F64(toward),
                A::F64(back),
            ],
        )?;
        product(self, false, 9, 6)?;
        self.submit_reference(
            "tc_ref_dual",
            (self.op.rows as u32).div_ceil(256),
            &[
                self.v(8),
                self.v(6),
                p(self.invariant[3].as_device_ptr()),
                p(self.invariant[4].as_device_ptr()),
                self.v(3),
                p(self.reference_bad.as_device_ptr()),
                A::U32(self.op.rows as u32),
                A::F64(ds),
                A::F64(toward),
                A::F64(back),
            ],
        )?;

        let mut bad = [0u32];
        self.reference_bad
            .copy_to(&mut bad, &self.stream)
            .map_err(device)?;
        self.counters.readback_bytes += 4;
        let result = (
            self.read_vector(10, self.op.columns)?,
            self.read_vector(6, self.op.rows)?,
        );
        self.counters.reference_readback_bytes += self.counters.readback_bytes - before_readback;
        if bad[0] != 0 {
            return Err("reference_fp64_range".into());
        }
        Ok(result)
    }

    fn window(
        &mut self,
        e: &Engine<'_>,
        op: &Operator,
        g: &Generation,
        s: &Fp64State,
        len: u64,
    ) -> Result<Window, String> {
        let _cost = optimizer_core::lp_cost::scope("resident_device_window");
        if !std::ptr::eq(op, self.op) || !g.matches(op) {
            return Err("stale_operator".into());
        }
        if len == 0
            || len
                > if op.layout == Layout::OriginalTuned {
                    200
                } else {
                    32
                }
        {
            return Err("resident_window_limit".into());
        }
        self.counters.windows += 1;
        self.submit(
            "tn_work_reset",
            (self.twork.len() as u32).div_ceil(256),
            &[
                A::DevicePtr(self.twork.as_device_ptr()),
                A::U32(self.twork.len() as u32),
            ],
        )?;
        self.bind_generation(g)?;
        self.upload_vector(0, &s.primal)?;
        self.upload_vector(1, &s.dual)?;
        self.counters.state_uploads += 1;
        if self.loaded_restarts != Some(s.restarts) {
            self.upload_vector(2, &s.anchor_primal)?;
            self.upload_vector(3, &s.anchor_dual)?;
            self.loaded_restarts = Some(s.restarts);
        }
        if op.layout != Layout::OriginalTuned {
            self.submit(
                "qr_reset",
                (self.stats.len() as u32).div_ceil(256),
                &[
                    A::DevicePtr(self.stats.as_device_ptr()),
                    A::DevicePtr(self.flags.as_device_ptr()),
                    A::DevicePtr(self.control.as_device_ptr()),
                    A::U32((op.rows + op.columns).max(1) as u32),
                ],
            )?;
        }
        let ps = e.step() / s.weight;
        let ds = e.step() * s.weight;
        if !ps.is_finite() || !ds.is_finite() || ps == 0. || ds == 0. {
            return Ok(Window {
                primal: s.primal.clone(),
                dual: s.dual.clone(),
                pre: None,
                started: 1,
                bad: vec![],
                failure: Some("resident_update_range".into()),
                counts: Counts {
                    windows: 1,
                    predicated: len - 1,
                    ..Counts::default()
                },
            });
        }
        let p = |x| A::DevicePtr(x);
        let grid = (op.rows.max(op.columns).max(1) as u32).div_ceil(256);
        for k in 0..len {
            let since = s.since_restart + k;
            let toward = (since + 1) as f64 / (since + 2) as f64;
            let back = 1. / (since + 2) as f64;
            if op.layout == Layout::OriginalTuned {
                self.submit(
                    "spmv_warp32",
                    (op.columns as u32).div_ceil(8),
                    &[
                        p(self.packed_values.as_device_ptr()),
                        p(self.inputs.as_device_ptr()),
                        p(self.entries.as_device_ptr() + op.rows as u64 * 4),
                        self.v(1),
                        self.v(5),
                        A::U32(op.columns as u32),
                        A::U32(0),
                    ],
                )?;
                self.submit(
                    "primal_step",
                    (op.columns as u32).div_ceil(256),
                    &[
                        self.v(0),
                        self.v(5),
                        p(self.invariant[0].as_device_ptr()),
                        p(self.invariant[1].as_device_ptr()),
                        p(self.invariant[2].as_device_ptr()),
                        self.v(9),
                        self.v(4),
                        A::F64(ps),
                        A::U32(op.columns as u32),
                    ],
                )?;
                self.submit(
                    "spmv_warp32",
                    (op.rows as u32).div_ceil(8),
                    &[
                        p(self.packed_values.as_device_ptr()),
                        p(self.inputs.as_device_ptr()),
                        p(self.entries.as_device_ptr()),
                        self.v(4),
                        self.v(6),
                        A::U32(op.rows as u32),
                        A::U32(0),
                    ],
                )?;
                self.submit(
                    "dual_step",
                    (op.rows as u32).div_ceil(256),
                    &[
                        self.v(1),
                        self.v(6),
                        p(self.invariant[3].as_device_ptr()),
                        p(self.invariant[4].as_device_ptr()),
                        self.v(10),
                        A::F64(ds),
                        A::U32(op.rows as u32),
                    ],
                )?;
                self.submit(
                    "halpern",
                    (op.columns as u32).div_ceil(256),
                    &[
                        self.v(9),
                        self.v(2),
                        self.v(0),
                        A::F64(toward),
                        A::F64(back),
                        A::U32(op.columns as u32),
                    ],
                )?;
                self.submit(
                    "halpern",
                    (op.rows as u32).div_ceil(256),
                    &[
                        self.v(10),
                        self.v(3),
                        self.v(1),
                        A::F64(toward),
                        A::F64(back),
                        A::U32(op.rows as u32),
                    ],
                )?;
            } else {
                self.submit(
                    "qr_begin",
                    grid,
                    &[
                        self.v(0),
                        self.v(1),
                        self.v(7),
                        self.v(8),
                        p(self.control.as_device_ptr()),
                        A::U32(op.columns as u32),
                        A::U32(op.rows as u32),
                        A::U32(u32::from(k + 1 == len)),
                    ],
                )?;
                self.product(g, true)?;
                self.submit(
                    "qr_primal",
                    (op.columns as u32).div_ceil(256),
                    &[
                        self.v(0),
                        self.v(5),
                        p(self.invariant[0].as_device_ptr()),
                        p(self.invariant[1].as_device_ptr()),
                        p(self.invariant[2].as_device_ptr()),
                        self.v(2),
                        self.v(4),
                        p(self.norm.as_device_ptr()),
                        p(self.control.as_device_ptr()),
                        p(self.flags.as_device_ptr()),
                        A::U32(op.rows as u32),
                        A::U32(op.columns as u32),
                        A::F64(ps),
                        A::F64(toward),
                        A::F64(back),
                    ],
                )?;
                self.product(g, false)?;
                self.submit(
                    "qr_dual",
                    (op.rows as u32).div_ceil(256),
                    &[
                        self.v(1),
                        self.v(6),
                        p(self.invariant[3].as_device_ptr()),
                        p(self.invariant[4].as_device_ptr()),
                        self.v(3),
                        p(self.norm.as_device_ptr()),
                        p(self.control.as_device_ptr()),
                        p(self.flags.as_device_ptr()),
                        A::U32(op.rows as u32),
                        A::F64(ds),
                        A::F64(toward),
                        A::F64(back),
                    ],
                )?;
            }
        }
        let (started, failure, bad, mut counts) = if op.layout == Layout::OriginalTuned {
            (
                len,
                None,
                vec![],
                Counts {
                    high: 2 * op.values.len() as u64 * len,
                    windows: 1,
                    ..Counts::default()
                },
            )
        } else {
            self.submit(
                "qr_collect",
                1,
                &[
                    p(self.stats.as_device_ptr()),
                    p(self.control.as_device_ptr()),
                    p(self.collected.as_device_ptr()),
                    A::U32(op.rows as u32),
                    A::U32(op.columns as u32),
                ],
            )?;
            let mut v = [0u64; 11];
            self.collected
                .copy_to(&mut v, &self.stream)
                .map_err(device)?;
            self.counters.readback_bytes += 88;
            let mut bad = vec![];
            let failure = if v[8] != 0 {
                let mut flags = vec![0u32; self.flags.len()];
                self.flags
                    .copy_to(&mut flags, &self.stream)
                    .map_err(device)?;
                self.counters.readback_bytes += (flags.len() * 4) as u64;
                bad.extend(op.bad_tiles(g, false, &flags[..op.rows]));
                bad.extend(op.bad_tiles(g, true, &flags[op.rows..op.rows + op.columns]));
                bad.sort_unstable();
                bad.dedup();
                Some(
                    if v[8] & 2 != 0 {
                        "resident_product_or_update_range"
                    } else if bad.is_empty() {
                        "native_operator_error_budget"
                    } else {
                        "operator_error_budget"
                    }
                    .to_string(),
                )
            } else {
                None
            };
            (
                v[7],
                failure,
                bad,
                Counts {
                    low: v[0],
                    high: v[1],
                    guard_products: 0,
                    residual_products: v[10],
                    nonzero_t: v[2],
                    nonzero_f: v[3],
                    coarse_pass: v[4],
                    detailed_pass: v[5],
                    detailed_fail: v[6],
                    predicated: len.saturating_sub(v[7]),
                    windows: 1,
                    ..Counts::default()
                },
            )
        };
        self.component_counts(&mut counts)?;
        if failure.is_some() {
            return Ok(Window {
                primal: s.primal.clone(),
                dual: s.dual.clone(),
                pre: None,
                started,
                bad,
                failure,
                counts,
            });
        }
        let primal = self.read_vector(0, op.columns)?;
        let dual = self.read_vector(1, op.rows)?;
        let pre = if op.layout.audits() {
            let mut pre = s.clone();
            pre.primal = self.read_vector(7, op.columns)?;
            pre.dual = self.read_vector(8, op.rows)?;
            pre.iterations += len - 1;
            pre.since_restart += len - 1;
            Some(pre)
        } else {
            None
        };
        Ok(Window {
            primal,
            dual,
            pre,
            started,
            bad,
            failure,
            counts,
        })
    }
}
