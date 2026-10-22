//! ADR-0040 isolated matrix quantization. Local error admission is not certification.
#![allow(missing_docs)]
use crate::{
    Engine, LinearProgram,
    control::{Fp64Checkpoint, Fp64Controller, Fp64State},
    outward::Enclosure,
};
use optimizer_core::CancellationToken;
use serde::{Deserialize, Serialize};
use std::{
    collections::{BTreeMap, BTreeSet},
    sync::Arc,
    time::Instant,
};
pub const ID: &str = "lp-quant-v1";
pub const BUDGET: f64 = 1e-7;
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Format {
    Fp16,
    E4m3,
    E5m2,
    Fp64,
}
impl Format {
    pub fn layout(self) -> (u32, u32, i32) {
        match self {
            Self::Fp16 => (5, 10, 15),
            Self::E4m3 => (4, 3, 7),
            Self::E5m2 => (5, 2, 15),
            Self::Fp64 => (11, 52, 1023),
        }
    }
    pub fn max_code(self) -> u16 {
        match self {
            Self::Fp16 => 0x7bff,
            Self::E4m3 => 0x7e,
            Self::E5m2 => 0x7b,
            Self::Fp64 => 0,
        }
    }
    pub fn width(self) -> usize {
        if self == Self::Fp16 { 2 } else { 1 }
    }
    pub fn decode(self, code: u16) -> Result<f64, &'static str> {
        if self == Self::Fp64 {
            return Err("format_encoding");
        }
        let (eb, mb, bias) = self.layout();
        let bits = 1 + eb + mb;
        if u32::from(code) >= (1u32 << bits) {
            return Err("format_encoding");
        }
        let sign = code & (1 << (bits - 1)) != 0;
        let mag = code & ((1 << (bits - 1)) - 1);
        if mag > self.max_code() {
            return Err("format_nonfinite");
        }
        let e = (u32::from(mag) >> mb) as i32;
        let m = u32::from(mag) & ((1 << mb) - 1);
        let v = if e == 0 {
            (m as f64) * 2.0f64.powi(1 - bias - mb as i32)
        } else {
            ((1 << mb) + m) as f64 * 2.0f64.powi(e - bias - mb as i32)
        };
        Ok(if sign { -v } else { v })
    }
    /// Binary search exact dyadic neighbors; comparisons and midpoints are exact
    /// in binary64, avoiding a binary32 double-rounding intermediate.
    pub fn encode(self, x: f64) -> Result<u16, &'static str> {
        if !x.is_finite() {
            return Err("conversion_nonfinite");
        }
        if self == Self::Fp64 {
            return Err("format_encoding");
        }
        let (_, mb, _) = self.layout();
        let (eb, _, _) = self.layout();
        let sign = if x.is_sign_negative() {
            1u16 << (eb + mb)
        } else {
            0
        };
        let a = x.abs();
        let max = self.max_code();
        if a > self.decode(max)? {
            return Err("conversion_overflow");
        }
        let (mut l, mut r) = (0, max);
        while l < r {
            let mid = l + (r - l).div_ceil(2);
            if self.decode(mid)? <= a {
                l = mid;
            } else {
                r = mid - 1;
            }
        }
        let mut q = l;
        if l < max {
            let lo = self.decode(l)?;
            let hi = self.decode(l + 1)?;
            let middle = (lo + hi) * 0.5;
            if a > middle || a == middle && l & 1 != 0 {
                q = l + 1;
            }
        }
        if a != 0.0 && q == 0 {
            return Err("conversion_lost_nonzero");
        }
        Ok(sign | q)
    }
}
fn interval(x: f64) -> Result<Enclosure, &'static str> {
    Enclosure::point(x).ok_or("bound_nonfinite")
}
fn add(a: f64, b: f64) -> Result<f64, &'static str> {
    Ok(interval(a)?.add(interval(b)?).ok_or("bound_range")?.upper)
}
fn mul(a: f64, b: f64) -> Result<f64, &'static str> {
    Ok(Enclosure::product(a, b).ok_or("bound_range")?.upper)
}
fn error(a: Enclosure, b: f64) -> Result<f64, &'static str> {
    let d = a.subtract(interval(b)?).ok_or("bound_range")?;
    Ok(d.lower.abs().max(d.upper.abs()))
}
fn finite(x: f64) -> Result<f64, &'static str> {
    if x.is_finite() {
        Ok(x)
    } else {
        Err("arithmetic_nonfinite")
    }
}
fn checked_product(a: f64, b: f64, low: bool) -> Result<f64, &'static str> {
    let p = if low {
        f64::from((crate::precision::narrow(a)? as f32) * (crate::precision::narrow(b)? as f32))
    } else {
        a * b
    };
    finite(p)?;
    if a != 0.0 && b != 0.0 && p == 0.0 {
        Err("product_lost_nonzero")
    } else {
        Ok(p)
    }
}
fn blend(toward: f64, next: f64, back: f64, anchor: f64) -> Result<f64, &'static str> {
    finite(checked_product(toward, next, false)? + checked_product(back, anchor, false)?)
}
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Policy {
    Uniform,
    Selective,
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Settings {
    pub format: Format,
    pub policy: Policy,
    pub tile_size: u32,
    pub rounding: String,
    pub primal_budget: f64,
    pub dual_budget: f64,
    pub audit_interval: u64,
    pub audit_absolute: f64,
    pub audit_relative: f64,
}
impl Settings {
    pub fn new(format: Format, policy: Policy) -> Self {
        Self {
            format,
            policy,
            tile_size: 32,
            rounding: "nearest_even".into(),
            primal_budget: BUDGET,
            dual_budget: BUDGET,
            audit_interval: 32,
            audit_absolute: BUDGET,
            audit_relative: BUDGET,
        }
    }
    pub fn validate(&self) -> Result<(), &'static str> {
        if *self == Self::new(self.format, self.policy) {
            Ok(())
        } else {
            Err("quant_settings")
        }
    }
}
#[derive(Clone, Debug)]
pub struct Tile {
    pub row: u32,
    pub column: u32,
    pub exponent: i32,
    pub count: usize,
    pub forced: bool,
}
#[derive(Clone, Debug)]
pub struct Group {
    pub tile: usize,
    pub ids: Vec<usize>,
    pub error: f64,
    pub original_error: f64,
    pub mass: f64,
    pub original_mass: f64,
}
#[derive(Clone, Debug)]
pub struct Operator {
    pub settings: Settings,
    pub rows: usize,
    pub columns: usize,
    pub values: Vec<f64>,
    pub quantized: Vec<f64>,
    pub codes: Vec<u16>,
    pub tile_of: Vec<usize>,
    pub row_of: Vec<usize>,
    pub column_of: Vec<usize>,
    pub tiles: Vec<Tile>,
    pub row_groups: Vec<Vec<Group>>,
    pub column_groups: Vec<Vec<Group>>,
    pub row_scale: Vec<f64>,
    pub column_scale: Vec<f64>,
    pub norm: f64,
    pub step: f64,
    pub preparation_bytes: u64,
}
pub fn preparation_bytes(m: usize, n: usize, z: usize) -> Result<u64, &'static str> {
    if m > 65536 || n > 65536 || z > 1 << 23 {
        return Err("shape_limit");
    }
    let b = (z as u64)
        .checked_mul(512)
        .and_then(|b| b.checked_add((m as u64 + n as u64) * 512))
        .ok_or("memory_overflow")?;
    if b > 2 << 30 {
        Err("preparation_memory_limit")
    } else {
        Ok(b)
    }
}
impl Operator {
    pub fn new(engine: &Engine<'_>, settings: Settings) -> Result<Self, &'static str> {
        let _cost = optimizer_core::lp_cost::scope("quant_pack_metadata_norm");
        settings.validate()?;
        let p = engine.program();
        let (m, n, z) = (p.row_count(), p.column_count(), p.nonzeros());
        let bytes = preparation_bytes(m, n, z)?;
        let values = engine.scaled_matrix().0.to_vec();
        let row_scale = engine.preconditioner().row().to_vec();
        let column_scale = engine.preconditioner().column().to_vec();
        if row_scale
            .iter()
            .chain(&column_scale)
            .any(|s| !s.is_finite() || *s <= 0.0)
        {
            return Err("scale_range");
        }
        let mut keys = BTreeMap::new();
        for (r, c, _) in p.row_major().entries() {
            keys.insert((r as u32 / 32, c / 32), 0usize);
        }
        for (i, v) in keys.values_mut().enumerate() {
            *v = i;
        }
        let mut tiles = keys
            .keys()
            .map(|&(row, column)| Tile {
                row,
                column,
                exponent: 0,
                count: 0,
                forced: false,
            })
            .collect::<Vec<_>>();
        let mut row_of = Vec::with_capacity(z);
        let mut column_of = Vec::with_capacity(z);
        let mut tile_of = Vec::with_capacity(z);
        let mut maxima = vec![0f64; tiles.len()];
        let mut exact = Vec::with_capacity(z);
        for ((r, c, a), &b) in p.row_major().entries().zip(&values) {
            let t = keys[&(r as u32 / 32, c / 32)];
            tiles[t].count += 1;
            maxima[t] = maxima[t].max(b.abs());
            row_of.push(r);
            column_of.push(c as usize);
            tile_of.push(t);
            exact.push(
                Enclosure::product(row_scale[r], a)
                    .and_then(|v| {
                        let b = column_scale[c as usize];
                        let lo = Enclosure::product(v.lower, b)?;
                        let hi = Enclosure::product(v.upper, b)?;
                        Enclosure::new(lo.lower, hi.upper, v.rounded * b)
                    })
                    .ok_or("scaling_error_range")?,
            );
        }
        if settings.format != Format::Fp64 {
            let limit = settings.format.decode(settings.format.max_code())?;
            for (t, &max) in tiles.iter_mut().zip(&maxima) {
                if max != 0.0 {
                    let mut e = 0;
                    let mut normalized = max;
                    while normalized > limit {
                        normalized *= 0.5;
                        e += 1;
                    }
                    while normalized * 2.0 <= limit {
                        normalized *= 2.0;
                        e -= 1;
                    }
                    t.exponent = e;
                }
            }
        }
        let mut quantized = values.clone();
        let mut codes = vec![0; z];
        if settings.format != Format::Fp64 {
            for (i, &v) in values.iter().enumerate() {
                let t = &mut tiles[tile_of[i]];
                let scaled = crate::research::scale_pow2(v, -t.exponent);
                match settings.format.encode(scaled).and_then(|c| {
                    let q = crate::research::scale_pow2(settings.format.decode(c)?, t.exponent);
                    finite(q)?;
                    if v != 0.0 && q == 0.0 {
                        return Err("conversion_lost_nonzero");
                    }
                    if crate::precision::narrow(q)?.to_bits() != q.to_bits() {
                        return Err("decode_fp32_range");
                    }
                    Ok((c, q))
                }) {
                    Ok((c, q)) => {
                        codes[i] = c;
                        quantized[i] = q;
                    }
                    Err(_) => {
                        t.forced = true;
                    }
                }
            }
        }
        let groups = |transpose: bool| -> Result<Vec<Vec<Group>>, &'static str> {
            let mut lines =
                vec![BTreeMap::<usize, Vec<usize>>::new(); if transpose { n } else { m }];
            for i in 0..z {
                lines[if transpose { column_of[i] } else { row_of[i] }]
                    .entry(tile_of[i])
                    .or_default()
                    .push(i);
            }
            lines
                .into_iter()
                .map(|line| {
                    line.into_iter()
                        .map(|(tile, ids)| {
                            let (mut e, mut oe, mut mass, mut om) = (0.0, 0.0, 0.0, 0.0);
                            for &i in &ids {
                                e = add(e, error(exact[i], quantized[i])?)?;
                                oe = add(oe, error(exact[i], values[i])?)?;
                                mass = add(mass, quantized[i].abs())?;
                                om = add(om, values[i].abs())?;
                            }
                            Ok(Group {
                                tile,
                                ids,
                                error: e,
                                original_error: oe,
                                mass,
                                original_mass: om,
                            })
                        })
                        .collect()
                })
                .collect()
        };
        let row_groups = groups(false)?;
        let column_groups = groups(true)?;
        let maximum = |lines: &Vec<Vec<Group>>| -> Result<f64, &'static str> {
            let mut max = 0f64;
            for line in lines {
                let mut total = 0.;
                for g in line {
                    for &i in &g.ids {
                        total = add(
                            total,
                            exact[i]
                                .lower
                                .abs()
                                .max(exact[i].upper.abs())
                                .max(values[i].abs())
                                * 2.0,
                        )?;
                    }
                }
                max = max.max(total);
            }
            Ok(max)
        };
        let (rn, cn) = (maximum(&row_groups)?, maximum(&column_groups)?);
        let norm = if rn == 0. || cn == 0. {
            0.
        } else {
            mul(rn.sqrt().next_up(), cn.sqrt().next_up())?
        };
        let step = if norm == 0. {
            engine.step()
        } else {
            engine.step().min((0.9f64.next_down() / norm).next_down())
        };
        if !step.is_finite() || step <= 0. {
            return Err("operator_step_range");
        }
        Ok(Self {
            settings,
            rows: m,
            columns: n,
            values,
            quantized,
            codes,
            tile_of,
            row_of,
            column_of,
            tiles,
            row_groups,
            column_groups,
            row_scale,
            column_scale,
            norm,
            step,
            preparation_bytes: bytes,
        })
    }
    pub fn groups(&self, transpose: bool) -> &Vec<Vec<Group>> {
        if transpose {
            &self.column_groups
        } else {
            &self.row_groups
        }
    }
    /// Includes vector conversion, coefficient error, gradual-underflow additive
    /// terms, tile reductions and the FP64 sum of tile results.
    pub fn bounds(
        &self,
        state: &Promotion,
        transpose: bool,
        v: &[f64],
    ) -> Result<(Vec<f64>, Vec<usize>), &'static str> {
        let _cost = optimizer_core::lp_cost::scope("quant_product_guard");
        if v.len() != if transpose { self.rows } else { self.columns }
            || v.iter().any(|x| !x.is_finite())
        {
            return Err("vector_shape_range");
        }
        state.validate(self)?;
        let mut max = vec![0f64; v.len().div_ceil(32)];
        let mut conversion = max.clone();
        for (i, &x) in v.iter().enumerate() {
            max[i / 32] = max[i / 32].max(x.abs());
            let f = f64::from(x as f32);
            conversion[i / 32] = conversion[i / 32].max(if f.is_finite() {
                error(interval(x)?, f)?
            } else {
                f64::INFINITY
            });
        }
        let mut bounds = Vec::new();
        let unavailable = self
            .groups(transpose)
            .iter()
            .flatten()
            .filter(|g| {
                let t = &self.tiles[g.tile];
                let block = if transpose { t.row } else { t.column } as usize;
                !state.mask[g.tile] && !conversion[block].is_finite()
            })
            .map(|g| g.tile)
            .collect::<BTreeSet<_>>();
        if !unavailable.is_empty() {
            return Ok((vec![], unavailable.into_iter().collect()));
        }
        let mut bad = BTreeSet::new();
        for (line, groups) in self.groups(transpose).iter().enumerate() {
            let (mut total, mut mass) = (0., 0.);
            for g in groups {
                let t = &self.tiles[g.tile];
                let block = if transpose { t.row } else { t.column } as usize;
                let low = !state.mask[g.tile];
                let a = if low { g.mass } else { g.original_mass };
                let e = if low { g.error } else { g.original_error };
                let mut b = mul(e, max[block])?;
                if low && !conversion[block].is_finite() {
                    bad.insert(g.tile);
                    bounds.push(f64::INFINITY);
                    continue;
                }
                if low {
                    b = add(b, mul(a, conversion[block])?)?;
                }
                let abs = mul(
                    a,
                    add(max[block], if low { conversion[block] } else { 0. })?,
                )?;
                let u = if low { 2f64.powi(-24) } else { 2f64.powi(-53) };
                let count = 64f64;
                let gamma = (count * u / (1. - count * u)).next_up();
                b = add(b, mul(gamma, abs)?)?;
                // One additive half-min-subnormal per product/add (overbound).
                b = add(
                    b,
                    if low {
                        2f64.powi(-149) * 64.
                    } else {
                        f64::from_bits(64)
                    },
                )?;
                total = add(total, b)?;
                mass = add(mass, abs)?;
            }
            let k = groups.len() as f64;
            let nu = k * 2f64.powi(-53);
            if nu >= 1. {
                return Err("reduction_length");
            }
            total = add(total, mul((nu / (1. - nu)).next_up(), mass)?)?;
            total = add(total, f64::from_bits(groups.len() as u64 + 1))?;
            let scale = if transpose {
                self.column_scale[line]
            } else {
                self.row_scale[line]
            };
            let original = finite((total / scale).next_up())?;
            bounds.push(original);
            let budget = if transpose {
                self.settings.dual_budget
            } else {
                self.settings.primal_budget
            };
            if original > budget {
                for g in groups {
                    if !state.mask[g.tile] {
                        bad.insert(g.tile);
                    }
                }
                if groups.iter().all(|g| state.mask[g.tile]) {
                    return Err("native_operator_error_budget");
                }
            }
        }
        Ok((bounds, bad.into_iter().collect()))
    }
    pub fn product(
        &self,
        state: &Promotion,
        transpose: bool,
        v: &[f64],
    ) -> Result<Vec<f64>, &'static str> {
        state.validate(self)?;
        if v.len() != if transpose { self.rows } else { self.columns } {
            return Err("vector_shape");
        }
        self.groups(transpose)
            .iter()
            .map(|groups| {
                let mut total = 0.;
                for g in groups {
                    let low = !state.mask[g.tile];
                    let mut lanes = [0.; 32];
                    for (lane, &id) in g.ids.iter().enumerate() {
                        let input = if transpose {
                            self.row_of[id]
                        } else {
                            self.column_of[id]
                        };
                        lanes[lane] = checked_product(
                            if low {
                                self.quantized[id]
                            } else {
                                self.values[id]
                            },
                            v[input],
                            low,
                        )?;
                    }
                    for offset in [16, 8, 4, 2, 1] {
                        for lane in 0..offset {
                            lanes[lane] = finite(if low {
                                f64::from(lanes[lane] as f32 + lanes[lane + offset] as f32)
                            } else {
                                lanes[lane] + lanes[lane + offset]
                            })?;
                        }
                    }
                    total = finite(total + lanes[0])?;
                }
                Ok(total)
            })
            .collect()
    }
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Promotion {
    pub mask: Vec<bool>,
    pub generation: u64,
    pub transitions: u64,
    pub native: bool,
}
impl Promotion {
    pub fn new(op: &Operator) -> Self {
        let mut s = Self {
            mask: vec![false; op.tiles.len()],
            generation: 0,
            transitions: 0,
            native: op.settings.format == Format::Fp64,
        };
        if s.native {
            s.mask.fill(true);
        } else {
            let forced = op
                .tiles
                .iter()
                .enumerate()
                .filter_map(|(i, t)| t.forced.then_some(i))
                .collect::<Vec<_>>();
            if !forced.is_empty() {
                s.promote(op, &forced);
            }
        }
        s
    }
    pub fn validate(&self, op: &Operator) -> Result<(), &'static str> {
        if self.mask.len() != op.tiles.len()
            || self.transitions > 9
            || self.generation != self.transitions
            || self.native && self.mask.iter().any(|m| !*m)
            || op
                .tiles
                .iter()
                .enumerate()
                .any(|(i, t)| t.forced && !self.mask[i])
        {
            Err("operator_generation")
        } else {
            Ok(())
        }
    }
    pub fn promote(&mut self, op: &Operator, ids: &[usize]) -> bool {
        let _cost = optimizer_core::lp_cost::scope("quant_promotion");
        if self.native {
            return false;
        }
        let old = self.mask.clone();
        for &i in ids {
            if i >= self.mask.len() {
                return false;
            }
            self.mask[i] = true;
        }
        let promoted = op
            .tiles
            .iter()
            .zip(&self.mask)
            .filter(|(_, m)| **m)
            .map(|(t, _)| t.count)
            .sum::<usize>();
        if op.settings.policy == Policy::Uniform
            || self.transitions >= 8
            || promoted * 4 > op.values.len()
        {
            self.native = true;
            self.mask.fill(true);
        }
        if self.mask != old {
            self.transitions += 1;
            self.generation += 1;
            true
        } else {
            false
        }
    }
}
pub trait Oracle {
    fn product(
        &mut self,
        op: &Operator,
        state: &Promotion,
        transpose: bool,
        v: &[f64],
    ) -> Result<Vec<f64>, String>;
}
pub struct HostOracle;
impl Oracle for HostOracle {
    fn product(
        &mut self,
        op: &Operator,
        state: &Promotion,
        t: bool,
        v: &[f64],
    ) -> Result<Vec<f64>, String> {
        op.product(state, t, v).map_err(str::to_string)
    }
}
#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Work {
    pub proposals: u64,
    pub rejected: u64,
    pub audits: u64,
    pub replays: u64,
    pub low_products: u64,
    pub high_products: u64,
    pub assessments: u64,
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Transition {
    pub iteration: u64,
    pub generation: u64,
    pub reason: String,
    pub promoted_coefficients: u64,
    pub native: bool,
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Outcome {
    pub primal: Vec<f64>,
    pub dual: Vec<f64>,
    pub scaled_primal: Vec<f64>,
    pub scaled_dual: Vec<f64>,
    pub iterations: u64,
    pub physical: u64,
    pub stop: String,
    pub failure: Option<String>,
    pub work: Work,
    pub promotion: Promotion,
    pub transitions: Vec<Transition>,
    pub norm: f64,
    pub step: f64,
}
/// In-memory checkpoint: numerical/promotion state restores, physical work does not.
#[derive(Clone)]
pub struct Checkpoint<'e, 'p> {
    origin: Arc<()>,
    controller: Fp64Checkpoint<'e, 'p>,
    promotion: Promotion,
}
pub struct Session<'e, 'p> {
    origin: Arc<()>,
    pub controller: Fp64Controller<'e, 'p>,
    pub promotion: Promotion,
}
impl<'e, 'p> Session<'e, 'p> {
    pub fn new(e: &'e Engine<'p>, op: &Operator, deadline: Option<Instant>) -> Self {
        let mut controller = Fp64Controller::new(e);
        controller.set_deadline(deadline);
        Self {
            origin: Arc::new(()),
            controller,
            promotion: Promotion::new(op),
        }
    }
    pub fn checkpoint(&self) -> Checkpoint<'e, 'p> {
        Checkpoint {
            origin: Arc::clone(&self.origin),
            controller: self.controller.checkpoint(),
            promotion: self.promotion.clone(),
        }
    }
    pub fn restore(&mut self, c: &Checkpoint<'e, 'p>) -> Result<(), &'static str> {
        let _cost = optimizer_core::lp_cost::scope("quant_window_restore");
        if !Arc::ptr_eq(&self.origin, &c.origin) {
            return Err("quant_checkpoint_session");
        }
        self.controller.restore(&c.controller)?;
        self.promotion = c.promotion.clone();
        Ok(())
    }
}
fn proposal<O: Oracle>(
    engine: &Engine<'_>,
    op: &Operator,
    p: &Promotion,
    s: &Fp64State,
    o: &mut O,
    w: &mut Work,
) -> Result<(Vec<f64>, Vec<f64>), Failure> {
    let mut product = |transpose: bool, v: &[f64]| -> Result<Vec<f64>, Failure> {
        let (_, bad) = op
            .bounds(p, transpose, v)
            .map_err(|e| Failure::Numerical(e.into()))?;
        if !bad.is_empty() {
            return Err(Failure::Promote(bad, "operator_error_budget".into()));
        }
        let low = op
            .tiles
            .iter()
            .zip(&p.mask)
            .filter(|(_, m)| !**m)
            .map(|(t, _)| t.count as u64)
            .sum::<u64>();
        w.low_products += low;
        w.high_products += op.values.len() as u64 - low;
        o.product(op, p, transpose, v).map_err(|e| {
            if e.starts_with("device:") {
                Failure::Device(e)
            } else {
                Failure::Promote((0..op.tiles.len()).filter(|&i| !p.mask[i]).collect(), e)
            }
        })
    };
    let aty = product(true, &s.dual)?;
    let (ps, ds) = (engine.step() / s.weight, engine.step() * s.weight);
    if !ps.is_finite() || !ds.is_finite() || ps == 0. || ds == 0. {
        return Err(Failure::Numerical("update_step_range".into()));
    }
    let (xl, xu) = engine.scaled_column_bounds();
    let (yl, yu) = engine.scaled_row_bounds();
    let toward = (s.since_restart + 1) as f64 / (s.since_restart + 2) as f64;
    let back = 1. / (s.since_restart + 2) as f64;
    let mut x = vec![0.; s.primal.len()];
    let mut bar = x.clone();
    for j in 0..x.len() {
        let diff = finite(engine.scaled_objective()[j] - aty[j])
            .map_err(|e| Failure::Numerical(e.into()))?;
        let next = finite(
            s.primal[j]
                - checked_product(ps, diff, false).map_err(|e| Failure::Numerical(e.into()))?,
        )
        .map_err(|e| Failure::Numerical(e.into()))?
        .max(xl[j])
        .min(xu[j]);
        bar[j] = finite(2. * next - s.primal[j]).map_err(|e| Failure::Numerical(e.into()))?;
        x[j] = blend(toward, next, back, s.anchor_primal[j])
            .map_err(|e| Failure::Numerical(e.into()))?;
    }
    let ax = product(false, &bar)?;
    let mut y = vec![0.; s.dual.len()];
    for j in 0..y.len() {
        let raw = finite(
            s.dual[j]
                - checked_product(ds, ax[j], false).map_err(|e| Failure::Numerical(e.into()))?,
        )
        .map_err(|e| Failure::Numerical(e.into()))?;
        let scaled = finite(raw / ds)
            .map_err(|e| Failure::Numerical(e.into()))?
            .max(-yu[j])
            .min(-yl[j]);
        let next = finite(
            raw - checked_product(ds, scaled, false).map_err(|e| Failure::Numerical(e.into()))?,
        )
        .map_err(|e| Failure::Numerical(e.into()))?;
        y[j] = blend(toward, next, back, s.anchor_dual[j])
            .map_err(|e| Failure::Numerical(e.into()))?;
    }
    Ok((x, y))
}
enum Failure {
    Promote(Vec<usize>, String),
    Numerical(String),
    Device(String),
}
#[allow(clippy::too_many_arguments)]
pub fn run<O: Oracle>(
    engine: &Engine<'_>,
    op: &Operator,
    o: &mut O,
    diagnostic: bool,
    cancel: &CancellationToken,
    deadline: Option<Instant>,
    mut assess: impl FnMut(&[f64], &[f64]) -> bool,
) -> Outcome {
    let _cost = optimizer_core::lp_cost::scope("quant_solve_loop");
    let mut s = Session::new(engine, op, deadline);
    let mut w = Work::default();
    let mut transitions = Vec::new();
    let (mut stop, mut failure) = ("iteration_limit".to_string(), None);
    w.assessments += 1;
    let initial = assess(
        &engine.unscale_primal(&s.controller.state().primal),
        &engine.unscale_dual(&s.controller.state().dual),
    );
    if initial && !diagnostic {
        stop = "certified".into();
    } else {
        'solve: while s.controller.remaining() > 1 {
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
            let len = s
                .controller
                .next_chunk(op.settings.audit_interval)
                .min(s.controller.remaining() - 1);
            let end = start + len;
            let mut replay = false;
            'attempt: loop {
                let _attempt_cost = optimizer_core::lp_cost::scope(if replay {
                    "quant_replay_window"
                } else {
                    "quant_proposal_window"
                });
                let before_proposals = w.proposals;
                let mut failed = None;
                let mut pre = None;
                while s.controller.state().iterations < end {
                    if cancel.is_cancelled() || s.controller.expired() {
                        {
                            let promoted = s.promotion.clone();
                            s.restore(&cp).expect("same session");
                            s.promotion = promoted;
                        }
                        stop = if cancel.is_cancelled() {
                            "interrupted"
                        } else {
                            "time_limit"
                        }
                        .into();
                        break 'solve;
                    }
                    if s.controller.remaining() < 2 {
                        {
                            let promoted = s.promotion.clone();
                            s.restore(&cp).expect("same session");
                            s.promotion = promoted;
                        }
                        break 'solve;
                    }
                    if s.controller.state().iterations + 1 == end {
                        pre = Some(s.controller.state().clone());
                    }
                    w.proposals += 1;
                    if replay {
                        w.replays += 1;
                    }
                    match proposal(engine, op, &s.promotion, s.controller.state(), o, &mut w) {
                        Ok((x, y)) => {
                            s.controller
                                .replace_endpoint(x, y)
                                .expect("finite endpoint");
                            s.controller.commit_steps(1).expect("bounded work");
                        }
                        Err(e) => {
                            s.controller.charge_extra(1).expect("rejected allowance");
                            failed = Some(e);
                            break;
                        }
                    }
                }
                if failed.is_none() {
                    if cancel.is_cancelled() || s.controller.expired() {
                        {
                            let promoted = s.promotion.clone();
                            s.restore(&cp).expect("same session");
                            s.promotion = promoted;
                        }
                        stop = if cancel.is_cancelled() {
                            "interrupted"
                        } else {
                            "time_limit"
                        }
                        .into();
                        break 'solve;
                    }
                    let _audit_cost = optimizer_core::lp_cost::scope("quant_audit");
                    s.controller.charge_extra(1).expect("audit allowance");
                    w.audits += 1;
                    match crate::precision::correction(
                        engine,
                        pre.as_ref().expect("final pre-step"),
                    ) {
                        Ok((x, y)) => {
                            let mut pass = true;
                            for (low, reference, before, scale) in [
                                (
                                    &s.controller.state().primal,
                                    &x,
                                    &pre.as_ref().unwrap().primal,
                                    engine.preconditioner().column(),
                                ),
                                (
                                    &s.controller.state().dual,
                                    &y,
                                    &pre.as_ref().unwrap().dual,
                                    engine.preconditioner().row(),
                                ),
                            ] {
                                for (((&l, &h), &b), &scale) in
                                    low.iter().zip(reference).zip(before).zip(scale)
                                {
                                    let (l, h, b) = (l * scale, h * scale, b * scale);
                                    let allowance = BUDGET + BUDGET * b.abs().max(h.abs());
                                    pass &= l.is_finite()
                                        && h.is_finite()
                                        && b.is_finite()
                                        && allowance.is_finite()
                                        && (l - h).abs() <= allowance;
                                }
                            }
                            if pass {
                                s.controller
                                    .replace_endpoint(x, y)
                                    .expect("reference endpoint");
                            } else {
                                failed = Some(Failure::Promote(
                                    (0..op.tiles.len())
                                        .filter(|&i| !s.promotion.mask[i])
                                        .collect(),
                                    "audit_error".into(),
                                ));
                            }
                        }
                        Err(e) => failed = Some(Failure::Numerical(e.into())),
                    }
                }
                if let Some(f) = failed {
                    w.rejected += w.proposals - before_proposals;
                    let mut promotion = s.promotion.clone();
                    let reason = match f {
                        Failure::Promote(ids, why) => {
                            if !promotion.promote(op, &ids) {
                                {
                                    let promoted = s.promotion.clone();
                                    s.restore(&cp).expect("same session");
                                    s.promotion = promoted;
                                }
                                stop = "numerical_failure".into();
                                failure = Some(why);
                                break 'solve;
                            }
                            why
                        }
                        Failure::Numerical(why) => {
                            {
                                let promoted = s.promotion.clone();
                                s.restore(&cp).expect("same session");
                                s.promotion = promoted;
                            }
                            stop = "numerical_failure".into();
                            failure = Some(why);
                            break 'solve;
                        }
                        Failure::Device(why) => {
                            {
                                let promoted = s.promotion.clone();
                                s.restore(&cp).expect("same session");
                                s.promotion = promoted;
                            }
                            stop = "device_failure".into();
                            failure = Some(why);
                            break 'solve;
                        }
                    };
                    {
                        let promoted = s.promotion.clone();
                        s.restore(&cp).expect("same session");
                        s.promotion = promoted;
                    }
                    s.promotion = promotion;
                    transitions.push(Transition {
                        iteration: start,
                        generation: s.promotion.generation,
                        reason,
                        promoted_coefficients: op
                            .tiles
                            .iter()
                            .zip(&s.promotion.mask)
                            .filter(|(_, m)| **m)
                            .map(|(t, _)| t.count as u64)
                            .sum(),
                        native: s.promotion.native,
                    });
                    replay = true;
                    continue 'attempt;
                }
                break;
            }
            if s.controller.check_pending() {
                w.assessments += 1;
                let closed = assess(
                    &engine.unscale_primal(&s.controller.state().primal),
                    &engine.unscale_dual(&s.controller.state().dual),
                );
                if closed && !diagnostic {
                    stop = "certified".into();
                    break;
                }
                s.controller.continue_after_check();
            }
        }
    }
    // A terminal failure already has its own stop reason and metadata. A late
    // deadline/cancellation may suppress success but cannot relabel that failure.
    if failure.is_none() {
        if cancel.is_cancelled() {
            stop = "interrupted".into();
        } else if s.controller.expired() {
            stop = "time_limit".into();
        }
    }
    let point = s.controller.state();
    w.rejected = w.proposals - point.iterations;
    let primal = engine.unscale_primal(&point.primal);
    let dual = engine.unscale_dual(&point.dual);
    w.assessments += 1;
    let closed = assess(&primal, &dual);
    if closed && stop == "iteration_limit" && !diagnostic {
        stop = "certified".into();
    }
    Outcome {
        primal,
        dual,
        scaled_primal: point.primal.clone(),
        scaled_dual: point.dual.clone(),
        iterations: point.iterations,
        physical: s.controller.physical_iterations(),
        stop,
        failure,
        work: w,
        promotion: s.promotion,
        transitions,
        norm: op.norm,
        step: engine.step(),
    }
}
/// Canonical model dimensions are checked without admitting a device.
pub fn admit_shape(p: &LinearProgram) -> Result<u64, &'static str> {
    preparation_bytes(p.row_count(), p.column_count(), p.nonzeros())
}
