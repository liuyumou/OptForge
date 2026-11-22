//! Bounded scratch packing; final arrays retain the canonical representation.
use crate::{
    Result,
    operator::{Operator, Orientation},
    tensor::{Config, Packed, Tiles},
};
use std::sync::mpsc::{Receiver, SyncSender, sync_channel};

const BATCH: usize = 256;
type Key = (usize, usize);
struct Encoded {
    key: Key,
    codes: Vec<u8>,
    exponents: Vec<i32>,
}
struct Worker {
    send: SyncSender<Vec<Key>>,
    receive: Receiver<Vec<Encoded>>,
}
fn encode(op: &Operator, c: &Config, keys: &[Key]) -> Vec<Encoded> {
    let mut values = [0.; 1024];
    keys.iter()
        .map(|&(row, column)| {
            values.fill(0.);
            for i in row * 32..((row + 1) * 32).min(op.rows.offsets.len() - 1) {
                let lo = op.rows.offsets[i] as usize;
                let hi = op.rows.offsets[i + 1] as usize;
                let indices = &op.rows.indices[lo..hi];
                let begin = indices.partition_point(|&j| (j as usize) < column * 32);
                for (at, &j) in indices.iter().enumerate().skip(begin) {
                    if j as usize >= (column + 1) * 32 {
                        break;
                    }
                    values[(i % 32) * 32 + j as usize % 32] = op.rows.original[lo + at];
                }
            }
            let (codes, exponents) =
                crate::tensor_prepare_encode::encode(&mut values, c.components);
            Encoded {
                key: (row, column),
                codes,
                exponents,
            }
        })
        .collect()
}
fn flush(
    keys: &mut Vec<Key>,
    workers: &[Worker],
    op: &Operator,
    c: &Config,
    mut emit: impl FnMut(Encoded) -> Result<()>,
) -> Result<()> {
    if workers.is_empty() {
        for tile in encode(op, c, keys) {
            emit(tile)?;
        }
    } else {
        let chunk = keys.len().div_ceil(4);
        for (i, worker) in workers.iter().enumerate() {
            let lo = ((i + 1) * chunk).min(keys.len());
            let hi = ((i + 2) * chunk).min(keys.len());
            worker.send.send(keys[lo..hi].to_vec())?;
        }
        for tile in encode(op, c, &keys[..chunk]) {
            emit(tile)?;
        }
        for worker in workers {
            for tile in worker.receive.recv()? {
                emit(tile)?;
            }
        }
    }
    keys.clear();
    Ok(())
}
fn prefix(counts: &[u32]) -> Result<Vec<u32>> {
    let mut offsets = Vec::with_capacity(counts.len() + 1);
    offsets.push(0u32);
    for &count in counts {
        offsets.push(
            offsets
                .last()
                .unwrap()
                .checked_add(count)
                .ok_or("packing offset overflow")?,
        );
    }
    Ok(offsets)
}
fn allocate(
    original: &Orientation,
    tile_counts: Vec<u32>,
    covered: Vec<u32>,
    c: &Config,
) -> Result<Tiles> {
    let offsets = prefix(&tile_counts)?;
    drop(tile_counts);
    let halves = *offsets.last().unwrap() as usize;
    let words = c.components * 32 * if c.compact_fragments { 2 } else { 4 };
    let fragments = halves.checked_mul(words).ok_or("fragment size overflow")?;
    u32::try_from(fragments).map_err(|_| "fragment index overflow")?;
    let mut residual_offsets = Vec::with_capacity(covered.len() + 1);
    residual_offsets.push(0u32);
    for (i, &count) in covered.iter().enumerate() {
        let remaining = (original.offsets[i + 1] - original.offsets[i])
            .checked_sub(count)
            .ok_or("coverage exceeds original row")?;
        residual_offsets.push(
            residual_offsets
                .last()
                .unwrap()
                .checked_add(remaining)
                .ok_or("residual size overflow")?,
        );
    }
    let residual = *residual_offsets.last().unwrap() as usize;
    Ok(Tiles {
        offsets,
        columns: vec![0; halves],
        fragments: vec![0; fragments],
        exponents: vec![0; halves * c.components],
        metadata: Vec::new(),
        covered,
        residual: Orientation {
            offsets: residual_offsets,
            indices: vec![0; residual].into(),
            original: vec![0.; residual].into(),
            ids: Vec::new(),
        },
    })
}
fn emit(t: &mut Tiles, cursors: &mut [u32], tile: &Encoded, transpose: bool, c: &Config) {
    let (row, column) = if transpose {
        (tile.key.1, tile.key.0)
    } else {
        tile.key
    };
    let words = 32 * if c.compact_fragments { 2 } else { 4 };
    for half in 0..2 {
        let line = row * 2 + half;
        if line >= cursors.len() {
            continue;
        }
        let slot = cursors[line] as usize;
        cursors[line] += 1;
        t.columns[slot] = column as u32;
        t.exponents[slot * c.components..(slot + 1) * c.components]
            .copy_from_slice(&tile.exponents);
        for h in 0..c.components {
            let output = &mut t.fragments
                [(slot * c.components + h) * words..(slot * c.components + h + 1) * words];
            let mut at = 0;
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
                        output[at] = word;
                        at += 1;
                    }
                }
                if c.compact_fragments {
                    output[at..at + 2].copy_from_slice(&packed);
                    at += 2;
                }
            }
        }
    }
}
fn count(op: &Operator, first: usize, counts: &mut [usize], touched: &mut Vec<usize>) {
    let last = (first + 32).min(op.rows.offsets.len() - 1);
    for &col in &op.rows.indices[op.rows.offsets[first] as usize..op.rows.offsets[last] as usize] {
        let block = col as usize / 32;
        if counts[block] == 0 {
            touched.push(block);
        }
        counts[block] += 1;
    }
    touched.sort_unstable();
}
fn clear(counts: &mut [usize], touched: &mut Vec<usize>) {
    for &col in touched.iter() {
        counts[col] = 0;
    }
    touched.clear();
}
fn validate_entry(op: &Operator, row: usize, j: usize, cursors: &mut [u32]) -> Result<()> {
    let col = op.rows.indices[j] as usize;
    let slot = cursors[col] as usize;
    if slot >= op.columns.offsets[col + 1] as usize
        || op.columns.indices[slot] as usize != row
        || op.columns.original[slot].to_bits() != op.rows.original[j].to_bits()
    {
        return Err("noncanonical original transpose".into());
    }
    cursors[col] += 1;
    Ok(())
}

