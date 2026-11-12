//! CPU-only attribution and exact endpoint replay, never an unchecked fast path.
use crate::{Result, checker};
use serde_json::json;
use std::{fs, hint::black_box, time::Instant};
pub fn run(a: &[String]) -> Result<()> {
    if a.len() != 7 {
        return Err("profile MODEL ENDPOINT TIER COUNT OUTPUT".into());
    }
    let c = checker::Checker::new(&fs::read(&a[2])?)?;
    let e = serde_json::from_slice(&fs::read(&a[3])?)?;
    let count: usize = a[5].parse()?;
    if count == 0 || count > 1000 {
        return Err("profile count".into());
    }
    let original = c.assess_mode(&e, &a[4], true)?;
    let candidate = c.assess(&e, &a[4])?;
    if original != candidate {
        return Err("certificate mismatch".into());
    }
    let mut rows = Vec::new();
    for repetition in 0..count {
        for serial in if repetition % 2 == 0 {
            [true, false]
        } else {
            [false, true]
        } {
            let session = optimizer_core::lp_cost::Session::begin()?;
            let start = Instant::now();
            let result = black_box(c.assess_mode(black_box(&e), &a[4], serial)?);
            let ns = start.elapsed().as_nanos();
            let costs = session.finish();
            if result != original {
                return Err("repeated certificate mismatch".into());
            }
            rows.push(json!({"baseline":serial,"repetition":repetition,"ns":ns,"costs":costs}));
        }
    }
    let result = json!({"certificate":original,"rows":rows});
    let mut f = fs::OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(&a[6])?;
    serde_json::to_writer(&mut f, &result)?;
    f.sync_all()?;
    Ok(())
}
