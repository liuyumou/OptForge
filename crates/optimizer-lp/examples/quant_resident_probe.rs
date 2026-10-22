//! CPU-only admission and independent exact-guard witness transport.
use optimizer_lp::{Engine, LinearProgram, quant_resident::*};
use std::io::{self, BufRead};
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let a = std::env::args().skip(1).collect::<Vec<_>>();
    if a.len() != 3 {
        return Err("quant_resident_probe prepare|batch MODEL SETTINGS_JSON".into());
    }
    let model = optimizer_core::Model::from_json(&std::fs::read(&a[1])?)?;
    let p = LinearProgram::new(&model)?;
    let v: serde_json::Value = serde_json::from_str(&a[2])?;
    let settings: Settings = serde_json::from_value(v["settings"].clone())?;
    let layout: Layout = serde_json::from_value(
        v.get("layout")
            .cloned()
            .unwrap_or(serde_json::json!("segmented")),
    )?;
    let e = Engine::new(
        &p,
        optimizer_core::LpSettings::from_json(include_bytes!(
            "../../../examples/lp-settings-v1.json"
        ))?,
    );
    let op = Operator::new(&e, settings, layout)?;
    if a[0] == "prepare" {
        println!(
            "{}",
            serde_json::json!({"tiles":op.tiles.len(),"coefficients":op.values.len(),"bytes":op.preparation_bytes,"norm":op.norm,"step":op.step})
        );
        return Ok(());
    }
    println!(
        "{}",
        serde_json::json!({"values":op.values,"quantized":op.quantized,"low_error":op.low_error,"native_error":op.native_error,"row_of":op.row_of,"column_of":op.column_of,"tile_of":op.tile_of,"row_scale":op.row_scale,"column_scale":op.column_scale,"row_groups":op.row_groups.iter().map(|gs|gs.iter().map(|g|g.ids.clone()).collect::<Vec<_>>()).collect::<Vec<_>>(),"column_groups":op.column_groups.iter().map(|gs|gs.iter().map(|g|g.ids.clone()).collect::<Vec<_>>()).collect::<Vec<_>>()})
    );
    for line in io::stdin().lock().lines() {
        let v: serde_json::Value = serde_json::from_str(&line?)?;
        let t = v["transpose"].as_bool().ok_or("transpose")?;
        let vector: Vec<f64> = serde_json::from_value(v["vector"].clone())?;
        let mut promotion = Promotion::new(&op);
        if let Some(ids) = v.get("promote") {
            let ids: Vec<usize> = serde_json::from_value(ids.clone())?;
            promotion.promote(&op, &ids);
        }
        let g = op.generation(promotion)?;
        let product = op.product(&g, t, &vector)?;
        let old = op.base.bounds(g.promotion(), t, &vector);
        println!(
            "{}",
            serde_json::json!({"product":product.output,"bounds":product.bounds,"flags":product.flags,"counts":product.counts,"promotion":g.promotion(),"constants":g.constants().iter().map(|c|[c.alpha,c.beta,c.tiny]).collect::<Vec<_>>(),"old_bounds":old.as_ref().ok().map(|x|&x.0),"old_bad":old.as_ref().ok().map(|x|&x.1)})
        );
    }
    Ok(())
}