pub fn prepare(op: &Operator, c: &Config) -> Result<Option<Packed>> {
    c.validate()?;
    let (m, n) = (op.rows.offsets.len() - 1, op.columns.offsets.len() - 1);
    let mut counts = vec![0usize; n.div_ceil(32)];
    let mut touched = Vec::new();
    let mut geometry = None;
    let mut tile_count = 0;
    for first in (0..m).step_by(32) {
        count(op, first, &mut counts, &mut touched);
        for &col in &touched {
            if counts[col] < c.min_tile_nnz {
                continue;
            }
            let (rows, columns, _, _) = geometry.get_or_insert_with(|| {
                (
                    vec![0u32; m.div_ceil(16)],
                    vec![0u32; n.div_ceil(16)],
                    vec![0u32; m],
                    vec![0u32; n],
                )
            });
            for half in 0..2 {
                if first / 16 + half < rows.len() {
                    rows[first / 16 + half] += 1;
                }
                if col * 2 + half < columns.len() {
                    columns[col * 2 + half] += 1;
                }
            }
            tile_count += 1;
        }
        if let Some((_, _, rows, columns)) = &mut geometry {
            for (row, covered) in rows
                .iter_mut()
                .enumerate()
                .take((first + 32).min(m))
                .skip(first)
            {
                for &col in &op.rows.indices
                    [op.rows.offsets[row] as usize..op.rows.offsets[row + 1] as usize]
                {
                    if counts[col as usize / 32] >= c.min_tile_nnz {
                        *covered += 1;
                        columns[col as usize] += 1;
                    }
                }
            }
        }
        clear(&mut counts, &mut touched);
    }
    let mut original_cursors = op.columns.offsets[..n].to_vec();
    let Some((row_tiles, column_tiles, row_covered, column_covered)) = geometry else {
        for row in 0..m {
            for j in op.rows.offsets[row] as usize..op.rows.offsets[row + 1] as usize {
                validate_entry(op, row, j, &mut original_cursors)?;
            }
        }
        if original_cursors != op.columns.offsets[1..] {
            return Err("noncanonical original transpose size".into());
        }
        return Ok(None);
    };
    let mut rows = allocate(&op.rows, row_tiles, row_covered, c)?;
    let mut columns = allocate(&op.columns, column_tiles, column_covered, c)?;
    let mut row_cursors = rows.offsets[..rows.offsets.len() - 1].to_vec();
    let mut column_cursors = columns.offsets[..columns.offsets.len() - 1].to_vec();
    let mut residual_cursors = columns.residual.offsets[..n].to_vec();
    std::thread::scope(|scope| -> Result<()> {
        let mut workers = Vec::new();
        if tile_count >= 128 {
            for _ in 0..3 {
                let (send, jobs) = sync_channel::<Vec<Key>>(1);
                let (results, receive) = sync_channel(1);
                scope.spawn(move || {
                    while let Ok(keys) = jobs.recv() {
                        if results.send(encode(op, c, &keys)).is_err() {
                            break;
                        }
                    }
                });
                workers.push(Worker { send, receive });
            }
        }
        let mut keys = Vec::with_capacity(BATCH);
        let mut encode_batch =
            |keys: &mut Vec<Key>, rows: &mut Tiles, columns: &mut Tiles| -> Result<()> {
                flush(keys, &workers, op, c, |tile| {
                    if tile.exponents.iter().any(|e| !(-48..=48).contains(e)) {
                        return Err("tensor matrix exponent domain".into());
                    }
                    emit(rows, &mut row_cursors, &tile, false, c);
                    emit(columns, &mut column_cursors, &tile, true, c);
                    Ok(())
                })
            };
        for first in (0..m).step_by(32) {
            count(op, first, &mut counts, &mut touched);
            for &col in &touched {
                if counts[col] >= c.min_tile_nnz {
                    keys.push((first / 32, col));
                    if keys.len() == BATCH {
                        encode_batch(&mut keys, &mut rows, &mut columns)?;
                    }
                }
            }
            for row in first..(first + 32).min(m) {
                let mut at = rows.residual.offsets[row] as usize;
                for j in op.rows.offsets[row] as usize..op.rows.offsets[row + 1] as usize {
                    validate_entry(op, row, j, &mut original_cursors)?;
                    let col = op.rows.indices[j] as usize;
                    if counts[col / 32] < c.min_tile_nnz {
                        let slot = residual_cursors[col] as usize;
                        rows.residual.indices.to_mut()[at] = col as u32;
                        rows.residual.original.to_mut()[at] = op.rows.original[j];
                        columns.residual.indices.to_mut()[slot] = row as u32;
                        columns.residual.original.to_mut()[slot] = op.rows.original[j];
                        residual_cursors[col] += 1;
                        at += 1;
                    }
                }
                if at != rows.residual.offsets[row + 1] as usize {
                    return Err("residual row count differs".into());
                }
            }
            clear(&mut counts, &mut touched);
        }
        if !keys.is_empty() {
            encode_batch(&mut keys, &mut rows, &mut columns)?;
        }
        Ok(())
    })?;
    if original_cursors != op.columns.offsets[1..]
        || residual_cursors != columns.residual.offsets[1..]
        || row_cursors != rows.offsets[1..]
        || column_cursors != columns.offsets[1..]
    {
        return Err("noncanonical packing sizes".into());
    }
    Ok(Some(Packed {
        rows,
        columns,
        components: c.components,
        tile_count,
        compact_fragments: c.compact_fragments,
    }))
}
