//! ADR-0041 resident windows and independently bounded sparse arithmetic.
#![allow(missing_docs)]
use crate::{
    Engine,
    control::{Fp64Checkpoint, Fp64Controller, Fp64State},
    outward::Enclosure,
    quant,
};
use optimizer_core::CancellationToken;
pub use quant::{Format, Policy, Promotion, Settings};
use serde::{Deserialize, Serialize};
use std::{collections::BTreeSet, sync::Arc, time::Instant};

pub const ID: &str = "lp-quant-resident-v1";
pub const GUARD: &str = "global-then-coordinate-successor-rn-v1";
pub const TREE: &str = "segmented-serial-fp32-fp64-v1";
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Layout {
    Segmented,
    Tuned,
    OriginalTuned,
}
impl Layout {
    pub fn audits(self) -> bool {
        self != Self::OriginalTuned
    }
    pub fn guard(self) -> &'static str {
        if self == Self::OriginalTuned {
            "none-original-tuned-v1"
        } else {
            GUARD
        }
    }
    pub fn tree(self) -> &'static str {
        if self == Self::Segmented {
            TREE
        } else {
            "tuned-warp32-v1"
        }
    }
}
/// Successor after nearest on nonnegative operands is an outward operation.
/// Exact zero identities avoid inventing errors on zero-vector products.
pub fn up_add(a: f64, b: f64) -> f64 {
    if a == 0. {
        b
    } else if b == 0. {
        a
    } else {
        (a + b).next_up()
    }
}
pub fn up_mul(a: f64, b: f64) -> f64 {
    if a == 0. || b == 0. {
        0.
    } else {
        (a * b).next_up()
    }
}
pub fn up_div(a: f64, b: f64) -> f64 {
    if a == 0. { 0. } else { (a / b).next_up() }
}
pub fn gamma(n: usize, low: bool) -> f64 {
    let u = if low { 2f64.powi(-24) } else { 2f64.powi(-53) };
    let nu = n as f64 * u;
    if nu >= 1. {
        f64::INFINITY
    } else {
        (nu / (1. - nu)).next_up()
    }
}
fn delta(e: Enclosure, q: f64) -> Result<f64, &'static str> {
    let d = e
        .subtract(Enclosure::point(q).ok_or("bound_range")?)
        .ok_or("bound_range")?;
    Ok(d.lower.abs().max(d.upper.abs()))
}
#[derive(Clone, Copy, Debug, Default)]
pub struct Constant {
    pub alpha: f64,
    pub beta: f64,
    pub tiny: f64,
}
pub struct Operator {
    pub base: quant::Operator,
    pub layout: Layout,
    pub low_error: Vec<f64>,
    pub native_error: Vec<f64>,
    pub preparation_bytes: u64,
    pub line: Vec<u32>,
    pub group: Vec<u32>,
    pub group_tiles: Vec<u32>,
    pub ids: Vec<u32>,
    pub inputs: Vec<u32>,
    pub entries: Vec<u32>,
    origin: Arc<()>,
}
impl std::ops::Deref for Operator {
    type Target = quant::Operator;
    fn deref(&self) -> &Self::Target {
        &self.base
    }
}
impl Operator {
    pub fn new(e: &Engine<'_>, settings: Settings, layout: Layout) -> Result<Self, &'static str> {
        let _cost = optimizer_core::lp_cost::scope("resident_pack_metadata_norm");
        if layout != Layout::Segmented && settings.format != Format::Fp64 {
            return Err("resident_layout_format");
        }
        let base = quant::Operator::new(e, settings)?;
        let mut low_error = Vec::with_capacity(base.values.len());
        let mut native_error = Vec::with_capacity(base.values.len());
        for (id, (r, c, a)) in e.program().row_major().entries().enumerate() {
            let v = Enclosure::product(base.row_scale[r], a).ok_or("scaling_error_range")?;
            let lo = Enclosure::product(v.lower, base.column_scale[c as usize])
                .ok_or("scaling_error_range")?;
            let hi = Enclosure::product(v.upper, base.column_scale[c as usize])
                .ok_or("scaling_error_range")?;
            let exact = Enclosure::new(
                lo.lower,
                hi.upper,
                v.rounded * base.column_scale[c as usize],
            )
            .ok_or("scaling_error_range")?;
            low_error.push(delta(exact, base.quantized[id])?);
            native_error.push(delta(exact, base.values[id])?);
        }
        let (mut line, mut group, mut tiles, mut ids, mut inputs, mut entries) =
            (vec![0], vec![0], vec![], vec![], vec![], vec![0]);
        for (t, lines) in [(false, &base.row_groups), (true, &base.column_groups)] {
            for gs in lines {
                for g in gs {
                    tiles.push(g.tile as u32);
                    for &id in &g.ids {
                        ids.push(id as u32);
                        inputs.push(if t {
                            base.row_of[id]
                        } else {
                            base.column_of[id]
                        } as u32);
                    }
                    group.push(ids.len() as u32);
                }
                line.push(tiles.len() as u32);
                entries.push(ids.len() as u32);
            }
        }
        let extra = 16u64
            .checked_mul(base.values.len() as u64)
            .and_then(|v| {
                v.checked_add(
                    4 * (line.len()
                        + group.len()
                        + tiles.len()
                        + ids.len()
                        + inputs.len()
                        + entries.len()) as u64,
                )
            })
            .ok_or("memory_overflow")?;
        if base
            .preparation_bytes
            .checked_add(extra)
            .is_none_or(|v| v > 2 << 30)
        {
            return Err("preparation_memory_limit");
        }
        let preparation_bytes = base.preparation_bytes + extra;
        Ok(Self {
            base,
            layout,
            low_error,
            native_error,
            preparation_bytes,
            line,
            group,
            group_tiles: tiles,
            ids,
            inputs,
            entries,
            origin: Arc::new(()),
        })
    }
    pub fn generation(&self, p: Promotion) -> Result<Generation, &'static str> {
        p.validate(&self.base)?;
        let initial = Promotion::new(self);
        let promoted = self
            .tiles
            .iter()
            .zip(&p.mask)
            .filter(|(_, m)| **m)
            .map(|(t, _)| t.count)
            .sum::<usize>();
        let initial_count = self
            .tiles
            .iter()
            .zip(&initial.mask)
            .filter(|(_, m)| **m)
            .map(|(t, _)| t.count)
            .sum::<usize>();
        if p.generation < initial.generation
            || p.generation == initial.generation && p != initial
            || p.generation > initial.generation && promoted <= initial_count
            || !p.native
                && (promoted * 4 > self.values.len()
                    || p.transitions > 8
                    || self.settings.policy == Policy::Uniform && p.transitions != 0)
        {
            return Err("resident_promotion_contract");
        }
        let mut constants = Vec::with_capacity(self.rows + self.columns);
        for groups in self.row_groups.iter().chain(&self.column_groups) {
            let (mut alpha, mut beta, mut mass, mut low_mass, mut tiny) = (0., 0., 0., 0., 0.);
            for g in groups {
                let low = !p.mask[g.tile];
                let gm = gamma(g.ids.len() + 1, low);
                for &id in &g.ids {
                    let a = if low {
                        self.quantized[id]
                    } else {
                        self.values[id]
                    }
                    .abs();
                    let err = if low {
                        self.low_error[id]
                    } else {
                        self.native_error[id]
                    };
                    alpha = up_add(alpha, up_add(err, up_mul(gm, a)));
                    mass = up_add(mass, a);
                    if low {
                        beta = up_add(beta, up_add(a, up_mul(gm, a)));
                        low_mass = up_add(low_mass, a);
                    }
                }
                tiny = up_add(
                    tiny,
                    (g.ids.len() + 1) as f64
                        * if low {
                            2f64.powi(-149)
                        } else {
                            f64::from_bits(1)
                        },
                );
            }
            let go = self.outer_gamma(groups);
            constants.push(Constant {
                alpha: up_add(alpha, up_mul(go, up_add(mass, alpha))),
                beta: up_add(beta, up_mul(go, up_add(low_mass, beta))),
                tiny: up_add(
                    up_add(tiny, up_mul(go, tiny)),
                    f64::from_bits(groups.len() as u64 + 1),
                ),
            });
        }
        Ok(Generation {
            promotion: p,
            constants,
            origin: Arc::clone(&self.origin),
            token: Arc::new(()),
        })
    }
    fn outer_gamma(&self, groups: &[quant::Group]) -> f64 {
        gamma(
            if self.layout == Layout::Segmented {
                groups.len() + 2
            } else {
                groups.iter().map(|g| g.ids.len()).sum::<usize>() + 8
            },
            false,
        )
    }
    pub fn product(&self, g: &Generation, t: bool, v: &[f64]) -> Result<Product, String> {
        if !g.matches(self) {
            return Err("stale_operator".into());
        }
        if v.len() != if t { self.rows } else { self.columns } || v.iter().any(|x| !x.is_finite()) {
            return Err("vector_shape_range".into());
        }
        let groups = if t {
            &self.column_groups
        } else {
            &self.row_groups
        };
        let scale = if t {
            &self.column_scale
        } else {
            &self.row_scale
        };
        let max = v.iter().fold(0f64, |a, x| a.max(x.abs()));
        let conversion = if g.promotion.native {
            0.
        } else {
            v.iter().fold(0f64, |a, &x| a.max(cast_error(x)))
        };
        let mut output = Vec::with_capacity(groups.len());
        let mut bounds = vec![];
        let mut flags = vec![];
        let mut counts = Counts::default();
        for (i, groups) in groups.iter().enumerate() {
            let c = g.constants[if t { self.rows + i } else { i }];
            let coarse = up_add(
                up_div(
                    up_add(
                        up_add(up_mul(c.alpha, max), up_mul(c.beta, conversion)),
                        c.tiny,
                    ),
                    scale[i],
                ),
                f64::from_bits(1),
            );
            let detailed = coarse > quant::BUDGET || !coarse.is_finite();
            let (mut total, mut bound, mut mass, mut flag) = (0., 0., 0., 0u32);
            let mut bridge = [0f64; 32];
            let mut entry = 0;
            for group in groups {
                let low = !g.promotion.mask[group.tile];
                let (mut sum, mut b, mut abs) = (0., 0., 0.);
                for &id in &group.ids {
                    let x = v[if t {
                        self.row_of[id]
                    } else {
                        self.column_of[id]
                    }];
                    let a = if low {
                        self.quantized[id]
                    } else {
                        self.values[id]
                    };
                    let vx = if low { f64::from(x as f32) } else { x };
                    let product = if low {
                        f64::from((a as f32) * (vx as f32))
                    } else {
                        a * vx
                    };
                    if low {
                        counts.low += 1;
                        if x != 0. {
                            if t {
                                counts.nonzero_t += 1;
                            } else {
                                counts.nonzero_f += 1;
                            }
                        }
                    } else {
                        counts.high += 1;
                    }
                    if !vx.is_finite()
                        || x != 0. && vx == 0.
                        || !product.is_finite()
                        || a != 0. && vx != 0. && product == 0.
                    {
                        flag |= if low { 4 } else { 2 };
                    }
                    sum = if low {
                        f64::from(sum as f32 + product as f32)
                    } else {
                        sum + product
                    };
                    if !sum.is_finite() {
                        flag |= if low { 4 } else { 2 };
                    }
                    if self.layout != Layout::Segmented {
                        bridge[entry % 32] += product;
                        entry += 1;
                    }
                    if detailed {
                        let err = if low {
                            self.low_error[id]
                        } else {
                            self.native_error[id]
                        };
                        b = up_add(b, up_mul(err, x.abs()));
                        if low {
                            b = up_add(b, up_mul(a.abs(), cast_error(x)));
                        }
                        abs = up_add(abs, up_mul(a.abs(), vx.abs()));
                    }
                }
                total += sum;
                if detailed {
                    b = up_add(b, up_mul(gamma(group.ids.len() + 1, low), abs));
                    b = up_add(
                        b,
                        (group.ids.len() + 1) as f64
                            * if low {
                                2f64.powi(-149)
                            } else {
                                f64::from_bits(1)
                            },
                    );
                    bound = up_add(bound, b);
                    mass = up_add(mass, abs);
                }
            }
            if self.layout != Layout::Segmented {
                for offset in [16, 8, 4, 2, 1] {
                    for lane in 0..offset {
                        bridge[lane] += bridge[lane + offset];
                    }
                }
                total = bridge[0];
            }
            let bound = if detailed {
                up_add(
                    up_div(
                        up_add(
                            up_add(bound, up_mul(self.outer_gamma(groups), up_add(mass, bound))),
                            f64::from_bits(groups.len() as u64 + 1),
                        ),
                        scale[i],
                    ),
                    f64::from_bits(1),
                )
            } else {
                coarse
            };
            if detailed {
                if bound <= quant::BUDGET {
                    counts.detailed_pass += 1;
                } else {
                    counts.detailed_fail += 1;
                }
            } else {
                counts.coarse_pass += 1;
            }
            if bound > quant::BUDGET || !bound.is_finite() {
                flag |= 1;
            }
            if !total.is_finite() && flag & 4 == 0 {
                flag |= 2;
            }
            output.push(total);
            bounds.push(bound);
            flags.push(flag);
        }
        if self.layout == Layout::Tuned {
            counts.guard_products = counts.high;
            counts.high *= 2;
        }
        if self.layout == Layout::OriginalTuned {
            for flag in &mut flags {
                *flag &= !1;
            }
            counts.coarse_pass = 0;
            counts.detailed_pass = 0;
            counts.detailed_fail = 0;
        }
        Ok(Product {
            output,
            bounds,
            flags,
            counts,
        })
    }
    pub fn bad_tiles(&self, g: &Generation, t: bool, flags: &[u32]) -> Vec<usize> {
        let groups = if t {
            &self.column_groups
        } else {
            &self.row_groups
        };
        groups
            .iter()
            .zip(flags)
            .filter(|(_, f)| **f != 0)
            .flat_map(|(gs, _)| {
                gs.iter()
                    .filter(|x| !g.promotion.mask[x.tile])
                    .map(|x| x.tile)
            })
            .collect::<BTreeSet<_>>()
            .into_iter()
            .collect()
    }
}
pub fn cast_error(x: f64) -> f64 {
    let f = f64::from(x as f32);
    if !f.is_finite() {
        f64::INFINITY
    } else if x == f {
        0.
    } else {
        (x - f).abs().next_up()
    }
}
pub struct Generation {
    promotion: Promotion,
    constants: Vec<Constant>,
    origin: Arc<()>,
    token: Arc<()>,
}
impl Generation {
    pub fn promotion(&self) -> &Promotion {
        &self.promotion
    }
    pub fn constants(&self) -> &[Constant] {
        &self.constants
    }
    pub fn identity(&self) -> Arc<()> {
        Arc::clone(&self.token)
    }
    pub fn matches(&self, op: &Operator) -> bool {
        Arc::ptr_eq(&self.origin, &op.origin)
    }
}
#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Counts {
    pub low: u64,
    pub high: u64,
    pub guard_products: u64,
    pub nonzero_t: u64,
    pub nonzero_f: u64,
    pub coarse_pass: u64,
    pub detailed_pass: u64,
    pub detailed_fail: u64,
    pub predicated: u64,
    pub accepted_nonzero_t: u64,
    pub accepted_nonzero_f: u64,
    pub useful_windows: u64,
    pub windows: u64,
    pub uncertain: u64,
}
impl Counts {
    pub fn add(&mut self, b: &Self) {
        self.low += b.low;
        self.high += b.high;
        self.guard_products += b.guard_products;
        self.nonzero_t += b.nonzero_t;
        self.nonzero_f += b.nonzero_f;
        self.coarse_pass += b.coarse_pass;
        self.detailed_pass += b.detailed_pass;
        self.detailed_fail += b.detailed_fail;
        self.predicated += b.predicated;
        self.windows += b.windows;
        self.uncertain += b.uncertain;
    }
}
pub struct Product {
    pub output: Vec<f64>,
    pub bounds: Vec<f64>,
    pub flags: Vec<u32>,
    pub counts: Counts,
}
pub struct Window {
    pub primal: Vec<f64>,
    pub dual: Vec<f64>,
    pub pre: Option<Fp64State>,
    pub started: u64,
    pub bad: Vec<usize>,
    pub failure: Option<String>,
    pub counts: Counts,
}
pub trait Oracle {
    fn window(
        &mut self,
        e: &Engine<'_>,
        op: &Operator,
        g: &Generation,
        s: &Fp64State,
        len: u64,
    ) -> Result<Window, String>;
}
fn valid_window(a: &Window, op: &Operator, s: &Fp64State, len: u64) -> bool {
    let finite = |v: &[f64], n: usize| v.len() == n && v.iter().all(|x| x.is_finite());
    if a.started == 0
        || a.started > len
        || a.counts.windows != 1
        || a.counts.predicated != len - a.started
        || a.counts.low.checked_add(a.counts.high).is_none_or(|n| {
            n > (if op.layout == Layout::Tuned { 4 } else { 2 })
                * op.values.len() as u64
                * a.started
        })
        || a.bad.iter().any(|&i| i >= op.tiles.len())
        || a.bad.windows(2).any(|p| p[0] >= p[1])
    {
        return false;
    }
    if a.failure.is_some() {
        return true;
    }
    if a.started != len
        || !a.bad.is_empty()
        || !finite(&a.primal, op.columns)
        || !finite(&a.dual, op.rows)
    {
        return false;
    }
    if !op.layout.audits() {
        return true;
    }
    a.pre.as_ref().is_some_and(|pre| {
        finite(&pre.primal, op.columns)
            && finite(&pre.dual, op.rows)
            && pre.iterations == s.iterations + len - 1
            && pre.since_restart == s.since_restart + len - 1
            && pre.weight.to_bits() == s.weight.to_bits()
    })
}
pub struct HostOracle;
fn checked(a: f64, b: f64) -> Result<f64, String> {
    let v = a * b;
    if !v.is_finite() || a != 0. && b != 0. && v == 0. {
        Err("resident_update_range".into())
    } else {
        Ok(v)
    }
}
fn finite(v: f64) -> Result<f64, String> {
    if v.is_finite() {
        Ok(v)
    } else {
        Err("resident_update_range".into())
    }
}
fn proposal(
    e: &Engine<'_>,
    s: &Fp64State,
    mut product: impl FnMut(bool, &[f64]) -> Result<Vec<f64>, String>,
) -> Result<(Vec<f64>, Vec<f64>), String> {
    let aty = product(true, &s.dual)?;
    let (ps, ds) = (e.step() / s.weight, e.step() * s.weight);
    if !ps.is_finite() || !ds.is_finite() || ps == 0. || ds == 0. {
        return Err("resident_update_range".into());
    }
    let (xl, xu) = e.scaled_column_bounds();
    let (yl, yu) = e.scaled_row_bounds();
    let toward = (s.since_restart + 1) as f64 / (s.since_restart + 2) as f64;
    let back = 1. / (s.since_restart + 2) as f64;
    let mut x = vec![0.; s.primal.len()];
    let mut bar = x.clone();
    for j in 0..x.len() {
        let diff = finite(e.scaled_objective()[j] - aty[j])?;
        let next = finite(s.primal[j] - checked(ps, diff)?)?
            .max(xl[j])
            .min(xu[j]);
        bar[j] = finite(2. * next - s.primal[j])?;
        x[j] = finite(checked(toward, next)? + checked(back, s.anchor_primal[j])?)?;
    }
    let ax = product(false, &bar)?;
    let mut y = vec![0.; s.dual.len()];
    for j in 0..y.len() {
        let raw = finite(s.dual[j] - checked(ds, ax[j])?)?;
        let v = finite(raw / ds)?.max(-yu[j]).min(-yl[j]);
        let next = finite(raw - checked(ds, v)?)?;
        y[j] = finite(checked(toward, next)? + checked(back, s.anchor_dual[j])?)?;
    }
    Ok((x, y))
}
impl Oracle for HostOracle {
    fn window(
        &mut self,
        e: &Engine<'_>,
        op: &Operator,
        g: &Generation,
        s: &Fp64State,
        len: u64,
    ) -> Result<Window, String> {
        let mut w = Window {
            primal: s.primal.clone(),
            dual: s.dual.clone(),
            pre: None,
            started: 0,
            bad: vec![],
            failure: None,
            counts: Counts {
                windows: 1,
                ..Counts::default()
            },
        };
        let mut state = s.clone();
        for k in 0..len {
            w.started += 1;
            if k + 1 == len {
                w.pre = Some(state.clone());
            }
            let result = proposal(e, &state, |t, v| {
                let p = op.product(g, t, v)?;
                w.counts.add(&p.counts);
                if p.flags.iter().any(|f| *f != 0) {
                    w.bad = op.bad_tiles(g, t, &p.flags);
                    Err(if p.flags.iter().any(|f| f & 2 != 0) {
                        "resident_product_range"
                    } else if w.bad.is_empty() {
                        "native_operator_error_budget"
                    } else {
                        "operator_error_budget"
                    }
                    .into())
                } else {
                    Ok(p.output)
                }
            });
            match result {
                Ok((x, y)) => {
                    state.primal = x;
                    state.dual = y;
                    state.iterations += 1;
                    state.since_restart += 1;
                }
                Err(f) => {
                    w.failure = Some(f);
                    break;
                }
            }
        }
        w.counts.predicated = len - w.started;
        w.primal = state.primal;
        w.dual = state.dual;
        Ok(w)
    }
}
#[derive(Clone)]
pub struct Checkpoint<'e, 'p> {
    origin: Arc<()>,
    controller: Fp64Checkpoint<'e, 'p>,
    generation: Arc<Generation>,
}
pub struct Session<'e, 'p> {
    origin: Arc<()>,
    pub controller: Fp64Controller<'e, 'p>,
    generation: Arc<Generation>,
}
impl<'e, 'p> Session<'e, 'p> {
    pub fn new(
        e: &'e Engine<'p>,
        op: &Operator,
        deadline: Option<Instant>,
    ) -> Result<Self, &'static str> {
        let mut controller = Fp64Controller::new(e);
        controller.set_deadline(deadline);
        Ok(Self {
            origin: Arc::new(()),
            controller,
            generation: Arc::new(op.generation(Promotion::new(op))?),
        })
    }
    pub fn checkpoint(&self) -> Checkpoint<'e, 'p> {
        Checkpoint {
            origin: Arc::clone(&self.origin),
            controller: self.controller.checkpoint(),
            generation: Arc::clone(&self.generation),
        }
    }
    pub fn restore(&mut self, c: &Checkpoint<'e, 'p>) -> Result<(), &'static str> {
        if !Arc::ptr_eq(&self.origin, &c.origin) {
            return Err("resident_checkpoint_session");
        }
        self.controller.restore(&c.controller)?;
        self.generation = Arc::clone(&c.generation);
        Ok(())
    }
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Outcome {
    pub core: quant::Outcome,
    pub counts: Counts,
    pub layout: Layout,
    pub guard: String,
    pub reduction: String,
    pub horizon: u64,
    pub first_certified_iteration: Option<u64>,
}

