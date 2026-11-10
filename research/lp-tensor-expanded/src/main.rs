//! CPU-only arithmetic adapter. Solver commands are added after model admission.
use lp_tensor_expanded_research::value::Value;
use std::io::{self, BufRead};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    for line in io::stdin().lock().lines() {
        let line = line?;
        let raw: serde_json::Value = serde_json::from_str(&line)?;
        let operation = raw["operation"].as_str().ok_or("operation missing")?;
        let output = match operation {
            "fma" => {
                let v: Vec<Value> = serde_json::from_value(raw["values"].clone())?;
                if v.len() != 3 { return Err("operand count".into()); }
                for x in &v { x.validate()?; }
                match v[0].fma(v[1],v[2]) {
                    Ok(x) => serde_json::json!({"value":x}),
                    Err(e) => serde_json::json!({"error":e}),
                }
            }
            "encode" => {
                let bits = raw["bits"].as_u64().ok_or("bits missing")?;
                match Value::from_f64(f64::from_bits(bits)) {
                    Ok(x) => serde_json::json!({"value":x}),
                    Err(e) => serde_json::json!({"error":e}),
                }
            }
            "decode" => {
                let x: Value = serde_json::from_value(raw["value"].clone())?;
                x.validate()?;
                match x.to_f64() {
                    Ok(x) => serde_json::json!({"bits":x.to_bits()}),
                    Err(e) => serde_json::json!({"error":e}),
                }
            }
            "pack" => {
                let x: Value = serde_json::from_value(raw["value"].clone())?;
                x.validate()?;
                let e = i32::try_from(raw["exponent"].as_i64().ok_or("exponent missing")?)?;
                match x.pack(e) {
                    Ok((q,r)) => serde_json::json!({"magnitude":q,"residual":r}),
                    Err(e) => serde_json::json!({"error":e}),
                }
            }
            _ => return Err("unknown arithmetic operation".into()),
        };
        println!("{output}");
    }
    Ok(())
}
