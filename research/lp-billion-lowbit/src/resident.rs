//! Solve-local ownership transfer. Kernels and host reference arrays are unchanged.
use crate::{
    Result,
    device::{DEVICE, upload},
    operator::Orientation,
};
use optimizer_cuda_sys::{Context, DeviceBuffer, Stream};
use optimizer_lp::Compressed;
use std::rc::Rc;

pub(crate) struct Matrix {
    pub offsets: DeviceBuffer<u32>,
    pub indices: DeviceBuffer<u32>,
    pub values: DeviceBuffer<f64>,
    pub n: usize,
}
impl Matrix {
    pub fn compressed(p: &Compressed, ctx: &Rc<Context>, stream: &Stream) -> Result<Self> {
        let (offsets, indices, values) = p.arrays();
        let offsets = offsets
            .iter()
            .map(|&v| u32::try_from(v))
            .collect::<std::result::Result<Vec<_>, _>>()?;
        Ok(Self {
            offsets: upload(ctx, stream, &offsets)?,
            indices: upload(ctx, stream, indices)?,
            values: upload(ctx, stream, values)?,
            n: p.lines(),
        })
    }
    pub fn new(p: &Orientation, ctx: &Rc<Context>, stream: &Stream) -> Result<Self> {
        Ok(Self {
            offsets: upload(ctx, stream, &p.offsets)?,
            indices: upload(ctx, stream, &p.indices)?,
            values: upload(ctx, stream, &p.original)?,
            n: p.offsets.len() - 1,
        })
    }
    pub fn bytes(&self) -> usize {
        4 * (self.offsets.len() + self.indices.len()) + 8 * self.values.len()
    }
}
pub(crate) struct Tiles {
    pub offsets: DeviceBuffer<u32>,
    pub columns: DeviceBuffer<u32>,
    pub fragments: DeviceBuffer<u32>,
    pub exponents: DeviceBuffer<i32>,
    pub residual_offsets: DeviceBuffer<u32>,
    pub residual_indices: DeviceBuffer<u32>,
}
impl Tiles {
    pub fn bytes(&self) -> usize {
        4 * (self.offsets.len()
            + self.columns.len()
            + self.fragments.len()
            + self.exponents.len()
            + self.residual_offsets.len()
            + self.residual_indices.len())
    }
}
pub(crate) struct Resident {
    pub ctx: Rc<Context>,
    pub stream: Rc<Stream>,
    pub rows: Option<Matrix>,
    pub columns: Option<Matrix>,
    pub row_tiles: Option<Tiles>,
    pub column_tiles: Option<Tiles>,
    pub avoided_upload_bytes: usize,
}
impl Resident {
    pub fn new() -> Result<Self> {
        if std::env::var("AI_OPTIMIZER_GPU_LEASE").as_deref() != Ok("inherited")
            || std::env::var("CUDA_VISIBLE_DEVICES").as_deref() != Ok(DEVICE)
        {
            return Err("pinned shared lease required for resident preparation".into());
        }
        let ctx = Rc::new(Context::create(DEVICE)?);
        let stream = Rc::new(ctx.stream()?);
        Ok(Self {
            ctx,
            stream,
            rows: None,
            columns: None,
            row_tiles: None,
            column_tiles: None,
            avoided_upload_bytes: 0,
        })
    }
}
