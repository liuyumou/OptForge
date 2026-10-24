//! Expanded private window buffers with retained FP64 reference/native kernels.
use crate::{
    Engine,
    control::Fp64State,
    native,
    tensor_cost::{Counts, Generation, Layout, Operator, Oracle as WindowOracle, Window},
    value::Value,
};
use optimizer_cuda_sys::events::Event;
use optimizer_cuda_sys::{
    Argument as A, Context, DeviceBuffer, Function, LaunchConfig, Module, launch,
};
use std::{collections::BTreeMap, rc::Rc};
fn p(v: u64) -> A {
    A::DevicePtr(v)
}
fn err(e: impl std::fmt::Display) -> String {
    format!("device:{e}")
}
struct Soa {
    buffer: DeviceBuffer<u32>,
    n: usize,
}
impl Soa {
    fn argument(&self) -> A {
        let base = self.buffer.as_device_ptr();
        A::Soa32([
            base,
            base + 4 * self.n as u64,
            base + 8 * self.n as u64,
            base + 12 * self.n as u64,
        ])
    }
    fn upload(
        &mut self,
        values: &[Value],
        stream: &optimizer_cuda_sys::Stream,
    ) -> Result<(), String> {
        if values.len() > self.n {
            return Err("expanded_shape".into());
        }
        let mut words = vec![0u32; 4 * self.n];
        for (i, v) in values.iter().enumerate() {
            words[i] = ((v.magnitude >> 40) as f32).to_bits();
            words[self.n + i] = (((v.magnitude >> 16) & 0xffffff) as f32).to_bits();
            words[2 * self.n + i] = ((v.magnitude & 65535) as f32).to_bits();
            words[3 * self.n + i] = (v.exponent as u32 & 65535) | (u32::from(v.negative) << 31);
        }
        self.buffer.copy_from(&words, stream).map_err(err)
    }
    fn read(&self, n: usize, stream: &optimizer_cuda_sys::Stream) -> Result<Vec<Value>, String> {
        let mut words = vec![0u32; 4 * self.n];
        self.buffer.copy_to(&mut words, stream).map_err(err)?;
        (0..n)
            .map(|i| {
                let hi = f32::from_bits(words[i]);
                let mid = f32::from_bits(words[self.n + i]);
                let lo = f32::from_bits(words[2 * self.n + i]);
                let meta = words[3 * self.n + i];
                if [hi, mid, lo]
                    .iter()
                    .any(|v| !v.is_finite() || v.is_sign_negative() || v.fract() != 0.)
                    || hi >= 16777216.
                    || mid >= 16777216.
                    || lo >= 65536.
                    || meta & 0x7fff0000 != 0
                {
                    return Err("expanded_malformed_component".into());
                }
                Ok(Value {
                    magnitude: ((hi as u64) << 40) | ((mid as u64) << 16) | lo as u64,
                    exponent: (meta as u16 as i16) as i32,
                    negative: meta >> 31 != 0,
                })
            })
            .collect()
    }
}
#[repr(C)]
#[derive(Clone, Copy, Default)]
pub(crate) struct Coefficient {
    m: u64,
    e: i32,
    sign: u32,
}
impl Coefficient {
    fn new(v: f64) -> Result<Self, String> {
        let v = Value::from_f64(v)?;
        Ok(Self {
            m: v.magnitude,
            e: v.exponent,
            sign: u32::from(v.negative),
        })
    }
}
pub struct Oracle<'o, 'm> {
    native: native::Oracle<'o, 'm>,
    functions: BTreeMap<&'static str, Function<'m>>,
    state: Vec<Soa>,
    parts: Soa,
    magnitudes: DeviceBuffer<u64>,
    signs: DeviceBuffer<u32>,
    guards: DeviceBuffer<u32>,
    blocks: DeviceBuffer<f64>,
    coefficients: DeviceBuffer<Coefficient>,
    errors: Vec<DeviceBuffer<f64>>,
    pending: Option<Fp64State>,
    valid: bool,
    generation: u64,
    native_sticky: bool,
    events: Vec<(Event, Event)>,
    event_names: Vec<&'static str>,
    pub device_milliseconds: BTreeMap<String, f64>,
}
pub fn additional_bytes(op: &Operator) -> Result<u64, String> {
    let n = op.rows.max(op.columns).max(1).div_ceil(32) * 32;
    let tiles = op.dense_exponents.len().max(1);
    u64::try_from(
        16u128 * (10 * n + tiles * 32) as u128 + 40 * n as u128 + 8 * n.div_ceil(128) as u128 + 64,
    )
    .map_err(err)
}
impl<'o, 'm> Oracle<'o, 'm> {
    pub fn set_host_audit(&mut self, enabled: bool) {
        self.native.host_audit = enabled;
    }
    pub fn probe(
        &mut self,
        g: &Generation,
        t: bool,
        input: &[Value],
    ) -> Result<(Vec<Value>, Vec<f64>, Counts), String> {
        let op = self.native.op;
        let n = if t { op.rows } else { op.columns };
        let count = if t { op.columns } else { op.rows };
        let start = if t { op.rows } else { 0 };
        if input.len() != n || !g.matches(op) || g.promotion().native {
            return Err("expanded_probe_binding".into());
        }
        self.native.bind_generation(g)?;
        self.native.submit(
            "qr_reset",
            (self.native.stats.len() as u32).div_ceil(256),
            &[
                p(self.native.stats.as_device_ptr()),
                p(self.native.flags.as_device_ptr()),
                p(self.native.control.as_device_ptr()),
                A::U32((op.rows + op.columns).max(1) as u32),
            ],
        )?;
        self.native.submit(
            "tn_work_reset",
            (self.native.twork.len() as u32).div_ceil(256),
            &[
                p(self.native.twork.as_device_ptr()),
                A::U32(self.native.twork.len() as u32),
            ],
        )?;
        self.state[if t { 1 } else { 4 }].upload(input, &self.native.stream)?;
        self.product(t)?;
        let status = self.status()?;
        self.collect_events()?;
        if status != 0 {
            return Err(format!("expanded_product_refusal:{status}"));
        }
        let values = self.state[if t { 5 } else { 6 }].read(count, &self.native.stream)?;
        let mut bounds = vec![0.; self.native.bounds.len()];
        self.native
            .bounds
            .copy_to(&mut bounds, &self.native.stream)
            .map_err(err)?;
        let mut counts = Counts::default();
        self.counters(&mut counts)?;
        Ok((values, bounds[start..start + count].to_vec(), counts))
    }
    pub fn new(
        c: Rc<Context>,
        op: &'o Operator,
        reference: &'m Module,
        modules: &'m [Module; 4],
        e: &Engine<'_>,
        diagnostic: bool,
    ) -> Result<Self, String> {
        let old = native::buffer_bytes(op)?;
        let extra = additional_bytes(op)?;
        let bytes = old.checked_add(extra).ok_or("device_memory_overflow")?;
        if bytes > 1 << 30
            || bytes > c.memory_info().map_err(err)?.0
            || op
                .preparation_bytes
                .checked_add(bytes * 2)
                .is_none_or(|v| v > 2 << 30)
        {
            return Err("device_memory_limit".into());
        }
        let native = native::Oracle::new(Rc::clone(&c), op, reference, 1 << 30, e)?;
        let n = op.rows.max(op.columns).max(1).div_ceil(32) * 32;
        fn zeros<T: Copy + Default>(
            c: &Rc<Context>,
            s: &optimizer_cuda_sys::Stream,
            n: usize,
        ) -> Result<DeviceBuffer<T>, String> {
            let mut b = c.allocate(n).map_err(err)?;
            b.copy_from(&vec![T::default(); n], s).map_err(err)?;
            Ok(b)
        }
        let mut state = Vec::new();
        for _ in 0..10 {
            state.push(Soa {
                buffer: zeros(&c, &native.stream, 4 * n)?,
                n,
            });
        }
        let pn = op.dense_exponents.len().max(1) * 32;
        let parts = Soa {
            buffer: zeros(&c, &native.stream, 4 * pn)?,
            n: pn,
        };
        let groups: [&[&str]; 4] = [
            &[
                "xe_encode64",
                "xe_decode64",
                "xe_scalar",
                "xe_integer_fma",
                "xe_project",
            ],
            &[
                "xe_int8_main",
                "xe_fp16_main",
                "xe_bf16_main",
                "xe_simt_main",
                "xe_pack64",
                "xe_primal_update",
                "xe_dual_update",
            ],
            &["xe_abs_blocks", "xe_abs_finish", "xe_reconstruct"],
            &[
                "xe_check_flags",
                "xe_primal_enclosure",
                "xe_dual_enclosure",
                "xe_boundary_enclosure",
            ],
        ];
        let mut functions = BTreeMap::new();
        for (module, names) in modules.iter().zip(groups) {
            for &name in names {
                functions.insert(name, module.function(name).map_err(err)?);
            }
        }
        let magnitudes = zeros(&c, &native.stream, n)?;
        let signs = zeros(&c, &native.stream, n)?;
        let guards = zeros(&c, &native.stream, n)?;
        let blocks = zeros(&c, &native.stream, n.div_ceil(128))?;
        let coefficients = zeros(&c, &native.stream, 4)?;
        let mut errors = Vec::new();
        for _ in 0..3 {
            errors.push(zeros(&c, &native.stream, n)?);
        }
        let mut events = Vec::new();
        if diagnostic {
            for _ in 0..1024 {
                events.push((Event::new(&c).map_err(err)?, Event::new(&c).map_err(err)?));
            }
        }
        Ok(Self {
            native,
            functions,
            state,
            parts,
            magnitudes,
            signs,
            guards,
            blocks,
            coefficients,
            errors,
            pending: None,
            valid: false,
            generation: 0,
            native_sticky: false,
            events,
            event_names: Vec::new(),
            device_milliseconds: BTreeMap::new(),
        })
    }
    fn submit(
        &mut self,
        name: &'static str,
        n: usize,
        block: u32,
        args: &[A],
    ) -> Result<(), String> {
        let _scope = optimizer_core::lp_cost::scope(name);
        self.begin_event(name)?;
        launch(
            &self.functions[name],
            LaunchConfig {
                grid: (n as u32).div_ceil(block).max(1),
                block,
                shared_memory: 0,
            },
            args,
            &self.native.stream,
        )
        .map_err(err)?;
        self.end_event()?;
        self.native.counters.launches += 1;
        Ok(())
    }
    fn begin_event(&mut self, name: &'static str) -> Result<(), String> {
        if self.events.is_empty() {
            return Ok(());
        }
        let i = self.event_names.len();
        let pair = self.events.get(i).ok_or("expanded_event_capacity")?;
        pair.0.record(&self.native.stream).map_err(err)?;
        self.event_names.push(name);
        Ok(())
    }
    fn end_event(&mut self) -> Result<(), String> {
        if !self.events.is_empty() {
            self.events[self.event_names.len() - 1]
                .1
                .record(&self.native.stream)
                .map_err(err)?;
        }
        Ok(())
    }
    fn collect_events(&mut self) -> Result<(), String> {
        if self.event_names.is_empty() {
            return Ok(());
        }
        self.native.stream.synchronize().map_err(err)?;
        for (name, pair) in self.event_names.drain(..).zip(&self.events) {
            *self.device_milliseconds.entry(name.into()).or_default() +=
                f64::from(pair.0.elapsed_to(&pair.1).map_err(err)?);
        }
        Ok(())
    }
    fn status(&mut self) -> Result<u32, String> {
        let mut c = [0u32; 4];
        self.native
            .control
            .copy_to(&mut c, &self.native.stream)
            .map_err(err)?;
        self.native.counters.readback_bytes += 16;
        Ok(c[0])
    }
    fn flags(&mut self, n: usize) -> Result<(), String> {
        self.submit(
            "xe_check_flags",
            n,
            128,
            &[
                p(self.guards.as_device_ptr()),
                p(self.native.control.as_device_ptr()),
                A::U32(n as u32),
            ],
        )
    }
    fn encode(&mut self, source: usize, target: usize, n: usize) -> Result<(), String> {
        self.submit(
            "xe_encode64",
            n,
            128,
            &[
                p(self.native.vectors[source].as_device_ptr()),
                self.state[target].argument(),
                p(self.guards.as_device_ptr()),
                A::U32(n as u32),
            ],
        )?;
        self.flags(n)
    }
    fn decode(
        &mut self,
        source: usize,
        target: usize,
        n: usize,
        error: usize,
        scale_start: usize,
    ) -> Result<(), String> {
        self.submit(
            "xe_decode64",
            n,
            128,
            &[
                self.state[source].argument(),
                p(self.native.vectors[target].as_device_ptr()),
                p(self.guards.as_device_ptr()),
                A::U32(n as u32),
            ],
        )?;
        self.flags(n)?;
        self.submit(
            "xe_boundary_enclosure",
            n,
            128,
            &[
                p(self.native.vectors[target].as_device_ptr()),
                p(self.errors[error].as_device_ptr()),
                p(self.native.scales.as_device_ptr() + 8 * scale_start as u64),
                p(self.native.control.as_device_ptr()),
                A::U32(n as u32),
            ],
        )
    }
    fn product(&mut self, t: bool) -> Result<(), String> {
        let op = self.native.op;
        let input = if t { 1 } else { 4 };
        let out = if t { 5 } else { 6 };
        let n = if t { op.rows } else { op.columns };
        let count = if t { op.columns } else { op.rows };
        let start = if t { op.rows } else { 0 };
        self.submit(
            "xe_abs_blocks",
            n,
            128,
            &[
                self.state[input].argument(),
                p(self.blocks.as_device_ptr()),
                p(self.native.control.as_device_ptr()),
                A::U32(n as u32),
            ],
        )?;
        self.submit(
            "xe_abs_finish",
            1,
            1,
            &[
                p(self.blocks.as_device_ptr()),
                p(self.native.norm.as_device_ptr()),
                A::U32(n.div_ceil(128) as u32),
            ],
        )?;
        self.submit(
            "xe_pack64",
            n.div_ceil(32) * 32,
            128,
            &[
                self.state[input].argument(),
                p(self.magnitudes.as_device_ptr()),
                p(self.signs.as_device_ptr()),
                p(self.native.txe.as_device_ptr()),
                self.state[9].argument(),
                p(self.guards.as_device_ptr()),
                p(self.native.control.as_device_ptr()),
                A::U32(n as u32),
            ],
        )?;
        let name = match op.layout {
            Layout::Int8 => "xe_int8_main",
            Layout::Fp16 => "xe_fp16_main",
            Layout::Bf16 => "xe_bf16_main",
            _ => "xe_simt_main",
        };
        let tiles = op.dense_exponents.len();
        if tiles > 0 {
            self.submit(
                name,
                tiles * if op.layout == Layout::Simt { 32 } else { 64 },
                128,
                &[
                    p(self.native.tq.as_device_ptr()),
                    p(self.native.tae.as_device_ptr()),
                    p(self.native.tr.as_device_ptr()),
                    p(self.native.tc.as_device_ptr()),
                    p(self.magnitudes.as_device_ptr()),
                    p(self.signs.as_device_ptr()),
                    p(self.native.txe.as_device_ptr()),
                    self.parts.argument(),
                    p(self.native.part_flags.as_device_ptr()),
                    p(self.native.twork.as_device_ptr()),
                    p(self.native.norm.as_device_ptr()),
                    p(self.native.control.as_device_ptr()),
                    A::U32(tiles as u32),
                    A::U32(u32::from(t)),
                    A::U32(0),
                ],
            )?;
        }
        self.submit(
            "xe_reconstruct",
            count,
            128,
            &[
                p(self.native.original.as_device_ptr()),
                p(self.native.represented.as_device_ptr()),
                self.state[9].argument(),
                p(self.magnitudes.as_device_ptr()),
                p(self.native.line.as_device_ptr()),
                p(self.native.group.as_device_ptr()),
                p(self.native.tiles.as_device_ptr()),
                p(self.native.ids.as_device_ptr()),
                p(self.native.inputs.as_device_ptr()),
                p(self.native.selected.as_device_ptr()),
                p(self.native.promoted.as_device_ptr()),
                p(self.native.constants.as_device_ptr()),
                p(self.native.bounds.as_device_ptr()),
                p(self.native.scales.as_device_ptr()),
                self.state[input].argument(),
                self.state[out].argument(),
                p(self.native.norm.as_device_ptr()),
                p(self.native.control.as_device_ptr()),
                p(self.native.flags.as_device_ptr()),
                p(self.native.stats.as_device_ptr()),
                self.parts.argument(),
                p(self.native.part_flags.as_device_ptr()),
                A::U32(count as u32),
                A::U32(start as u32),
            ],
        )
    }
    fn step(&mut self, e: &Engine<'_>, s: &Fp64State, k: u64) -> Result<u32, String> {
        let op = self.native.op;
        let ps = e.step() / s.weight;
        let ds = e.step() * s.weight;
        let since = s.since_restart + k;
        let toward = (since + 1) as f64 / (since + 2) as f64;
        let back = 1. / (since + 2) as f64;
        if !ps.is_finite() || !ds.is_finite() || ps <= 0. || ds <= 0. {
            return Ok(8);
        }
        self.coefficients
            .copy_from(
                &[
                    Coefficient::new(ps)?,
                    Coefficient::new(ds)?,
                    Coefficient::new(toward)?,
                    Coefficient::new(back)?,
                ],
                &self.native.stream,
            )
            .map_err(err)?;
        self.product(true)?;
        let status = self.status()?;
        if status != 0 {
            return Ok(status);
        }
        self.submit(
            "xe_primal_update",
            op.columns,
            128,
            &[
                self.state[0].argument(),
                self.state[5].argument(),
                self.state[2].argument(),
                p(self.native.invariant[0].as_device_ptr()),
                p(self.native.invariant[1].as_device_ptr()),
                p(self.native.invariant[2].as_device_ptr()),
                p(self.coefficients.as_device_ptr()),
                self.state[7].argument(),
                self.state[4].argument(),
                p(self.guards.as_device_ptr()),
                A::U32(op.columns as u32),
            ],
        )?;
        self.flags(op.columns)?;
        self.submit(
            "xe_primal_enclosure",
            op.columns,
            128,
            &[
                self.state[0].argument(),
                self.state[5].argument(),
                self.state[2].argument(),
                self.state[4].argument(),
                p(self.native.invariant[0].as_device_ptr()),
                p(self.native.bounds.as_device_ptr()),
                p(self.native.scales.as_device_ptr() + 8 * op.rows as u64),
                p(self.errors[0].as_device_ptr()),
                p(self.errors[2].as_device_ptr()),
                p(self.native.control.as_device_ptr()),
                A::U32(op.columns as u32),
                A::U32(op.rows as u32),
                A::F64(ps),
                A::F64(toward),
                A::F64(back),
            ],
        )?;
        let status = self.status()?;
        if status != 0 {
            return Ok(status);
        }
        self.product(false)?;
        let status = self.status()?;
        if status != 0 {
            return Ok(status);
        }
        self.submit(
            "xe_dual_update",
            op.rows,
            128,
            &[
                self.state[1].argument(),
                self.state[6].argument(),
                self.state[3].argument(),
                p(self.native.invariant[3].as_device_ptr()),
                p(self.native.invariant[4].as_device_ptr()),
                p(self.coefficients.as_device_ptr()),
                self.state[8].argument(),
                p(self.guards.as_device_ptr()),
                A::U32(op.rows as u32),
            ],
        )?;
        self.flags(op.rows)?;
        self.submit(
            "xe_dual_enclosure",
            op.rows,
            128,
            &[
                self.state[1].argument(),
                self.state[6].argument(),
                self.state[3].argument(),
                self.state[8].argument(),
                p(self.native.bounds.as_device_ptr()),
                p(self.errors[2].as_device_ptr()),
                p(self.native.original.as_device_ptr()),
                p(self.native.native_error.as_device_ptr()),
                p(self.native.reference_offsets.as_device_ptr()),
                p(self.native.reference_indices.as_device_ptr()),
                p(self.native.invariant[3].as_device_ptr()),
                p(self.native.invariant[4].as_device_ptr()),
                p(self.native.scales.as_device_ptr()),
                p(self.errors[1].as_device_ptr()),
                p(self.native.control.as_device_ptr()),
                A::U32(op.rows as u32),
                A::F64(ds),
                A::F64(toward),
                A::F64(back),
            ],
        )?;
        let status = self.status()?;
        if status == 0 {
            self.state.swap(0, 7);
            self.state.swap(1, 8);
        }
        Ok(status)
    }
    fn counters(&mut self, counts: &mut Counts) -> Result<(), String> {
        let op = self.native.op;
        let mut stats = vec![0u64; self.native.stats.len()];
        self.native
            .stats
            .copy_to(&mut stats, &self.native.stream)
            .map_err(err)?;
        for (row, v) in stats.chunks_exact(7).enumerate() {
            counts.low += v[0];
            counts.high += v[1];
            if row < op.rows {
                counts.nonzero_f += v[2];
            } else {
                counts.nonzero_t += v[2];
            }
            counts.coarse_pass += v[3];
            counts.detailed_pass += v[4];
            counts.detailed_fail += v[5];
            counts.residual_products += v[6];
        }
        let mut work = vec![0u64; self.native.twork.len()];
        self.native
            .twork
            .copy_to(&mut work, &self.native.stream)
            .map_err(err)?;
        let executed = work.into_iter().try_fold(0u64, |a, b| {
            a.checked_add(b).ok_or("expanded_counter_overflow")
        })?;
        let per = match op.layout {
            Layout::Int8 => 32,
            Layout::Fp16 => 64,
            Layout::Bf16 => 112,
            _ => 1,
        };
        if !executed.is_multiple_of(per) {
            return Err("expanded_mma_counter_remainder".into());
        }
        if op.layout == Layout::Simt {
            counts.component_products = executed * 1024;
        } else {
            counts.mma_instructions = executed;
            counts.component_products =
                executed / per * 1024 * if op.layout == Layout::Bf16 { 224 } else { 80 };
            counts.padded_products = executed
                * if op.layout == Layout::Int8 {
                    4096
                } else {
                    2048
                };
        }
        Ok(())
    }
}
pub fn same_state(a: &Fp64State, b: &Fp64State) -> bool {
    fn bits(a: &[f64], b: &[f64]) -> bool {
        a.len() == b.len() && a.iter().zip(b).all(|(a, b)| a.to_bits() == b.to_bits())
    }
    bits(&a.primal, &b.primal)
        && bits(&a.dual, &b.dual)
        && bits(&a.anchor_primal, &b.anchor_primal)
        && bits(&a.anchor_dual, &b.anchor_dual)
        && [a.weight, a.integral, a.anchor_error, a.last_check_error].map(f64::to_bits)
            == [b.weight, b.integral, b.anchor_error, b.last_check_error].map(f64::to_bits)
        && a.previous_error.map(f64::to_bits) == b.previous_error.map(f64::to_bits)
        && (
            a.iterations,
            a.restarts,
            a.since_restart,
            a.checked_iteration,
        ) == (
            b.iterations,
            b.restarts,
            b.since_restart,
            b.checked_iteration,
        )
}
impl WindowOracle for Oracle<'_, '_> {
    fn reference(&mut self, e: &Engine<'_>, s: &Fp64State) -> Result<(Vec<f64>, Vec<f64>), String> {
        let pre = self.pending.take().ok_or("expanded_reference_not_bound")?;
        self.valid = false;
        if !same_state(&pre, s) {
            return Err("expanded_reference_input_mismatch".into());
        }
        // The only writers of native vectors 7/8 in an expanded window are the two
        // checked penultimate decodes below. The final candidate uses other buffers.
        self.begin_event("reference_audit")?;
        let result = self.native.reference(e, s);
        self.end_event()?;
        self.collect_events()?;
        result
    }
    fn window(
        &mut self,
        e: &Engine<'_>,
        op: &Operator,
        g: &Generation,
        s: &Fp64State,
        len: u64,
    ) -> Result<Window, String> {
        self.pending = None;
        self.valid = false;
        if !std::ptr::eq(op, self.native.op) || !g.matches(op) {
            return Err("expanded_operator_binding".into());
        }
        if g.promotion().generation < self.generation || self.native_sticky && !g.promotion().native
        {
            return Err("expanded_stale_generation".into());
        }
        self.generation = g.promotion().generation;
        self.native_sticky |= g.promotion().native;
        if !op.layout.tensor() || g.promotion().native {
            self.begin_event("native_window")?;
            let w = self.native.window(e, op, g, s, len)?;
            self.end_event()?;
            self.collect_events()?;
            self.pending = w.pre.clone();
            return Ok(w);
        }
        if len == 0 || len > 32 || len > 200 - s.iterations % 200 {
            return Err("expanded_window_length".into());
        }
        self.native.bind_generation(g)?;
        self.native.submit(
            "qr_reset",
            (self.native.stats.len() as u32).div_ceil(256),
            &[
                p(self.native.stats.as_device_ptr()),
                p(self.native.flags.as_device_ptr()),
                p(self.native.control.as_device_ptr()),
                A::U32((op.rows + op.columns).max(1) as u32),
            ],
        )?;
        self.native.submit(
            "tn_work_reset",
            (self.native.twork.len() as u32).div_ceil(256),
            &[
                p(self.native.twork.as_device_ptr()),
                A::U32(self.native.twork.len() as u32),
            ],
        )?;
        for i in 0..2 {
            let n = self.errors[i].len();
            self.errors[i]
                .copy_from(&vec![0.; n], &self.native.stream)
                .map_err(err)?;
        }
        for (i, v) in [&s.primal, &s.dual, &s.anchor_primal, &s.anchor_dual]
            .into_iter()
            .enumerate()
        {
            self.native.upload_vector(i, v)?;
            self.encode(i, i, v.len())?;
        }
        let mut w = Window {
            primal: s.primal.clone(),
            dual: s.dual.clone(),
            pre: None,
            started: 0,
            bad: vec![],
            failure: None,
            counts: Counts {
                expansion_counter_version: 1,
                windows: 1,
                encoded_coordinates: 2 * (op.rows + op.columns) as u64,
                ..Default::default()
            },
        };
        let mut status = self.status()?;
        self.valid = status == 0;
        for k in 0..len {
            if status != 0 {
                break;
            }
            if k + 1 == len {
                self.decode(0, 7, op.columns, 0, op.rows)?;
                self.decode(1, 8, op.rows, 1, 0)?;
                w.counts.decoded_coordinates += (op.rows + op.columns) as u64;
                status = self.status()?;
                if status != 0 {
                    break;
                }
                let mut pre = s.clone();
                pre.primal = self.native.read_vector(7, op.columns)?;
                pre.dual = self.native.read_vector(8, op.rows)?;
                pre.iterations += k;
                pre.since_restart += k;
                self.encode(7, 0, op.columns)?;
                self.encode(8, 1, op.rows)?;
                w.counts.encoded_coordinates += (op.rows + op.columns) as u64;
                status = self.status()?;
                if status != 0 {
                    break;
                }
                w.pre = Some(pre);
            }
            w.started += 1;
            status = self.step(e, s, k)?;
            if status == 0 {
                w.counts.expanded_updates += 1;
            }
        }
        if status == 0 {
            self.decode(0, 0, op.columns, 0, op.rows)?;
            self.decode(1, 1, op.rows, 1, 0)?;
            w.counts.decoded_coordinates += (op.rows + op.columns) as u64;
            status = self.status()?;
            if status == 0 {
                w.primal = self.native.read_vector(0, op.columns)?;
                w.dual = self.native.read_vector(1, op.rows)?;
                self.pending = w.pre.clone();
            }
        }
        if status != 0 {
            w.failure = Some(
                if status & 1 != 0 {
                    "expanded_update_or_product_error_budget"
                } else {
                    "expanded_range"
                }
                .into(),
            );
            w.bad = g
                .promotion()
                .mask
                .iter()
                .enumerate()
                .filter_map(|(i, &v)| (!v).then_some(i))
                .collect();
            w.pre = None;
        }
        self.valid = false;
        w.counts.predicated = len - w.started;
        self.counters(&mut w.counts)?;
        self.collect_events()?;
        Ok(w)
    }
}
