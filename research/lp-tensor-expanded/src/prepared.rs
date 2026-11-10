//! Compact FP64 metadata and interval Gram norm for ADR-0044 only.
#![allow(missing_docs)]
use crate::{Engine, outward::Enclosure, quant};

pub struct CompactBase {
    pub(crate) data: quant::OperatorData,
}
impl std::ops::Deref for CompactBase {
    type Target = quant::OperatorData;
    fn deref(&self) -> &Self::Target {
        &self.data
    }
}
fn add(a: f64, b: f64) -> Result<f64, &'static str> {
    Ok(Enclosure::point(a)
        .and_then(|a| a.add(Enclosure::point(b)?))
        .ok_or("bound_range")?
        .upper)
}
fn error(a: Enclosure, b: f64) -> Result<f64, &'static str> {
    let d = a
        .subtract(Enclosure::point(b).ok_or("bound_range")?)
        .ok_or("bound_range")?;
    Ok(d.lower.abs().max(d.upper.abs()))
}
pub fn prepare(
    e: &Engine<'_>,
    settings: quant::Settings,
) -> Result<(CompactBase, Vec<f64>, Vec<f64>), &'static str> {
    let _profile = optimizer_core::lp_cost::scope("compact_pack");
    settings.validate()?;
    if settings.format != quant::Format::Fp64 || settings.policy != quant::Policy::Uniform {
        return Err("resident_layout_format");
    }
    let p = e.program();
    let (m, n, z) = (p.row_count(), p.column_count(), p.nonzeros());
    let lookup_size = m
        .div_ceil(32)
        .checked_mul(n.div_ceil(32))
        .ok_or("preparation_memory_overflow")?;
    if m > 65536 || n > 65536 {
        return Err("preparation_dimension_limit");
    }
    let bytes = quant::preparation_bytes(m, n, z)?
        .checked_add(
            (lookup_size as u64)
                .checked_mul(8)
                .ok_or("preparation_memory_overflow")?,
        )
        .ok_or("preparation_memory_overflow")?;
    if bytes > 2 << 30 {
        return Err("preparation_memory_limit");
    }
    let values = e.scaled_matrix().0.to_vec();
    let row_scale = e.preconditioner().row().to_vec();
    let column_scale = e.preconditioner().column().to_vec();
    if row_scale
        .iter()
        .chain(&column_scale)
        .any(|x| !x.is_finite() || *x <= 0.)
    {
        return Err("scale_range");
    }
    let width = n.div_ceil(32);
    let mut lookup = vec![usize::MAX; lookup_size];
    for (r, c, _) in p.row_major().entries() {
        lookup[(r / 32) * width + c as usize / 32] = 0;
    }
    let mut tiles = Vec::new();
    for (key, value) in lookup.iter_mut().enumerate() {
        if *value == usize::MAX {
            continue;
        }
        *value = tiles.len();
        tiles.push(quant::Tile {
            row: (key / width) as u32,
            column: (key % width) as u32,
            exponent: 0,
            count: 0,
            forced: false,
        });
    }
    let mut row_of = Vec::with_capacity(z);
    let mut column_of = Vec::with_capacity(z);
    let mut tile_of = Vec::with_capacity(z);
    let mut errors = Vec::with_capacity(z);
    let mut absolute = Vec::with_capacity(z);
    let mut rows = vec![Vec::<(usize, Vec<usize>)>::new(); m];
    let mut columns = vec![Vec::<(usize, Vec<usize>)>::new(); n];
    let append = |line: &mut Vec<(usize, Vec<usize>)>, tile: usize, id: usize| {
        if line.last().is_none_or(|(last, _)| *last != tile) {
            line.push((tile, Vec::new()));
        }
        line.last_mut().unwrap().1.push(id);
    };
    for (id, ((r, c, a), &v)) in p.row_major().entries().zip(&values).enumerate() {
        let c = c as usize;
        let tile = lookup[(r / 32) * width + c / 32];
        tiles[tile].count += 1;
        row_of.push(r);
        column_of.push(c);
        tile_of.push(tile);
        append(&mut rows[r], tile, id);
        append(&mut columns[c], tile, id);
        let first = Enclosure::product(row_scale[r], a).ok_or("scaling_error_range")?;
        let lo = Enclosure::product(first.lower, column_scale[c]).ok_or("scaling_error_range")?;
        let hi = Enclosure::product(first.upper, column_scale[c]).ok_or("scaling_error_range")?;
        let exact = Enclosure::new(lo.lower, hi.upper, first.rounded * column_scale[c])
            .ok_or("scaling_error_range")?;
        errors.push(error(exact, v)?);
        absolute.push(exact.lower.abs().max(exact.upper.abs()).max(v.abs()));
    }
    let groups =
        |lines: Vec<Vec<(usize, Vec<usize>)>>| -> Result<Vec<Vec<quant::Group>>, &'static str> {
            lines
                .into_iter()
                .map(|line| {
                    line.into_iter()
                        .map(|(tile, ids)| {
                            let (mut err, mut mass) = (0., 0.);
                            for &id in &ids {
                                err = add(err, errors[id])?;
                                mass = add(mass, values[id].abs())?;
                            }
                            Ok(quant::Group {
                                tile,
                                ids,
                                error: err,
                                original_error: err,
                                mass,
                                original_mass: mass,
                            })
                        })
                        .collect()
                })
                .collect()
        };
    let row_groups = groups(rows)?;
    let column_groups = groups(columns)?;
    drop(lookup);
    let maximum = |lines: &Vec<Vec<quant::Group>>| -> Result<f64, &'static str> {
        let mut maximum = 0f64;
        for line in lines {
            let mut sum = 0.;
            for g in line {
                for &id in &g.ids {
                    sum = add(sum, absolute[id] * 2.)?;
                }
            }
            maximum = maximum.max(sum);
        }
        Ok(maximum)
    };
    let (rn, cn) = (maximum(&row_groups)?, maximum(&column_groups)?);
    let norm = if rn == 0. || cn == 0. {
        0.
    } else {
        Enclosure::product(rn.sqrt().next_up(), cn.sqrt().next_up())
            .ok_or("bound_range")?
            .upper
    };
    let step = if norm == 0. {
        e.step()
    } else {
        e.step().min((0.9f64.next_down() / norm).next_down())
    };
    if !step.is_finite() || step <= 0. {
        return Err("operator_step_range");
    }
    let base = CompactBase {
        data: quant::OperatorData {
            settings,
            rows: m,
            columns: n,
            quantized: values.clone(),
            values,
            codes: vec![0; z],
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
        },
    };
    Ok((base, errors.clone(), errors))
}