#[allow(clippy::too_many_arguments)]
pub fn run<O: Oracle>(
    e: &Engine<'_>,
    op: &Operator,
    o: &mut O,
    horizon: u64,
    cancel: &CancellationToken,
    deadline: Option<Instant>,
    mut assess: impl FnMut(&[f64], &[f64]) -> bool,
) -> Outcome {
    let _cost = optimizer_core::lp_cost::scope("resident_solve_loop");
    let mut s = Session::new(e, op, deadline).expect("prepared operator");
    let mut w = quant::Work::default();
    let mut counts = Counts::default();
    let mut transitions = vec![];
    let (mut stop, mut failure) = ("iteration_limit".to_string(), None);
    w.assessments += 1;
    let initial = assess(
        &e.unscale_primal(&s.controller.state().primal),
        &e.unscale_dual(&s.controller.state().dual),
    );
    let mut first_certified_iteration =
        if initial && !cancel.is_cancelled() && !s.controller.expired() {
            Some(0)
        } else {
            None
        };
    if initial && horizon == 0 {
        stop = "certified".into();
    } else {
        'solve: while s.controller.remaining() > u64::from(op.layout.audits()) {
            if horizon != 0 && s.controller.state().iterations == horizon {
                stop = "work_horizon".into();
                break;
            }
            if cancel.is_cancelled() || s.controller.expired() {
                stop = if cancel.is_cancelled() {
                    "interrupted"
                } else {
                    "time_limit"
                }
                .into();
                break;
            }
            let cp = s.checkpoint();
            let start = s.controller.state().iterations;
            let mut len = s
                .controller
                .next_chunk(if op.layout == Layout::OriginalTuned {
                    200
                } else {
                    32
                })
                .min(s.controller.remaining() - u64::from(op.layout.audits()));
            if horizon != 0 {
                len = len.min(horizon - start);
            }
            if len == 0 {
                break;
            }
            let mut replay = false;
            loop {
                if s.controller.remaining() < len + u64::from(op.layout.audits()) {
                    break 'solve;
                }
                let attempt = match o.window(e, op, &s.generation, s.controller.state(), len) {
                    Ok(a) => a,
                    Err(err) => {
                        w.proposals += len;
                        if replay {
                            w.replays += len;
                        }
                        counts.uncertain += len;
                        counts.windows += 1;
                        s.controller
                            .charge_extra(len)
                            .expect("uncertain window allowance");
                        stop = "device_failure".into();
                        failure = Some(err);
                        break 'solve;
                    }
                };
                if !valid_window(&attempt, op, s.controller.state(), len) {
                    w.proposals += len;
                    if replay {
                        w.replays += len;
                    }
                    counts.uncertain += len;
                    counts.windows += 1;
                    s.controller
                        .charge_extra(len)
                        .expect("invalid window allowance");
                    stop = "device_failure".into();
                    failure = Some("resident_invalid_window".into());
                    break 'solve;
                }
                w.proposals += attempt.started;
                if replay {
                    w.replays += attempt.started;
                }
                counts.add(&attempt.counts);
                if attempt.failure.is_none() && attempt.started == len {
                    s.controller
                        .replace_endpoint(attempt.primal.clone(), attempt.dual.clone())
                        .expect("finite window endpoint");
                    s.controller
                        .commit_steps(attempt.started)
                        .expect("window allowance");
                } else {
                    s.controller
                        .charge_extra(attempt.started)
                        .expect("rejected allowance");
                }
                let mut why = attempt.failure;
                let mut bad = attempt.bad;
                if cancel.is_cancelled() || s.controller.expired() {
                    let saved_generation = Arc::clone(&s.generation);
                    s.restore(&cp).unwrap();
                    s.generation = saved_generation;
                    stop = if cancel.is_cancelled() {
                        "interrupted"
                    } else {
                        "time_limit"
                    }
                    .into();
                    break 'solve;
                }
                if why.is_none() && op.layout.audits() {
                    let _audit = optimizer_core::lp_cost::scope("resident_host_audit");
                    w.audits += 1;
                    s.controller.charge_extra(1).expect("audit allowance");
                    match crate::precision::correction(
                        e,
                        attempt.pre.as_ref().expect("full window pre-step"),
                    ) {
                        Ok((x, y)) => {
                            let pre = attempt.pre.as_ref().unwrap();
                            let mut pass = true;
                            for (low, reference, before, scale) in [
                                (
                                    &attempt.primal,
                                    &x,
                                    &pre.primal,
                                    e.preconditioner().column(),
                                ),
                                (&attempt.dual, &y, &pre.dual, e.preconditioner().row()),
                            ] {
                                for (((&l, &h), &b), &scale) in
                                    low.iter().zip(reference).zip(before).zip(scale)
                                {
                                    let (l, h, b) = (l * scale, h * scale, b * scale);
                                    let a = quant::BUDGET + quant::BUDGET * b.abs().max(h.abs());
                                    pass &= l.is_finite()
                                        && h.is_finite()
                                        && b.is_finite()
                                        && a.is_finite()
                                        && (l - h).abs() <= a;
                                }
                            }
                            if pass {
                                s.controller
                                    .replace_endpoint(x, y)
                                    .expect("reference finite");
                            } else {
                                why = Some("audit_error".into());
                                bad = (0..op.tiles.len())
                                    .filter(|&i| !s.generation.promotion.mask[i])
                                    .collect();
                            }
                        }
                        Err(err) => why = Some(err.into()),
                    }
                } else if why.is_none() {
                    s.controller
                        .replace_endpoint(attempt.primal, attempt.dual)
                        .expect("finite device endpoint");
                }
                if cancel.is_cancelled() || s.controller.expired() {
                    let saved_generation = Arc::clone(&s.generation);
                    s.restore(&cp).unwrap();
                    s.generation = saved_generation;
                    stop = if cancel.is_cancelled() {
                        "interrupted"
                    } else {
                        "time_limit"
                    }
                    .into();
                    break 'solve;
                }
                if let Some(reason) = why {
                    let mut p = s.generation.promotion.clone();
                    let promoted = !bad.is_empty() && p.promote(op, &bad);
                    let saved_generation = Arc::clone(&s.generation);
                    s.restore(&cp).unwrap();
                    s.generation = saved_generation;
                    if !promoted {
                        stop = "numerical_failure".into();
                        failure = Some(reason);
                        break 'solve;
                    }
                    s.generation = Arc::new(op.generation(p).expect("valid promotion"));
                    transitions.push(quant::Transition {
                        iteration: start,
                        generation: s.generation.promotion.generation,
                        reason,
                        promoted_coefficients: op
                            .tiles
                            .iter()
                            .zip(&s.generation.promotion.mask)
                            .filter(|(_, m)| **m)
                            .map(|(t, _)| t.count as u64)
                            .sum(),
                        native: s.generation.promotion.native,
                    });
                    replay = true;
                    continue;
                }
                if e.unscale_primal(&s.controller.state().primal)
                    .iter()
                    .chain(&e.unscale_dual(&s.controller.state().dual))
                    .any(|v| !v.is_finite())
                {
                    let saved_generation = Arc::clone(&s.generation);
                    s.restore(&cp).unwrap();
                    s.generation = saved_generation;
                    stop = "numerical_failure".into();
                    failure = Some("original_point_unscaling_range".into());
                    break 'solve;
                }
                counts.accepted_nonzero_t += attempt.counts.nonzero_t;
                counts.accepted_nonzero_f += attempt.counts.nonzero_f;
                if len == 32
                    && attempt.counts.nonzero_t > 0
                    && attempt.counts.nonzero_f > 0
                    && !s.generation.promotion.native
                {
                    counts.useful_windows += 1;
                }
                break;
            }
            if s.controller.check_pending() {
                w.assessments += 1;
                let closed = assess(
                    &e.unscale_primal(&s.controller.state().primal),
                    &e.unscale_dual(&s.controller.state().dual),
                );
                if closed
                    && first_certified_iteration.is_none()
                    && !cancel.is_cancelled()
                    && !s.controller.expired()
                {
                    first_certified_iteration = Some(s.controller.state().iterations);
                }
                if closed && horizon == 0 {
                    stop = "certified".into();
                    break;
                }
                s.controller.continue_after_check();
            }
        }
    }
    if failure.is_none() {
        if cancel.is_cancelled() {
            stop = "interrupted".into();
        } else if s.controller.expired() {
            stop = "time_limit".into();
        }
    }
    if horizon != 0 && s.controller.state().iterations == horizon && stop == "iteration_limit" {
        stop = "work_horizon".into();
    }
    let point = s.controller.state();
    w.low_products = counts.low;
    w.high_products = counts.high;
    w.rejected = w.proposals - point.iterations;
    let primal = e.unscale_primal(&point.primal);
    let dual = e.unscale_dual(&point.dual);
    w.assessments += 1;
    let closed = assess(&primal, &dual);
    if closed
        && first_certified_iteration.is_none()
        && !cancel.is_cancelled()
        && !s.controller.expired()
    {
        first_certified_iteration = Some(point.iterations);
    }
    if closed && stop == "iteration_limit" && horizon == 0 {
        stop = "certified".into();
    }
    Outcome {
        core: quant::Outcome {
            primal,
            dual,
            scaled_primal: point.primal.clone(),
            scaled_dual: point.dual.clone(),
            iterations: point.iterations,
            physical: s.controller.physical_iterations(),
            stop,
            failure,
            work: w,
            promotion: s.generation.promotion.clone(),
            transitions,
            norm: op.norm,
            step: e.step(),
        },
        counts,
        layout: op.layout,
        guard: op.layout.guard().into(),
        reduction: op.layout.tree().into(),
        horizon,
        first_certified_iteration,
    }
}
