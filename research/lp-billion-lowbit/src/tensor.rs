//! Canonical sparse-block FP4 packing. No full-matrix padding or fixture dispatch.
use crate::{
    Result,
    operator::{Operator, Orientation, decode},
};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct Config {
    pub min_tile_nnz: usize,
    pub components: usize,
    pub control_interval: u64,
    pub incremental: bool,
    pub compact_fragments: bool,
    pub tensor_warps: usize,
}
impl Default for Config {
    fn default() -> Self {
        Self {
            min_tile_nnz: 128,
            components: 2,
            control_interval: 100,
            incremental: true,
            compact_fragments: true,
            tensor_warps: 1,
        }
    }
}
impl Config {
    pub fn validate(&self) -> Result<()> {
        if ![1, 4].contains(&self.tensor_warps)
            || !(1..=1024).contains(&self.min_tile_nnz)
            || !(1..=4).contains(&self.components)
            || !(1..=1000).contains(&self.control_interval)
        {
            return Err("tensor configuration domain".into());
        }
        Ok(())
    }
}
#[derive(Debug, Serialize)]
pub struct Tiles {
    pub offsets: Vec<u32>,
    pub columns: Vec<u32>,
    pub fragments: Vec<u32>,
    pub exponents: Vec<i32>,
    /// Per 16-row half tile: coefficient error and component magnitude, interleaved.
    pub metadata: Vec<f64>,
    pub covered: Vec<u32>,
    pub residual: Orientation<'static>,
}
#[derive(Debug, Serialize)]
pub struct Packed {
    pub rows: Tiles,
    pub columns: Tiles,
    pub components: usize,
    pub tile_count: usize,
    pub compact_fragments: bool,
}
fn upadd(a: f64, b: f64) -> f64 {
    if a == 0. && b == 0. {
        0.
    } else {
        (a + b).next_up()
    }
}
pub(crate) fn quant(v: f64) -> u8 {
    let x = v.abs();
    let best = if x > 5. {
        7
    } else if x >= 3.5 {
        6
    } else if x > 2.5 {
        5
    } else if x >= 1.75 {
        4
    } else if x > 1.25 {
        3
    } else if x > 0.5 {
        2
    } else {
        0
    };
    best | if v < 0. && best != 0 { 8 } else { 0 }
}
pub(crate) fn encode(values: &[f64], k: usize) -> (Vec<u8>, Vec<i32>, Vec<f64>) {
    let mut rem = values.to_vec();
    let mut codes = vec![0; values.len() * k];
    let mut ex = Vec::new();
    for h in 0..k {
        let max = rem.iter().map(|v| v.abs()).fold(0., f64::max);
        let mut e = if max == 0. {
            -48
        } else {
            (max.log2().floor() as i32 - 2).max(-48)
        };
        if max > 6. * 2f64.powi(e) {
            e += 1;
        }
        ex.push(e);
        let scale = 2f64.powi(e);
        let inverse = 2f64.powi(-e);
        for (j, v) in rem.iter_mut().enumerate() {
            let c = quant(*v * inverse);
            codes[h * values.len() + j] = c;
            *v -= decode(c) * scale;
        }
    }
    (codes, ex, rem)
}
impl Packed {
    pub fn new(op: &Operator, c: &Config) -> Result<Self> {
        Self::build(op, c, true)
    }
    /// Unenclosed search proposals do not consume outward row metadata.
    pub fn proposal(op: &Operator, c: &Config) -> Result<Self> {
        Self::build(op, c, false)
    }
    fn build(op: &Operator, c: &Config, enclose: bool) -> Result<Self> {
        Self::build_scheduled(op, c, enclose, true)
    }
    fn build_scheduled(op: &Operator, c: &Config, enclose: bool, parallel: bool) -> Result<Self> {
        c.validate()?;
        // Maps contain only occupied sparse tiles. Quantized tiles are allocated
        // only after passing the density test; original coefficients stay authoritative.
        let mut canonical = BTreeMap::new();
        let mut row_covered = vec![false; op.rows.original.len()];
        let blocks = (op.columns.offsets.len() - 1).div_ceil(32);
        let mut counts = vec![0usize; blocks];
        let mut slots = vec![usize::MAX; blocks];
        for first in (0..op.rows.offsets.len() - 1).step_by(32) {
            let last = (first + 32).min(op.rows.offsets.len() - 1);
            let lo = op.rows.offsets[first] as usize;
            let hi = op.rows.offsets[last] as usize;
            let mut touched = Vec::new();
            for &col in &op.rows.indices[lo..hi] {
                let block = col as usize / 32;
                if counts[block] == 0 {
                    touched.push(block);
                }
                counts[block] += 1;
            }
            touched.sort_unstable();
            let eligible: Vec<_> = touched
                .iter()
                .copied()
                .filter(|&col| counts[col] >= c.min_tile_nnz)
                .collect();
            let mut values = vec![vec![0.; 1024]; eligible.len()];
            for (i, &col) in eligible.iter().enumerate() {
                slots[col] = i;
            }
            if !eligible.is_empty() {
                for row in first..last {
                    let range = op.rows.offsets[row] as usize..op.rows.offsets[row + 1] as usize;
                    for ((&col, &value), covered) in op.rows.indices[range.clone()]
                        .iter()
                        .zip(&op.rows.original[range.clone()])
                        .zip(&mut row_covered[range])
                    {
                        let col = col as usize;
                        let slot = slots[col / 32];
                        if slot != usize::MAX {
                            values[slot][(row % 32) * 32 + col % 32] = value;
                            *covered = true;
                        }
                    }
                }
            }
            for (col, values) in eligible.into_iter().zip(values) {
                canonical.insert((first / 32, col), (values, Vec::new(), Vec::new()));
                slots[col] = usize::MAX;
            }
            for col in touched {
                counts[col] = 0;
            }
        }
        // Quantization is independent per canonical tile. Retain tile order,
        // coefficient order and identical rounding in both orientations.
        let mut tiles: Vec<_> = canonical.values_mut().collect();
        let workers = if parallel && !enclose && tiles.len() >= 128 {
            4
        } else {
            1
        };
        let chunk = tiles.len().div_ceil(workers).max(1);
        std::thread::scope(|scope| {
            for batch in tiles.chunks_mut(chunk) {
                scope.spawn(move || {
                    for (values, codes, ex) in batch.iter_mut().map(|t| &mut **t) {
                        let (encoded, powers, _) = encode(values, c.components);
                        *codes = encoded;
                        *ex = powers;
                    }
                });
            }
        });
        if canonical
            .values()
            .any(|(_, _, ex)| ex.iter().any(|e| !(-48..=48).contains(e)))
        {
            return Err("tensor matrix exponent domain".into());
        }
        let mut column_covered = vec![false; op.columns.original.len()];
        let mut cursors = op.columns.offsets[..op.columns.offsets.len() - 1].to_vec();
        // Both sparse orientations are sorted. A linear permutation verifies
        // every original coefficient, including the untiled remainder.
        for row in 0..op.rows.offsets.len() - 1 {
            for (j, &covered) in row_covered
                .iter()
                .enumerate()
                .take(op.rows.offsets[row + 1] as usize)
                .skip(op.rows.offsets[row] as usize)
            {
                let col = op.rows.indices[j] as usize;
                let slot = cursors[col] as usize;
                if slot >= op.columns.offsets[col + 1] as usize
                    || op.columns.indices[slot] as usize != row
                    || op.columns.original[slot].to_bits() != op.rows.original[j].to_bits()
                {
                    return Err("noncanonical original transpose".into());
                }
                column_covered[slot] = covered;
                cursors[col] += 1;
            }
        }
        if cursors
            .iter()
            .zip(&op.columns.offsets[1..])
            .any(|(a, b)| a != b)
        {
            return Err("noncanonical original transpose size".into());
        }
        let make = |transpose: bool| {
            let original = op.orientation(transpose);
            let n = original.offsets.len() - 1;
            type HalfTile = (usize, (usize, usize), usize);
            let mut lists: Vec<Vec<HalfTile>> = vec![Vec::new(); n.div_ceil(16)];
            for &(r, col) in canonical.keys() {
                let (row, column) = if transpose { (col, r) } else { (r, col) };
                for half in 0..2 {
                    if row * 2 + half < lists.len() {
                        lists[row * 2 + half].push((column, (r, col), half));
                    }
                }
            }
            let mut t = Tiles {
                offsets: vec![0],
                columns: Vec::new(),
                fragments: Vec::new(),
                exponents: Vec::new(),
                metadata: Vec::new(),
                covered: vec![0; n],
                residual: Orientation {
                    offsets: vec![0],
                    indices: Vec::new().into(),
                    original: Vec::new().into(),
                    ids: Vec::new(),
                },
            };
            for list in &mut lists {
                list.sort_by_key(|v| v.0);
                for &(column, key, half) in list.iter() {
                    let (values, codes, ex) = &canonical[&key];
                    let index = |r: usize, col: usize| {
                        if transpose {
                            col * 32 + r
                        } else {
                            r * 32 + col
                        }
                    };
                    t.columns.push(column as u32);
                    t.exponents.extend(ex);
                    for h in 0..c.components {
                        for lane in 0..32 {
                            let mut packed = [0u32; 2];
                            for reg in 0..4 {
                                let row = half * 16 + lane / 4 + (reg % 2) * 8;
                                let col = (lane % 4) * 4 + (reg / 2) * 16;
                                let mut word = 0u32;
                                for z in 0..4 {
                                    let code = u32::from(codes[h * 1024 + index(row, col + z)]);
                                    word |= code << (2 + z * 8);
                                    packed[reg / 2] |= code << (16 * (reg % 2) + 4 * z);
                                }
                                if !c.compact_fragments {
                                    t.fragments.push(word);
                                }
                            }
                            if c.compact_fragments {
                                t.fragments.extend(packed);
                            }
                        }
                    }
                    for row in half * 16..half * 16 + if enclose { 16 } else { 0 } {
                        let (mut err, mut mag) = (0., 0.);
                        for col in 0..32 {
                            let j = index(row, col);
                            let mut value = 0.;
                            let mut local_mag = 0.;
                            for h in 0..c.components {
                                let part = decode(codes[h * 1024 + j]) * 2f64.powi(ex[h]);
                                value += part;
                                local_mag = upadd(local_mag, part.abs());
                                mag = upadd(mag, part.abs());
                            }
                            // Components and their sum are exact dyadics; allow
                            // subtraction rounding against the original coefficient.
                            let d = (values[j] - value).abs();
                            if d != 0. {
                                err = upadd(err, d.next_up());
                            }
                            if local_mag != 0. {
                                err = upadd(err, (4. * f64::EPSILON * local_mag).next_up());
                            }
                        }
                        t.metadata.extend([err, mag]);
                    }
                }
                t.offsets.push(t.columns.len() as u32);
            }
            for row in 0..n {
                for j in original.offsets[row] as usize..original.offsets[row + 1] as usize {
                    let col = original.indices[j] as usize;
                    if if transpose {
                        column_covered[j]
                    } else {
                        row_covered[j]
                    } {
                        t.covered[row] += 1;
                    } else {
                        t.residual.indices.to_mut().push(col as u32);
                        t.residual.original.to_mut().push(original.original[j]);
                    }
                }
                t.residual.offsets.push(t.residual.indices.len() as u32);
            }
            t
        };
        let (rows, columns) = if parallel && !enclose && canonical.len() >= 128 {
            std::thread::scope(|scope| {
                let columns = scope.spawn(|| make(true));
                (
                    make(false),
                    columns.join().expect("transpose packing worker"),
                )
            })
        } else {
            (make(false), make(true))
        };
        Ok(Self {
            rows,
            columns,
            components: c.components,
            tile_count: canonical.len(),
            compact_fragments: c.compact_fragments,
        })
    }
    pub fn storage_bytes(&self) -> usize {
        [&self.rows, &self.columns]
            .iter()
            .map(|t| {
                4 * (t.offsets.len()
                    + t.columns.len()
                    + t.fragments.len()
                    + t.exponents.len()
                    + t.covered.len()
                    + t.residual.offsets.len()
                    + t.residual.indices.len())
                    + 8 * (t.metadata.len() + t.residual.original.len())
            })
            .sum()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn parallel_proposal_packing_preserves_both_orientations_and_tails() {
        let n = 385usize;
        let make = |transpose| Orientation {
            offsets: (0..=n).map(|i| (i * n) as u32).collect(),
            indices: (0..n).flat_map(|_| 0..n as u32).collect(),
            original: (0..n)
                .flat_map(|i| {
                    (0..n).map(move |j| {
                        let (r, c) = if transpose { (j, i) } else { (i, j) };
                        ((r * 23 + c * 17) % 103) as f64 / 16. - 3.
                    })
                })
                .collect(),
            ids: Vec::new(),
        };
        let op = Operator {
            prepared: crate::operator::Format::Native,
            rows: make(false),
            columns: make(true),
            codes: Vec::new(),
            exponents: Vec::new(),
            fp32: Vec::new(),
        };
        for components in 1..=4 {
            for compact_fragments in [false, true] {
                let c = Config {
                    components,
                    compact_fragments,
                    ..Config::default()
                };
                let a = Packed::build_scheduled(&op, &c, false, false).unwrap();
                let b = Packed::proposal(&op, &c).unwrap();
                let indexed = crate::tensor_prepare::prepare(&op, &c).unwrap().unwrap();
                assert_eq!(
                    serde_json::to_value(&b).unwrap(),
                    serde_json::to_value(indexed).unwrap()
                );
                assert!(a.tile_count >= 128);
                assert_eq!(
                    serde_json::to_value(a).unwrap(),
                    serde_json::to_value(b).unwrap()
                );
            }
        }
    }
    #[test]
    fn quantization_preserves_normal_e2m1_nearest_even_boundaries() {
        let reference = |v: f64| {
            let mut best = 0;
            let mut error = v.abs();
            for c in 2..=7 {
                let e = (v.abs() - decode(c)).abs();
                if e < error || (e == error && c % 2 == 0 && best % 2 != 0) {
                    best = c;
                    error = e;
                }
            }
            best | if v < 0. && best != 0 { 8 } else { 0 }
        };
        for mid in [0.5f64, 1.25, 1.75, 2.5, 3.5, 5.] {
            for x in [mid.next_down(), mid, mid.next_up()] {
                for sign in [-1., 1.] {
                    assert_eq!(quant(sign * x), reference(sign * x));
                }
            }
        }
    }
}
