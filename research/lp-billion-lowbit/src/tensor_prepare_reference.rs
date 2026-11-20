//! Exact proposal packing with ordered tile indices and no discarded residuals.
use crate::{
    Result,
    operator::{Operator, Orientation},
    tensor::{Config, Packed, Tiles},
};

struct Tile {
    row: usize,
    column: usize,
    values: Vec<f64>,
    codes: Vec<u8>,
    exponents: Vec<i32>,
}

/// The caller selects sparse FP32 when no canonical FP4 tile qualifies. Transpose
/// validation still visits every coefficient before returning that empty result.
pub fn prepare(op: &Operator, c: &Config) -> Result<Option<Packed>> {
    c.validate()?;
    let mut canonical: Vec<Tile> = Vec::new();
    let mut covered_nnz = 0;
    let mut row_covered = vec![false; op.rows.original.len()];
    let blocks = (op.columns.offsets.len() - 1).div_ceil(32);
    let mut counts = vec![0usize; blocks];
    let mut slots = vec![usize::MAX; blocks];
    let mut touched = Vec::new();
    for first in (0..op.rows.offsets.len() - 1).step_by(32) {
        let last = (first + 32).min(op.rows.offsets.len() - 1);
        let lo = op.rows.offsets[first] as usize;
        let hi = op.rows.offsets[last] as usize;
        touched.clear();
        for &col in &op.rows.indices[lo..hi] {
            let block = col as usize / 32;
            if counts[block] == 0 {
                touched.push(block);
            }
            counts[block] += 1;
        }
        touched.sort_unstable();
        let begin = canonical.len();
        for &col in &touched {
            if counts[col] >= c.min_tile_nnz {
                covered_nnz += counts[col];
                slots[col] = canonical.len();
                canonical.push(Tile {
                    row: first / 32,
                    column: col,
                    values: vec![0.; 1024],
                    codes: Vec::new(),
                    exponents: Vec::new(),
                });
            }
        }
        if canonical.len() != begin {
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
                        canonical[slot].values[(row % 32) * 32 + col % 32] = value;
                        *covered = true;
                    }
                }
            }
        }
        for &col in &touched {
            counts[col] = 0;
            slots[col] = usize::MAX;
        }
    }
    let no_tiles = canonical.is_empty();
    if !no_tiles {
        let workers = if canonical.len() >= 128 { 4 } else { 1 };
        let chunk = canonical.len().div_ceil(workers);
        std::thread::scope(|scope| {
            for batch in canonical.chunks_mut(chunk) {
                scope.spawn(move || {
                    for tile in batch {
                        let (codes, exponents) =
                            crate::tensor_prepare_encode::encode(&mut tile.values, c.components);
                        tile.codes = codes;
                        tile.exponents = exponents;
                        tile.values = Vec::new();
                    }
                });
            }
        });
    }
    if canonical
        .iter()
        .any(|tile| tile.exponents.iter().any(|e| !(-48..=48).contains(e)))
    {
        return Err("tensor matrix exponent domain".into());
    }
    let mut column_covered = vec![
        false;
        if no_tiles {
            0
        } else {
            op.columns.original.len()
        }
    ];
    let mut cursors = op.columns.offsets[..op.columns.offsets.len() - 1].to_vec();
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
            if !no_tiles {
                column_covered[slot] = covered;
            }
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
    if no_tiles {
        return Ok(None);
    }
    let make = |transpose: bool| {
        let original = op.orientation(transpose);
        let n = original.offsets.len() - 1;
        let mut lists: Vec<Vec<(usize, usize, usize)>> = vec![Vec::new(); n.div_ceil(16)];
        for (id, tile) in canonical.iter().enumerate() {
            let (row, column) = if transpose {
                (tile.column, tile.row)
            } else {
                (tile.row, tile.column)
            };
            for half in 0..2 {
                if row * 2 + half < lists.len() {
                    lists[row * 2 + half].push((column, id, half));
                }
            }
        }
        let halves: usize = lists.iter().map(Vec::len).sum();
        let mut offsets = Vec::with_capacity(lists.len() + 1);
        offsets.push(0);
        let mut residual_offsets = Vec::with_capacity(n + 1);
        residual_offsets.push(0);
        let residual_nnz = original.original.len() - covered_nnz;
        let mut t = Tiles {
            offsets,
            columns: Vec::with_capacity(halves),
            fragments: Vec::with_capacity(
                halves * c.components * 32 * if c.compact_fragments { 2 } else { 4 },
            ),
            exponents: Vec::with_capacity(halves * c.components),
            metadata: Vec::new(),
            covered: vec![0; n],
            residual: Orientation {
                offsets: residual_offsets,
                indices: Vec::with_capacity(residual_nnz).into(),
                original: Vec::with_capacity(residual_nnz).into(),
                ids: Vec::new(),
            },
        };
        for list in &mut lists {
            list.sort_by_key(|v| v.0);
            for &(column, id, half) in list.iter() {
                let tile = &canonical[id];
                t.columns.push(column as u32);
                t.exponents.extend(&tile.exponents);
                for h in 0..c.components {
                    for lane in 0..32 {
                        let mut packed = [0u32; 2];
                        for reg in 0..4 {
                            let row = half * 16 + lane / 4 + (reg % 2) * 8;
                            let col = (lane % 4) * 4 + (reg / 2) * 16;
                            let mut word = 0u32;
                            for z in 0..4 {
                                let index = if transpose {
                                    (col + z) * 32 + row
                                } else {
                                    row * 32 + col + z
                                };
                                let code = u32::from(tile.codes[h * 1024 + index]);
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
            }
            t.offsets.push(t.columns.len() as u32);
        }
        let indices = t.residual.indices.to_mut();
        let values = t.residual.original.to_mut();
        for row in 0..n {
            for j in original.offsets[row] as usize..original.offsets[row + 1] as usize {
                let covered = if transpose {
                    column_covered[j]
                } else {
                    row_covered[j]
                };
                if covered {
                    t.covered[row] += 1;
                } else {
                    indices.push(original.indices[j]);
                    values.push(original.original[j]);
                }
            }
            t.residual.offsets.push(indices.len() as u32);
        }
        t
    };
    let (rows, columns) = if canonical.len() >= 128 {
        std::thread::scope(|scope| {
            let columns = scope.spawn(|| make(true));
            (
                make(false),
                columns.join().expect("indexed transpose packing worker"),
            )
        })
    } else {
        (make(false), make(true))
    };
    Ok(Some(Packed {
        rows,
        columns,
        components: c.components,
        tile_count: canonical.len(),
        compact_fragments: c.compact_fragments,
    }))
}
