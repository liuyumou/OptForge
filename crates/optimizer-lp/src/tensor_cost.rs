//! ADR-0044 resident windows and independently bounded sparse arithmetic.
#![allow(missing_docs)]
use crate::{
    Engine,
    control::{Fp64Checkpoint, Fp64Controller, Fp64State},
    quant,
};
use optimizer_core::CancellationToken;
pub use quant::{Format, Policy, Promotion, Settings};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use std::{collections::BTreeSet, sync::Arc, time::Instant};

use crate::tensor_cost_prepare::CompactBase;
pub use crate::tensor_cost_prepare::NormProof;
pub fn norm_block(block: &[f64]) -> Option<f64> {
    crate::tensor_cost_prepare::gram_bound(block)
}
pub const ID: &str = "lp-tensor-cost-v1";
pub const GUARD: &str = "tensor-cost-successor-bound-v1";
pub const TREE: &str = "exact-tile128-residual-fp64-v1";
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Layout {
    Segmented,
    Tuned,
    OriginalTuned,
    Int8,
    Fp16,
    Bf16,
    Simt,
}
impl Layout {
    pub fn tensor(self) -> bool {
        matches!(self, Self::Int8 | Self::Fp16 | Self::Bf16 | Self::Simt)
    }
    pub fn mode(self) -> u32 {
        match self {
            Self::Int8 => 0,
            Self::Fp16 => 1,
            Self::Bf16 => 2,
            _ => 3,
        }
    }
    pub fn audits(self) -> bool {
        self != Self::OriginalTuned
    }
    pub fn guard(self) -> &'static str {
        if self == Self::OriginalTuned {
            "none-original-tuned-v1"
        } else {
            "tensor-cost-successor-bound-v1"
        }
    }
    pub fn tree(self) -> &'static str {
        if self != Self::OriginalTuned {
            "exact-tile128-residual-fp64-v1"
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
#[derive(Clone, Copy, Debug, Default)]
pub struct Constant {
    pub alpha: f64,
    pub beta: f64,
    pub tiny: f64,
}
/// A generation binds immutable coefficients, sparse layout and error summaries.
///
/// ```compile_fail
/// fn corrupt(mut op: optimizer_lp::tensor_cost::Operator) {
///     op.low_error[0] = 0.0;
///     op.base.quantized[0] = 0.0;
/// }
/// ```
pub struct Operator {
    data: OperatorData,
    origin: Arc<()>,
}
/// Immutable operator data, accessible through shared dereferencing only.
pub struct OperatorData {
    pub base: CompactBase,
    pub norm_proof: NormProof,
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
    pub selected: Vec<i32>,
    pub dense: Vec<i64>,
    pub dense_exponents: Vec<i32>,
    pub dense_rows: Vec<u32>,
    pub dense_columns: Vec<u32>,
    pub represented: Vec<f64>,
    pub representation_error: Vec<f64>,
}
impl std::ops::Deref for Operator {
    type Target = OperatorData;
    fn deref(&self) -> &Self::Target {
        &self.data
    }
}
impl std::ops::Deref for OperatorData {
    type Target = CompactBase;
    fn deref(&self) -> &Self::Target {
        &self.base
    }
}
impl Operator {
    pub fn new(e: &Engine<'_>, settings: Settings, layout: Layout) -> Result<Self, &'static str> {
        let _cost = optimizer_core::lp_cost::scope("resident_pack_metadata_norm");
        if settings.format != Format::Fp64 || settings.policy != Policy::Uniform {
            return Err("resident_layout_format");
        }
        let (mut base, low_error, native_error) = crate::tensor_cost_prepare::prepare(e, settings)?;
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
        let mut selected = vec![-1; base.tiles.len()];
        let mut dense = vec![];
        let mut dense_exponents = vec![];
        let mut dense_rows = vec![];
        let mut dense_columns = vec![];
        let mut represented = base.values.clone();
        let mut representation_error = low_error.clone();
        let mut by_tile = BTreeMap::<usize, Vec<usize>>::new();
        for (id, &tile) in base.tile_of.iter().enumerate() {
            by_tile.entry(tile).or_default().push(id);
        }
        for (tile, ids) in by_tile {
            if base.tiles[tile].count < 512 {
                continue;
            }
            let exponent = block_exponent(ids.iter().map(|&id| base.values[id]))?;
            selected[tile] = dense_exponents.len() as i32;
            let first = ids[0];
            dense_rows.push((base.row_of[first] / 32) as u32);
            dense_columns.push((base.column_of[first] / 32) as u32);
            dense_exponents.push(exponent);
            let begin = dense.len();
            dense.resize(begin + 1024, 0);
            for id in ids {
                let q = encode(base.values[id], exponent)?;
                if base.values[id] != 0. && q == 0 {
                    return Err("tensor_matrix_lost_nonzero");
                }
                dense[begin + (base.row_of[id] % 32) * 32 + base.column_of[id] % 32] = q;
                let decoded = round_dot(i128::from(q), exponent - 56)?.0;
                represented[id] = decoded;
                representation_error[id] =
                    up_add(native_error[id], (base.values[id] - decoded).abs());
            }
        }
        let extra = extra
            .checked_add(
                (dense.len() * 8
                    + selected.len() * 4
                    + represented.len() * 16
                    + dense_exponents.len() * 12) as u64,
            )
            .ok_or("preparation_memory_overflow")?;
        let preparation_bytes = base
            .preparation_bytes
            .checked_add(extra)
            .ok_or("preparation_memory_overflow")?;
        if preparation_bytes > 2 << 30 {
            return Err("preparation_memory_limit");
        }
        let norm_proof = crate::tensor_cost_prepare::tighten(
            &mut base,
            &selected,
            &dense,
            &dense_exponents,
            &represented,
            &representation_error,
        );
        base.data.step = if base.norm == 0. {
            e.step()
        } else {
            e.step().min((0.9f64.next_down() / base.norm).next_down())
        };
        Ok(Self {
            data: OperatorData {
                base,
                norm_proof,
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
                selected,
                dense,
                dense_exponents,
                dense_rows,
                dense_columns,
                represented,
                representation_error,
            },
            origin: Arc::new(()),
        })
    }
    pub fn promote(&self, p: &mut Promotion, ids: &[usize]) -> bool {
        if p.native || ids.is_empty() || ids.iter().any(|&i| i >= p.mask.len()) {
            return false;
        }
        p.mask.fill(true);
        p.native = true;
        p.generation += 1;
        p.transitions += 1;
        true
    }
    pub fn initial(&self) -> Promotion {
        let mask = self
            .selected
            .iter()
            .map(|&v| !self.layout.tensor() || v < 0)
            .collect::<Vec<_>>();
        Promotion {
            native: mask.iter().all(|m| *m),
            mask,
            generation: 0,
            transitions: 0,
        }
    }
    pub fn generation(&self, p: Promotion) -> Result<Generation, &'static str> {
        if p.mask.len() != self.tiles.len() || p.native && p.mask.iter().any(|m| !*m) {
            return Err("operator_generation");
        }
        let initial = self.initial();
        if p.transitions > 1
            || p.generation != p.transitions
            || (p.transitions == 0 && p != initial)
            || (p.transitions == 1 && (!p.native || p.mask.iter().any(|m| !*m)))
        {
            return Err("tensor_promotion_contract");
        }
        let mut constants = vec![];
        for groups in self.row_groups.iter().chain(&self.column_groups) {
            let (mut alpha, mut beta, mut mass, mut tiny) = (0., 0., 0., 0.);
            for group in groups {
                let low = !p.mask[group.tile];
                for &id in &group.ids {
                    let a = if low {
                        self.represented[id]
                    } else {
                        self.values[id]
                    }
                    .abs();
                    alpha = up_add(
                        alpha,
                        if low {
                            self.representation_error[id]
                        } else {
                            self.native_error[id]
                        },
                    );
                    mass = up_add(mass, a);
                    // Native serial arithmetic and exact-dot final rounding are both enclosed.
                    alpha = up_add(
                        alpha,
                        up_mul(gamma(group.ids.len() + if low { 4 } else { 1 }, false), a),
                    );
                    if low {
                        beta = up_add(beta, 0.);
                    }
                }
                tiny = up_add(
                    tiny,
                    f64::from_bits((group.ids.len() + if low { 4 } else { 1 }) as u64),
                );
            }
            let outer = gamma(groups.len() + 2, false);
            constants.push(Constant {
                alpha: up_add(alpha, up_mul(outer, up_add(mass, alpha))),
                beta: up_mul(beta, up_add(1., outer)),
                tiny: up_add(
                    up_mul(tiny, up_add(1., outer)),
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
        let scales = if t {
            &self.column_scale
        } else {
            &self.row_scale
        };
        let max = v.iter().fold(0f64, |m, x| m.max(x.abs()));
        let conversion = if g.promotion.native || max == 0. {
            0.
        } else {
            unit_bound(block_exponent([max]).map_err(str::to_string)? - 56)
        };
        let mut packed = Vec::new();
        let mut exponents = vec![];
        let mut range = vec![];
        let mut residual = Vec::with_capacity(v.len());
        for block in v.chunks(32) {
            let e = block_exponent(block.iter().copied()).map_err(str::to_string)?;
            exponents.push(e);
            let mut bad = false;
            for &x in block {
                match encode(x, e) {
                    Ok(q) => {
                        packed.push(q);
                        let main = round_dot(i128::from(q), e - 56).map_err(str::to_string)?.0;
                        let tail = x - main;
                        if !tail.is_finite() {
                            return Err("tensor_cost_range".into());
                        }
                        residual.push(tail);
                    }
                    Err(_) => {
                        packed.push(0);
                        residual.push(0.);
                        bad = true;
                    }
                }
            }
            range.push(bad);
        }
        let (mut output, mut bounds, mut flags, mut counts) =
            (vec![], vec![], vec![], Counts::default());
        for (row, groups) in groups.iter().enumerate() {
            let mut total = 0.;
            let mut flag = 0;
            for group in groups {
                let low = !g.promotion.mask[group.tile];
                let mut sum = 0.;
                let mut exact = 0i128;
                let mut correction = 0.;
                let exponent = if low {
                    self.dense_exponents[self.selected[group.tile] as usize]
                } else {
                    0
                };
                let mut ve = 0;
                for &id in &group.ids {
                    let index = if t {
                        self.row_of[id]
                    } else {
                        self.column_of[id]
                    };
                    let x = v[index];
                    if low {
                        counts.low += 1;
                        if packed[index] != 0 {
                            if t {
                                counts.nonzero_t += 1;
                            } else {
                                counts.nonzero_f += 1;
                            }
                        }
                        if range[index / 32] {
                            flag |= 4;
                        }
                        let tile = self.selected[group.tile] as usize;
                        let a = self.dense
                            [tile * 1024 + (self.row_of[id] % 32) * 32 + self.column_of[id] % 32];
                        exact += i128::from(a) * i128::from(packed[index]);
                        if residual[index] != 0. {
                            counts.residual_products += 1;
                            let product = self.represented[id] * residual[index];
                            if !product.is_finite() || self.represented[id] != 0. && product == 0. {
                                flag |= 4;
                            }
                            correction += product;
                            if !correction.is_finite() {
                                flag |= 4;
                            }
                        }
                        ve = exponents[index / 32];
                    } else {
                        counts.high += 1;
                        let product = self.values[id] * x;
                        if !product.is_finite() || self.values[id] != 0. && x != 0. && product == 0.
                        {
                            flag |= 2;
                        }
                        sum += product;
                    }
                }
                if low {
                    match round_dot(exact, exponent + ve - 112) {
                        Ok((x, _)) => {
                            sum = x + correction;
                            if !sum.is_finite() {
                                flag |= 4;
                            }
                        }
                        Err(_) => flag |= 4,
                    };
                }
                total += sum;
                if !total.is_finite() {
                    flag |= if low { 4 } else { 2 };
                }
            }
            let c = g.constants[if t { self.rows + row } else { row }];
            let bound = up_add(
                up_div(
                    up_add(
                        up_add(up_mul(c.alpha, max), up_mul(c.beta, conversion)),
                        c.tiny,
                    ),
                    scales[row],
                ),
                f64::from_bits(1),
            );
            if !bound.is_finite() || bound > quant::BUDGET {
                flag |= 1;
                counts.detailed_fail += 1;
            } else {
                counts.coarse_pass += 1;
            }
            output.push(total);
            bounds.push(bound);
            flags.push(flag);
        }
        if !g.promotion.native {
            let tiles = self.dense_exponents.len() as u64;
            counts.component_products = tiles
                * 1024
                * if self.layout == Layout::Bf16 {
                    14 * 14
                } else if self.layout == Layout::Simt {
                    1
                } else {
                    8 * 8
                };
            counts.mma_instructions = tiles
                * match self.layout {
                    Layout::Int8 => 16,
                    Layout::Fp16 => 32,
                    Layout::Bf16 => 112,
                    _ => 0,
                };
            counts.padded_products = counts.mma_instructions
                * if self.layout == Layout::Int8 {
                    4096
                } else {
                    2048
                };
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
    pub residual_products: u64,
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
    pub component_products: u64,
    pub mma_instructions: u64,
    pub padded_products: u64,
}
impl Counts {
    pub fn add(&mut self, b: &Self) {
        self.low += b.low;
        self.high += b.high;
        self.guard_products += b.guard_products;
        self.residual_products += b.residual_products;
        self.nonzero_t += b.nonzero_t;
        self.nonzero_f += b.nonzero_f;
        self.coarse_pass += b.coarse_pass;
        self.detailed_pass += b.detailed_pass;
        self.detailed_fail += b.detailed_fail;
        self.predicated += b.predicated;
        self.windows += b.windows;
        self.uncertain += b.uncertain;
        self.component_products += b.component_products;
        self.mma_instructions += b.mma_instructions;
        self.padded_products += b.padded_products;
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
    fn reference(&mut self, e: &Engine<'_>, s: &Fp64State) -> Result<(Vec<f64>, Vec<f64>), String> {
        crate::precision::correction(e, s).map_err(str::to_string)
    }
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
    let c = &a.counts;
    if c.residual_products > c.low
        || !physical_counts_valid(c, op, a.started)
        || a.started == 0
        || a.started > len
        || a.counts.windows != 1
        || a.counts.predicated != len - a.started
        || a.counts.low.checked_add(a.counts.high).is_none_or(|n| {
            n > (if op.layout == Layout::Tuned { 4 } else { 2 })
                * op.values.len() as u64
                * a.started
        })
        || u128::from(c.nonzero_t) + u128::from(c.nonzero_f) > u128::from(c.low)
        || u128::from(c.coarse_pass) + u128::from(c.detailed_pass) + u128::from(c.detailed_fail)
            > (op.rows + op.columns) as u128 * u128::from(a.started)
        || c.guard_products > c.high
        || op.layout != Layout::Tuned && c.guard_products != 0
        || op.layout == Layout::Tuned && c.guard_products.checked_mul(2) != Some(c.high)
        || c.mma_instructions as u128
            > op.dense_exponents.len() as u128 * 224 * u128::from(a.started)
        || c.component_products as u128
            > op.dense_exponents.len() as u128 * 1024 * 392 * u128::from(a.started)
        || c.padded_products as u128 > u128::from(c.mma_instructions) * 4096
        || c.accepted_nonzero_t != 0
        || c.accepted_nonzero_f != 0
        || c.useful_windows != 0
        || c.uncertain != 0
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
            generation: Arc::new(op.generation(op.initial())?),
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
                    match o.reference(e, attempt.pre.as_ref().expect("full window pre-step")) {
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
                        Err(err) => why = Some(err),
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
                    let promoted = !bad.is_empty() && op.promote(&mut p, &bad);
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

/// Shared block exponent, including binary64 subnormals without normalization arithmetic.
pub fn block_exponent(values: impl IntoIterator<Item = f64>) -> Result<i32, &'static str> {
    let mut exponent = -1074;
    for x in values {
        if !x.is_finite() {
            return Err("tensor_nonfinite");
        }
        let a = x.to_bits() & 0x7fff_ffff_ffff_ffff;
        if a == 0 {
            continue;
        }
        let field = (a >> 52) as i32;
        let e = if field == 0 {
            63 - a.leading_zeros() as i32 - 1074
        } else {
            field - 1023
        };
        exponent = exponent.max(e + 1);
    }
    Ok(exponent)
}
pub fn encode(x: f64, exponent: i32) -> Result<i64, &'static str> {
    if x == 0. {
        return Ok(0);
    }
    let d = crate::exec::decode(x.to_bits())?;
    let shift = d.exponent - exponent + 56;
    if shift >= 0 && (64 - d.significand.leading_zeros()) as i32 + shift > 56 {
        return Err("tensor_conversion_range");
    }
    let m = if shift >= 0 {
        u128::from(d.significand)
            .checked_shl(shift as u32)
            .ok_or("tensor_conversion_range")?
    } else {
        u128::from(d.significand)
            .checked_shr((-shift) as u32)
            .unwrap_or(0)
    };
    if m >= 1u128 << 56 {
        return Err("tensor_lost_nonzero_or_range");
    }
    let q = m as i64;
    Ok(if d.negative != 0 { -q } else { q })
}
pub fn unit_bound(exponent: i32) -> f64 {
    if exponent < -1074 {
        f64::from_bits(1)
    } else if exponent > 1023 {
        f64::INFINITY
    } else {
        crate::research::scale_pow2(1., exponent)
    }
}
/// Correct nearest-even rounding of an exact signed tile integer times 2^base.
pub fn round_dot(value: i128, base: i32) -> Result<(f64, f64), &'static str> {
    if value == 0 {
        return Ok((0., 0.));
    }
    let negative = value < 0;
    let m = value.unsigned_abs();
    let top = 127 - m.leading_zeros() as i32;
    let mut unit = (base + top - 52).max(-1074);
    let shift = unit - base;
    let (mut q, rest, half) = if shift <= 0 {
        (
            m.checked_shl((-shift) as u32).ok_or("tensor_round_range")?,
            false,
            false,
        )
    } else if shift > 128 {
        (0, true, false)
    } else if shift == 128 {
        (0, true, m >= 1u128 << 127)
    } else {
        let mask = (1u128 << shift) - 1;
        let r = m & mask;
        let h = 1u128 << (shift - 1);
        (
            m >> shift,
            r != 0,
            r > h || r == h && ((m >> shift) & 1) != 0,
        )
    };
    if half {
        q += 1;
    }
    if q == 1u128 << 53 {
        q >>= 1;
        unit += 1;
    }
    if unit > 971 || q == 0 {
        return Err("tensor_round_overflow_or_lost_nonzero");
    }
    let bits = if q < 1u128 << 52 {
        q as u64
    } else {
        ((unit + 1075) as u64) << 52 | q as u64 & ((1u64 << 52) - 1)
    };
    let out = f64::from_bits(bits | ((negative as u64) << 63));
    Ok((out, if rest { unit_bound(unit - 1) } else { 0. }))
}

/// Refuse impossible component and padded counters before window aggregation.
pub fn physical_counts_valid(c: &Counts, op: &Operator, proposals: u64) -> bool {
    if c.residual_products > c.low {
        return false;
    }
    let t = op.dense_exponents.len() as u128;
    let pairs = 2 * t * u128::from(proposals);
    let (per, slices, k) = match op.layout {
        Layout::Int8 => (16u64, 64u64, 4096u64),
        Layout::Fp16 => (32, 64, 2048),
        Layout::Bf16 => (112, 196, 2048),
        _ => (0, 0, 0),
    };
    if !op.layout.tensor() {
        return c.mma_instructions == 0
            && c.component_products == 0
            && c.padded_products == 0
            && c.low == 0;
    }
    if op.layout == Layout::Simt {
        return c.mma_instructions == 0
            && c.padded_products == 0
            && u128::from(c.component_products) <= pairs * 1024
            && c.component_products.is_multiple_of(1024);
    }
    u128::from(c.mma_instructions) <= pairs * u128::from(per)
        && c.mma_instructions.is_multiple_of(per)
        && u128::from(c.component_products)
            == u128::from(c.mma_instructions / per) * 1024 * u128::from(slices)
        && u128::from(c.padded_products) == u128::from(c.mma_instructions) * u128::from(k)
}
