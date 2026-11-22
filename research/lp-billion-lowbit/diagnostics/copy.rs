//! Exercise the admitted safe offset-copy implementation across real chunk boundaries.
use optimizer_cuda_sys::Context;
use std::rc::Rc;
fn main() -> Result<(), Box<dyn std::error::Error>> {
    const CHUNK: usize = 8 << 20;
    let len = 2 * CHUNK + 17;
    let ctx = Rc::new(Context::create("GPU-6721b13a-30f9-83ec-dace-ba2d9738556f")?);
    let stream = ctx.stream()?;
    let mut device = ctx.allocate::<f32>(len)?;
    let value = |i: usize| f32::from_bits(0x3f800000 + (i % 8191) as u32);
    let mut calls = 0;
    for offset in (0..len).step_by(CHUNK) {
        let input: Vec<f32> = (offset..(offset + CHUNK).min(len)).map(value).collect();
        device.copy_from_at(offset, &input, &stream)?;
        calls += 1;
    }
    device.copy_from_at(len, &[], &stream)?;
    assert!(device.copy_from_at(len, &[1.], &stream).is_err());
    let mut actual = vec![0.; len];
    device.copy_to(&mut actual, &stream)?;
    assert!(actual.iter().enumerate().all(|(i, v)| v.to_bits() == value(i).to_bits()));
    println!("{{\"status\":\"passed\",\"elements\":{len},\"chunk_copies\":{calls},\"partial_tail_elements\":17,\"bitwise_exact\":true}}");
    Ok(())
}
