//! CPU-only attribution of unchanged preparation and exact byte binding.
use crate::identity::hex;
use crate::{Result, checker::Checker, model::Data};
use optimizer_core::lp_cost;
use optimizer_lp::LinearProgram;
use serde_json::json;
use std::{fs, hint::black_box, io::Write, time::Instant};

pub fn run(a: &[String]) -> Result<()> {
    if a.len() != 6 {
        return Err("startup-profile MODEL IMAGE COUNT OUTPUT".into());
    }
    let count: usize = a[4].parse()?;
    if !(1..=32).contains(&count) {
        return Err("profile count".into());
    }
    let bytes = fs::read(&a[2])?;
    let image = fs::read(&a[3])?;
    let executable = fs::read(std::env::current_exe()?)?;
    let mut rows = Vec::new();
    for repetition in 0..count {
        let order = if repetition % 2 == 0 {
            [0, 1, 2, 3, 4, 5]
        } else {
            [5, 4, 3, 2, 1, 0]
        };
        for operation in order {
            let session = lp_cost::Session::begin()?;
            let start = Instant::now();
            let label = match operation {
                0 => {
                    black_box(Data::new(black_box(&bytes), true)?);
                    "solver_data"
                }
                1 => {
                    black_box(Checker::new(black_box(&bytes))?);
                    "checker_data"
                }
                2 => {
                    let model = crate::parse::model(black_box(&bytes))?;
                    black_box(LinearProgram::new(&model)?);
                    "parse_and_lp"
                }
                3 => {
                    black_box(hex(black_box(&bytes)));
                    "model_hash"
                }
                4 => {
                    black_box(hex(black_box(&image)));
                    "image_hash"
                }
                _ => {
                    black_box(hex(black_box(&executable)));
                    "executable_hash"
                }
            };
            let elapsed = start.elapsed().as_nanos();
            rows.push(json!({"operation":label,"repetition":repetition,"ns":elapsed,"costs":session.finish()}));
        }
    }
    let mut f = fs::OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(&a[5])?;
    serde_json::to_writer(
        &mut f,
        &json!({"rows":rows,"model_sha256":hex(&bytes),"model_bytes":bytes.len(),"image_sha256":hex(&image),"executable_sha256":hex(&executable),"image_bytes":image.len(),"executable_bytes":executable.len()}),
    )?;
    f.write_all(b"\n")?;
    f.sync_all()?;
    Ok(())
}
