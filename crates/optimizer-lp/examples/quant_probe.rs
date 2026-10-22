//! CPU-only quantization admission and oracle bridge.
use optimizer_lp::{
    Engine, LinearProgram,
    quant::{Format, Operator, Promotion, Settings},
};
use std::io::{self, BufRead};
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let a = std::env::args().skip(1).collect::<Vec<_>>();
    if a.first().map(String::as_str) == Some("codec") {
        for l in io::stdin().lock().lines() {
            let v: serde_json::Value = serde_json::from_str(&l?)?;
            let f: Format = serde_json::from_value(v["format"].clone())?;
            let x = f64::from_bits(v["bits"].as_u64().ok_or("bits")?);
            println!(
                "{}",
                serde_json::json!({"code":f.encode(x).ok(),"decoded_bits":v["code"].as_u64().and_then(|c|u16::try_from(c).ok()).and_then(|c|f.decode(c).ok()).map(f64::to_bits)})
            );
        }
        return Ok(());
    }
    if a.len() != 3 {
        return Err("quant_probe prepare|product MODEL SETTINGS_JSON".into());
    }
    let m = optimizer_core::Model::from_json(&std::fs::read(&a[1])?)?;
    let p = LinearProgram::new(&m)?;
    let v: serde_json::Value = serde_json::from_str(&a[2])?;
    let settings: Settings = serde_json::from_value(v["settings"].clone())?;
    let mut engine = Engine::new(
        &p,
        optimizer_core::LpSettings::from_json(include_bytes!(
            "../../../examples/lp-settings-v1.json"
        ))?,
    );
    let op = Operator::new(&engine, settings)?;
    engine.restrict_step(op.step)?;
    let promotion = Promotion::new(&op);
    if a[0] == "prepare" {
        println!(
            "{}",
            serde_json::json!({"tiles":op.tiles.len(),"forced_tiles":op.tiles.iter().filter(|t|t.forced).count(),"promotion":promotion,"norm":op.norm,"step":op.step,"bytes":op.preparation_bytes,"coefficients":op.values.len()})
        );
    } else {
        let vector: Vec<f64> = serde_json::from_value(v["vector"].clone())?;
        let t = v["transpose"].as_bool().ok_or("transpose")?;
        let b = op.bounds(&promotion, t, &vector);
        println!(
            "{}",
            serde_json::json!({"product":op.product(&promotion,t,&vector).ok(),"bounds":b.as_ref().ok().map(|x|&x.0),"bad":b.as_ref().ok().map(|x|&x.1),"error":b.err(),"row_scale":op.row_scale,"column_scale":op.column_scale})
        );
    }
    Ok(())
}
