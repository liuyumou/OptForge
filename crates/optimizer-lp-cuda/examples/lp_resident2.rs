//! SPEC-0024 explicit research driver; normal-limit vectors are exported faithfully.
use optimizer_core::{CancellationToken, LpDiagnostics, LpSettings, Model};
use optimizer_lp::LinearProgram;
use optimizer_lp_cuda::resident2::{self, Mode, PreparedModel, ResidentSession};
use serde_json::{Value, json};
use std::{
    error::Error,
    fs::{File, OpenOptions},
    io::{BufWriter, Write},
    path::Path,
    rc::Rc,
    time::{Duration, Instant},
};
fn ns(t: Instant) -> u64 {
    u64::try_from(t.elapsed().as_nanos()).unwrap_or(u64::MAX)
}
fn write(path: &Path, data: &Value) -> Result<(), Box<dyn Error>> {
    let mut out = BufWriter::new(OpenOptions::new().write(true).create_new(true).open(path)?);
    serde_json::to_writer(&mut out, data)?;
    out.write_all(b"\n")?;
    out.flush()?;
    out.get_ref().sync_all()?;
    Ok(())
}
fn main() -> Result<(), Box<dyn Error>> {
    let a: Vec<_> = std::env::args().collect();
    if a.len() != 8 {
        return Err("usage: lp_resident2 control|resident MODEL OUTPUT ITERATIONS SECONDS SOLVES fixed|solve".into());
    }
    if std::env::var("AI_OPTIMIZER_GPU_LEASE").as_deref() != Ok("inherited") {
        return Err("inherited GPU lease required".into());
    }
    let mode = match a[1].as_str() {
        "control" => Mode::Control,
        "resident" => Mode::Resident,
        _ => return Err("mode".into()),
    };
    let iterations: u64 = a[4].parse()?;
    let seconds: u64 = a[5].parse()?;
    let solves: usize = a[6].parse()?;
    if iterations == 0
        || iterations > 50000
        || seconds == 0
        || seconds > 60
        || !(1..=8).contains(&solves)
        || !matches!(a[7].as_str(), "fixed" | "solve")
    {
        return Err("bounded request refused".into());
    }
    let output = Path::new(&a[3]);
    std::fs::create_dir(output)?;
    let start = Instant::now();
    let phase = Instant::now();
    if std::fs::metadata(&a[2])?.len() > 128 << 20 {
        return Err("model input limit".into());
    }
    let raw = std::fs::read(&a[2])?;
    let model = Model::from_json(&raw)?;
    let original_sha = optimizer_core::sha256::hex(&raw);
    let program = LinearProgram::new(&model)?;
    let row_ids = model
        .document()
        .constraints
        .iter()
        .map(|r| r.id)
        .collect::<Vec<_>>();
    let variable_ids = program.variable_ids().to_vec();
    let conversion_ns = ns(phase);
    let phase = Instant::now();
    let prepared = PreparedModel::new(model, LpSettings::published(iterations, 200))?;
    let preparation_ns = ns(phase);
    let phase = Instant::now();
    let image = std::fs::read(resident2::code_object_path())?;
    let context = Rc::new(optimizer_cuda_sys::Context::create(&std::env::var(
        "CUDA_VISIBLE_DEVICES",
    )?)?);
    let mut setup = LpDiagnostics::new(true, false);
    setup.device_buffer_limit_bytes = Some(12 << 30);
    let session = ResidentSession::open(context, prepared, mode, &image, &mut setup)?;
    let import_ns = ns(phase);
    let mut rows = Vec::new();
    for i in 0..solves {
        let mut diagnostics = LpDiagnostics::new(true, false);
        let profile = optimizer_core::lp_cost::Session::begin()?;
        let phase = Instant::now();
        let result = session.solve(
            &CancellationToken::new(),
            &mut diagnostics,
            Some(phase + Duration::from_secs(seconds)),
            a[7] == "fixed",
        );
        let native_ns = ns(phase);
        let costs = profile.finish();
        let phase = Instant::now();
        let (x, y, updates, error) = match result {
            Ok((x, y, n)) => (Some(x), Some(y), Some(n), None),
            Err(e) => (None, None, None, Some(e.to_string())),
        };
        let stop = diagnostics
            .control
            .as_ref()
            .map(|c| c.stop.as_str())
            .unwrap_or("device_failure");
        let native_status = if error.is_some() {
            "numerical_failure"
        } else if stop == "accepted" {
            "optimal"
        } else {
            "limit"
        };
        let candidate = json!({"schema_version":1,"kind":"lp-baseline-candidate","model_sha256":original_sha,
            "row_ids":row_ids,"variable_ids":variable_ids,"primal":x,"dual":y,
            "transport":if error.is_some(){"error"}else{"completed"},"native_status":native_status});
        let bytes = serde_json::to_vec(&candidate)?;
        let export_ns = ns(phase);
        let phase = Instant::now();
        let candidate_path = output.join(format!("candidate-{i}.json"));
        let mut file = OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(candidate_path)?;
        file.write_all(&bytes)?;
        file.sync_all()?;
        let output_ns = ns(phase);
        rows.push(json!({"index":i,"native_ns":native_ns,"export_ns":export_ns,"output_ns":output_ns,
            "iterations":updates,"stop":stop,"error":error,"diagnostics":diagnostics,"native_costs":costs}));
    }
    drop(session);
    let envelope = json!({"schema_version":1,"kind":"lp-resident2-worker","mode":a[1],
        "lifecycle":if solves==1{"cold"}else{"prepared"},"solves":solves,"model_sha256":original_sha,
        "image_sha256":optimizer_core::sha256::hex(&image),"conversion_ns":conversion_ns,
        "preparation_ns":preparation_ns,"import_ns":import_ns,"setup":setup,"rows":rows,
        "worker_before_metadata_ns":ns(start)});
    write(&output.join("worker.json"), &envelope)?;
    File::open(output)?.sync_all()?;
    Ok(())
}
