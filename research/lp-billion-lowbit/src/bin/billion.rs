use lp_billion_lowbit::{
    Result,
    array_assessment::Assessor,
    array_input::{Array, Original, Store},
    fast_device,
    solve::Settings,
    tensor::Config,
};
use serde_json::{Value, json};
use std::{
    io::{self, BufRead, Write},
    path::Path,
    time::Instant,
};
fn run() -> Result<()> {
    let a: Vec<_> = std::env::args().collect();
    if a.len() < 4 {
        return Err(
            "usage: billion convert|inspect|assess|solve|prepare-check MODEL STORE [CUBIN]".into(),
        );
    }
    let started = Instant::now();
    let store = Store::new(Path::new(&a[3]))?;
    if a[1] == "convert" {
        let (model, _) = lp_billion_lowbit::input::load(Path::new(&a[2]))?;
        println!(
            "{}",
            serde_json::to_string(&Original::convert(&model, &store)?)?
        );
        return Ok(());
    }
    let original = Original::load(Path::new(&a[2]), &store)?;
    let input_ns = started.elapsed().as_nanos();
    if a[1] == "inspect" {
        println!(
            "{}",
            json!({"model_sha256":original.sha256,"matrix_sha256":original.program.matrix_sha256(),
            "rows":original.program.row_count(),"columns":original.program.column_count(),
            "nonzeros":original.program.nonzeros(),"input_ns":input_ns})
        );
        return Ok(());
    }
    let mut assessor = Assessor::new(&original, &store, false);
    for line in io::stdin().lock().lines() {
        let line = line?;
        if line.len() > 16 << 20 {
            return Err("request byte limit".into());
        }
        let r: Value = serde_json::from_str(&line)?;
        let settings: Settings = serde_json::from_value(r["settings"].clone())?;
        settings.validate()?;
        let mut result = if a[1] == "prepare-check" && a.len() == 5 {
            let lp = if let Some(value) = r.get("lp_settings") {
                serde_json::from_value(value.clone())?
            } else {
                settings.lp()
            };
            lp.validate()?;
            lp_billion_lowbit::gpu_prepare::check(&original.program, lp, Path::new(&a[4]))?
        } else if a[1] == "assess" {
            let x: Array = serde_json::from_value(r["endpoint"]["primal"].clone())?;
            let y: Array = serde_json::from_value(r["endpoint"]["dual"].clone())?;
            let x = store.read(&x, original.program.column_count())?;
            let y = store.read(&y, original.program.row_count())?;
            assessor.evaluate(&x, &y, settings.tolerance, false)?
        } else if a[1] == "solve" && a.len() == 5 {
            let mut t: Config =
                serde_json::from_value(r.get("tensor").cloned().unwrap_or(json!({})))?;
            if settings.format.components() > 0 {
                t.components = settings.format.components();
            }
            let f: fast_device::Config =
                serde_json::from_value(r.get("fast").cloned().unwrap_or(json!({})))?;
            lp_billion_lowbit::billion::solve(
                &original,
                &store,
                &settings,
                Path::new(&a[4]),
                &t,
                &f,
            )?
        } else {
            return Err("command domain".into());
        };
        result["model_sha256"] = json!(original.sha256);
        result["input_ns"] = json!(input_ns);
        println!("{}", serde_json::to_string(&result)?);
        io::stdout().flush()?;
    }
    Ok(())
}
fn main() {
    if let Err(e) = run() {
        eprintln!("{e}");
        std::process::exit(2);
    }
}
