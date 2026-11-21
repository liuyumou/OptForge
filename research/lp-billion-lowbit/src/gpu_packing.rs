//! GPU scans and exact canonical FP4 packing; host work is O(axes + tiles).
use crate::{
    Result,
    device::{DEVICE, pointer, read, upload},
    operator::{MAX_DIMENSION, MAX_NONZEROS, Operator, Orientation},
    tensor::{Config, Packed, Tiles},
};
use optimizer_cuda_sys::{
    Argument as A, Context, DeviceBuffer, LaunchConfig, Module, Stream, launch,
};
use serde_json::{Value, json};
use std::{path::Path, rc::Rc, time::Instant};

fn prefix(counts: &[u32]) -> Result<Vec<u32>> {
    let mut result = Vec::with_capacity(counts.len() + 1);
    result.push(0u32);
    for &n in counts {
        result.push(
            result
                .last()
                .unwrap()
                .checked_add(n)
                .ok_or("packing offset overflow")?,
        );
    }
    Ok(result)
}
fn shape(op: &Operator) -> Result<(usize, usize, usize)> {
    let m = op
        .rows
        .offsets
        .len()
        .checked_sub(1)
        .ok_or("missing row offsets")?;
    let n = op
        .columns
        .offsets
        .len()
        .checked_sub(1)
        .ok_or("missing column offsets")?;
    let z = op.rows.indices.len();
    if m.max(n) > MAX_DIMENSION || z > MAX_NONZEROS || op.columns.indices.len() != z {
        return Err("GPU packing shape domain".into());
    }
    for o in [&op.rows, &op.columns] {
        if o.original.len() != z
            || o.offsets[0] != 0
            || o.offsets.last() != Some(&(z as u32))
            || o.offsets.windows(2).any(|w| w[0] > w[1])
        {
            return Err("GPU packing compressed shape".into());
        }
    }
    Ok((m, n, z))
}
fn capacity(bytes: usize) -> Result<usize> {
    if bytes > 80usize << 30 {
        return Err("GPU packing allocation limit".into());
    }
    Ok(bytes)
}
struct Matrix {
    offsets: DeviceBuffer<u32>,
    indices: DeviceBuffer<u32>,
    values: DeviceBuffer<f64>,
    n: usize,
}
impl Matrix {
    fn new(o: &Orientation, ctx: &Rc<Context>, s: &Stream) -> Result<Self> {
        Ok(Self {
            offsets: upload(ctx, s, &o.offsets)?,
            indices: upload(ctx, s, &o.indices)?,
            values: upload(ctx, s, &o.original)?,
            n: o.offsets.len() - 1,
        })
    }
}
struct Gpu {
    ctx: Rc<Context>,
    module: Module,
    stream: Stream,
}
impl Gpu {
    fn call(&self, name: &str, grid: usize, args: &[A]) -> Result<()> {
        if grid != 0 {
            launch(
                &self.module.function(name)?,
                LaunchConfig {
                    grid: u32::try_from(grid)?,
                    block: 256,
                    shared_memory: 0,
                },
                args,
                &self.stream,
            )?;
        }
        Ok(())
    }
    fn sync(&self) -> Result<()> {
        Ok(self.stream.synchronize()?)
    }
}
struct Geometry {
    offsets: Vec<u32>,
    columns: Vec<u32>,
}
fn geometry(
    m: usize,
    n: usize,
    offsets: &[u32],
    keys: &mut [u32],
) -> Result<(Geometry, Geometry, Vec<u32>)> {
    let mut rcounts = vec![0; m.div_ceil(16)];
    let mut ccounts = vec![0; n.div_ceil(16)];
    for group in 0..offsets.len() - 1 {
        let slice = &mut keys[offsets[group] as usize..offsets[group + 1] as usize];
        slice.sort_unstable();
        if slice.windows(2).any(|w| w[0] >= w[1]) {
            return Err("duplicate GPU tile".into());
        }
        for &col in slice.iter() {
            if col as usize >= n.div_ceil(32) {
                return Err("GPU tile domain".into());
            }
            for half in 0..2 {
                if group * 2 + half < rcounts.len() {
                    rcounts[group * 2 + half] += 1;
                }
                if (col as usize) * 2 + half < ccounts.len() {
                    ccounts[(col as usize) * 2 + half] += 1;
                }
            }
        }
    }
    let ro = prefix(&rcounts)?;
    let co = prefix(&ccounts)?;
    let mut rc = vec![0; *ro.last().unwrap() as usize];
    let mut cc = vec![0; *co.last().unwrap() as usize];
    let mut cursor = co[..co.len() - 1].to_vec();
    let mut tiles = Vec::with_capacity(keys.len() * 6);
    for group in 0..offsets.len() - 1 {
        for (rank, &col) in keys[offsets[group] as usize..offsets[group + 1] as usize]
            .iter()
            .enumerate()
        {
            let mut tile = [group as u32, col, u32::MAX, u32::MAX, u32::MAX, u32::MAX];
            for half in 0..2 {
                if group * 2 + half < rcounts.len() {
                    let slot = ro[group * 2 + half] + rank as u32;
                    rc[slot as usize] = col;
                    tile[2 + half] = slot;
                }
                let line = col as usize * 2 + half;
                if line < ccounts.len() {
                    let slot = cursor[line];
                    cursor[line] += 1;
                    cc[slot as usize] = group as u32;
                    tile[4 + half] = slot;
                }
            }
            tiles.extend(tile);
        }
    }
    Ok((
        Geometry {
            offsets: ro,
            columns: rc,
        },
        Geometry {
            offsets: co,
            columns: cc,
        },
        tiles,
    ))
}
struct Output {
    geometry: Geometry,
    offsets: DeviceBuffer<u32>,
    columns: DeviceBuffer<u32>,
    covered: DeviceBuffer<u32>,
    fragments: DeviceBuffer<u32>,
    exponents: DeviceBuffer<i32>,
    fragment_len: usize,
    exponent_len: usize,
}
impl Output {
    fn sizes(g: &Geometry, c: &Config) -> Result<(usize, usize)> {
        let exponents = g
            .columns
            .len()
            .checked_mul(c.components)
            .ok_or("packing exponent size")?;
        let fragments = exponents
            .checked_mul(if c.compact_fragments { 64 } else { 128 })
            .ok_or("packing fragment size")?;
        u32::try_from(fragments).map_err(|_| "packing fragment index overflow")?;
        Ok((fragments, exponents))
    }
    fn new(g: Geometry, n: usize, c: &Config, gpu: &Gpu) -> Result<Self> {
        let (fragment_len, exponent_len) = Self::sizes(&g, c)?;
        Ok(Self {
            offsets: upload(&gpu.ctx, &gpu.stream, &g.offsets)?,
            columns: upload(&gpu.ctx, &gpu.stream, &g.columns)?,
            covered: gpu.ctx.allocate(n.max(1))?,
            fragments: gpu.ctx.allocate(fragment_len.max(1))?,
            exponents: gpu.ctx.allocate(exponent_len.max(1))?,
            geometry: g,
            fragment_len,
            exponent_len,
        })
    }
    fn finish(self, m: &Matrix, o: &Orientation, gpu: &Gpu) -> Result<Tiles> {
        let covered = read(&self.covered, &gpu.stream, m.n)?;
        let mut remaining = Vec::with_capacity(m.n);
        for (i, &count) in covered.iter().enumerate() {
            remaining.push(
                (o.offsets[i + 1] - o.offsets[i])
                    .checked_sub(count)
                    .ok_or("GPU coverage exceeds row")?,
            );
        }
        let offsets = prefix(&remaining)?;
        drop(remaining);
        let z = *offsets.last().unwrap() as usize;
        let d_offsets = upload(&gpu.ctx, &gpu.stream, &offsets)?;
        let indices = gpu.ctx.allocate::<u32>(z.max(1))?;
        let values = gpu.ctx.allocate::<f64>(z.max(1))?;
        gpu.call(
            "pack_residual",
            m.n.div_ceil(256),
            &[
                pointer(&m.offsets),
                pointer(&m.indices),
                pointer(&m.values),
                pointer(&self.offsets),
                pointer(&self.columns),
                pointer(&d_offsets),
                pointer(&indices),
                pointer(&values),
                A::U32(m.n as u32),
            ],
        )?;
        gpu.sync()?;
        Ok(Tiles {
            offsets: self.geometry.offsets,
            columns: self.geometry.columns,
            covered,
            fragments: read(&self.fragments, &gpu.stream, self.fragment_len)?,
            exponents: read(&self.exponents, &gpu.stream, self.exponent_len)?,
            metadata: Vec::new(),
            residual: Orientation {
                offsets,
                indices: if z == 0 {
                    Vec::new()
                } else {
                    read(&indices, &gpu.stream, z)?
                }
                .into(),
                original: if z == 0 {
                    Vec::new()
                } else {
                    read(&values, &gpu.stream, z)?
                }
                .into(),
                ids: Vec::new(),
            },
        })
    }
}
/// Allocates no tile fragments or residual arrays when no tile is eligible.
/// A bounded structural hash overflow explicitly falls back to canonical host packing.
pub fn prepare(op: &Operator, c: &Config, image: &Path) -> Result<(Option<Packed>, Value)> {
    c.validate()?;
    let started = Instant::now();
    let (m, n, z) = shape(op)?;
    if std::env::var("AI_OPTIMIZER_GPU_LEASE").as_deref() != Ok("inherited")
        || std::env::var("CUDA_VISIBLE_DEVICES").as_deref() != Ok(DEVICE)
    {
        return Err("pinned shared lease required for GPU packing".into());
    }
    let base_bytes = capacity(24 * z + 4 * (m + n + 2) + 8 * m.div_ceil(32) + 64)?;
    let ctx = Rc::new(Context::create(DEVICE)?);
    let stream = ctx.stream()?;
    let module = ctx.load_module_file(image)?;
    let gpu = Gpu {
        ctx,
        module,
        stream,
    };
    let rows = Matrix::new(&op.rows, &gpu.ctx, &gpu.stream)?;
    let columns = Matrix::new(&op.columns, &gpu.ctx, &gpu.stream)?;
    let bad = upload(&gpu.ctx, &gpu.stream, &[0u32])?;
    gpu.sync()?;
    let uploaded = started.elapsed().as_nanos();
    for (matrix, other) in [(&rows, n), (&columns, m)] {
        gpu.call(
            "pack_validate",
            matrix.n.div_ceil(256),
            &[
                pointer(&matrix.offsets),
                pointer(&matrix.indices),
                pointer(&matrix.values),
                A::U32(matrix.n as u32),
                A::U32(other as u32),
                pointer(&bad),
            ],
        )?;
    }
    gpu.sync()?;
    if read(&bad, &gpu.stream, 1)?[0] != 0 {
        return Err("GPU packing coefficient/index domain".into());
    }
    gpu.call(
        "pack_transpose",
        m.div_ceil(256),
        &[
            pointer(&rows.offsets),
            pointer(&rows.indices),
            pointer(&rows.values),
            pointer(&columns.offsets),
            pointer(&columns.indices),
            pointer(&columns.values),
            A::U32(m as u32),
            pointer(&bad),
        ],
    )?;
    gpu.sync()?;
    if read(&bad, &gpu.stream, 1)?[0] != 0 {
        return Err("noncanonical original transpose".into());
    }
    let validated = started.elapsed().as_nanos();
    let groups = m.div_ceil(32);
    let counts = gpu.ctx.allocate::<u32>(groups.max(1))?;
    // Unused emit pointers are valid allocations, even in the zero-eligible pass.
    gpu.call(
        "pack_eligible",
        groups,
        &[
            pointer(&rows.offsets),
            pointer(&rows.indices),
            A::U32(m as u32),
            A::U32(c.min_tile_nnz as u32),
            pointer(&counts),
            pointer(&counts),
            pointer(&counts),
            A::U32(0),
            pointer(&bad),
        ],
    )?;
    gpu.sync()?;
    if read(&bad, &gpu.stream, 1)?[0] != 0 {
        drop(counts);
        drop(bad);
        drop(rows);
        drop(columns);
        drop(gpu);
        let result = crate::tensor_prepare::prepare(op, c)?;
        return Ok((
            result,
            json!({"backend":"host_hash_overflow","total_ns":started.elapsed().as_nanos(),"allocated_bytes_upper":base_bytes}),
        ));
    }
    let counts_host = if groups == 0 {
        Vec::new()
    } else {
        read(&counts, &gpu.stream, groups)?
    };
    let offsets = prefix(&counts_host)?;
    let tile_count = *offsets.last().unwrap() as usize;
    let detected = started.elapsed().as_nanos();
    if tile_count == 0 {
        return Ok((
            None,
            json!({"backend":"gpu","eligible_tiles":0,"skipped":true,"upload_ns":uploaded,
        "validation_ns":validated-uploaded,"eligibility_ns":detected-validated,"allocated_bytes_upper":base_bytes,"total_ns":detected}),
        ));
    }
    // Reject unsupported final fragment indices before allocating tile metadata.
    let words = if c.compact_fragments { 64 } else { 128 };
    let half_upper = tile_count.checked_mul(2).ok_or("tile count overflow")?;
    let fragment_upper = half_upper
        .checked_mul(c.components * words)
        .ok_or("fragment count overflow")?;
    u32::try_from(fragment_upper).map_err(|_| "packing fragment index overflow")?;
    capacity(
        base_bytes
            + 24 * z
            + 12 * (m + n + 2)
            + 40 * tile_count
            + 8 * (fragment_upper + half_upper * c.components + half_upper)
            + 1024,
    )?;
    let d_offsets = upload(&gpu.ctx, &gpu.stream, &offsets)?;
    let d_keys = gpu.ctx.allocate::<u32>(tile_count)?;
    gpu.call(
        "pack_eligible",
        groups,
        &[
            pointer(&rows.offsets),
            pointer(&rows.indices),
            A::U32(m as u32),
            A::U32(c.min_tile_nnz as u32),
            pointer(&counts),
            pointer(&d_offsets),
            pointer(&d_keys),
            A::U32(1),
            pointer(&bad),
        ],
    )?;
    gpu.sync()?;
    if read(&bad, &gpu.stream, 1)?[0] != 0 || read(&counts, &gpu.stream, groups)? != counts_host {
        return Err("GPU tile-count replay differs".into());
    }
    let mut keys = read(&d_keys, &gpu.stream, tile_count)?;
    let (rgeom, cgeom, geometry) = geometry(m, n, &offsets, &mut keys)?;
    let (rf, re) = Output::sizes(&rgeom, c)?;
    let (cf, ce) = Output::sizes(&cgeom, c)?;
    // Conservative peak: both residual orientations, all fragments, both geometries,
    // coverage, original matrices, tile keys and coordinates; includes padding.
    let allocated = capacity(
        base_bytes
            + 24 * z
            + 12 * (m + n + 2)
            + 40 * tile_count
            + 4 * (rf + re + cf + ce + rgeom.columns.len() + cgeom.columns.len())
            + 1024,
    )?;
    let r = Output::new(rgeom, m, c, &gpu)?;
    let col = Output::new(cgeom, n, c, &gpu)?;
    let d_geometry = upload(&gpu.ctx, &gpu.stream, &geometry)?;
    drop(keys);
    drop(geometry);
    drop(d_keys);
    drop(d_offsets);
    drop(counts);
    for (matrix, out) in [(&rows, &r), (&columns, &col)] {
        gpu.call(
            "pack_coverage",
            matrix.n.div_ceil(256),
            &[
                pointer(&matrix.offsets),
                pointer(&matrix.indices),
                pointer(&out.offsets),
                pointer(&out.columns),
                pointer(&out.covered),
                A::U32(matrix.n as u32),
            ],
        )?;
    }
    gpu.sync()?;
    let arranged = started.elapsed().as_nanos();
    gpu.call(
        "pack_encode",
        tile_count,
        &[
            pointer(&rows.offsets),
            pointer(&rows.indices),
            pointer(&rows.values),
            pointer(&d_geometry),
            A::U32(m as u32),
            A::U32(c.components as u32),
            A::U32(u32::from(c.compact_fragments)),
            pointer(&r.fragments),
            pointer(&r.exponents),
            pointer(&col.fragments),
            pointer(&col.exponents),
        ],
    )?;
    gpu.sync()?;
    let encoded = started.elapsed().as_nanos();
    let result = Packed {
        rows: r.finish(&rows, &op.rows, &gpu)?,
        columns: col.finish(&columns, &op.columns, &gpu)?,
        components: c.components,
        tile_count,
        compact_fragments: c.compact_fragments,
    };
    let done = started.elapsed().as_nanos();
    Ok((
        Some(result),
        json!({"backend":"gpu","eligible_tiles":tile_count,"skipped":false,"upload_ns":uploaded,
        "validation_ns":validated-uploaded,"eligibility_ns":detected-validated,"geometry_coverage_ns":arranged-detected,
        "encoding_ns":encoded-arranged,"residual_download_ns":done-encoded,"total_ns":done,"allocated_bytes_upper":allocated}),
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn geometry_has_canonical_half_and_transpose_order() {
        let (r, c, g) = geometry(49, 65, &[0, 2, 3], &mut [2, 0, 0]).unwrap();
        assert_eq!(r.offsets, [0, 2, 4, 5, 6]);
        assert_eq!(r.columns, [0, 2, 0, 2, 0, 0]);
        assert_eq!(c.offsets, [0, 2, 4, 4, 4, 5]);
        assert_eq!(c.columns, [0, 1, 0, 1, 0]);
        assert_eq!(
            g,
            [0, 0, 0, 2, 0, 2, 0, 2, 1, 3, 4, u32::MAX, 1, 0, 4, 5, 1, 3]
        );
    }
    #[test]
    fn geometry_and_sizes_fail_closed() {
        assert!(prefix(&[u32::MAX, 1]).is_err());
        assert!(geometry(32, 32, &[0, 2], &mut [0, 0]).is_err());
        assert!(geometry(32, 32, &[0, 1], &mut [1]).is_err());
        assert!(capacity((80usize << 30) + 1).is_err());
    }
}