#[derive(Clone, Debug, serde::Serialize, serde::Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct NormProof {
    pub legacy_bound: f64,
    pub gram_bound: Option<f64>,
    pub selected_bound: f64,
    pub blocks: usize,
    pub gram_terms: u64,
    pub fallback: Option<String>,
}
fn sqrt_product(a: f64, b: f64) -> Option<f64> {
    if a == 0. || b == 0. {
        Some(0.)
    } else {
        let v = crate::tensor_cost::up_mul(a.sqrt().next_up(), b.sqrt().next_up());
        v.is_finite().then_some(v)
    }
}
/// Outward row-sum bound of the interval Gram matrix; handles cancellation.
pub fn gram_bound(block: &[f64]) -> Option<f64> {
    if block.len() != 1024 || block.iter().any(|x| !x.is_finite()) {
        return None;
    }
    let mut sums = [0.; 32];
    let parts = block
        .iter()
        .map(|&v| {
            if v == 0. {
                None
            } else {
                Some(crate::outward::parts(v))
            }
        })
        .collect::<Vec<_>>();
    for i in 0..32 {
        for j in i..32 {
            let mut dot = Enclosure::ZERO;
            for k in 0..32 {
                dot = dot.add(Enclosure::product_cached(
                    block[k * 32 + i],
                    block[k * 32 + j],
                    parts[k * 32 + i],
                    parts[k * 32 + j],
                )?)?;
            }
            let absolute = dot.lower.abs().max(dot.upper.abs());
            sums[i] = crate::tensor_cost::up_add(sums[i], absolute);
            if i != j {
                sums[j] = crate::tensor_cost::up_add(sums[j], absolute);
            }
        }
    }
    let upper = sums.into_iter().fold(0f64, f64::max);
    let bound = if upper == 0. {
        0.
    } else {
        upper.sqrt().next_up()
    };
    bound.is_finite().then_some(bound)
}
pub fn tighten(
    base: &mut CompactBase,
    selected: &[i32],
    dense: &[i64],
    exponents: &[i32],
    represented: &[f64],
    errors: &[f64],
) -> NormProof {
    let _profile = optimizer_core::lp_cost::scope("interval_gram_norm");
    let legacy = base.norm;
    let mut proof = NormProof {
        legacy_bound: legacy,
        gram_bound: None,
        selected_bound: legacy,
        blocks: exponents.len(),
        gram_terms: 0,
        fallback: None,
    };
    let attempt = || -> Result<(f64, u64), &'static str> {
        let count = exponents.len();
        if count == 0 || count > 2048 || count as u64 * 32768 > 67108864 {
            return Err("gram_work_cap_or_no_dense_blocks");
        }
        let mut row_blocks = std::collections::BTreeSet::new();
        let mut column_blocks = std::collections::BTreeSet::new();
        for (tile, &index) in base.tiles.iter().zip(selected) {
            if index >= 0 && (!row_blocks.insert(tile.row) || !column_blocks.insert(tile.column)) {
                return Err("non_disjoint_dense_blocks");
            }
        }
        let mut maximum = 0f64;
        for (tile, &exponent) in exponents.iter().enumerate() {
            let mut block = [0.; 1024];
            for (out, &q) in block.iter_mut().zip(&dense[tile * 1024..(tile + 1) * 1024]) {
                *out = crate::tensor_cost::round_dot(i128::from(q), exponent - 56)?.0;
            }
            maximum = maximum.max(gram_bound(&block).ok_or("gram_range")?);
        }
        let (mut rr, mut rc) = (vec![0.; base.rows], vec![0.; base.columns]);
        let (mut er, mut ec) = (rr.clone(), rc.clone());
        for id in 0..base.values.len() {
            let (r, c) = (base.row_of[id], base.column_of[id]);
            if selected[base.tile_of[id]] < 0 {
                rr[r] = crate::tensor_cost::up_add(rr[r], represented[id].abs());
                rc[c] = crate::tensor_cost::up_add(rc[c], represented[id].abs());
            }
            er[r] = crate::tensor_cost::up_add(er[r], errors[id]);
            ec[c] = crate::tensor_cost::up_add(ec[c], errors[id]);
        }
        let max = |v: Vec<f64>| v.into_iter().fold(0f64, f64::max);
        let remainder = sqrt_product(max(rr), max(rc)).ok_or("remainder_norm_range")?;
        let error = sqrt_product(max(er), max(ec)).ok_or("error_norm_range")?;
        let norm =
            crate::tensor_cost::up_add(crate::tensor_cost::up_add(maximum, remainder), error);
        if !norm.is_finite() || norm < 0. {
            return Err("gram_norm_range");
        }
        Ok((norm, count as u64 * 32 * 32 * 33 / 2))
    };
    match attempt() {
        Ok((norm, terms)) => {
            proof.gram_bound = Some(norm);
            proof.gram_terms = terms;
            base.data.norm = legacy.min(norm);
            // The original engine step was already an upper bound on legacy step;
            // recover it explicitly at the call site, never by scaling that step.
            proof.selected_bound = base.norm;
        }
        Err(why) => proof.fallback = Some(why.into()),
    }
    proof
}
