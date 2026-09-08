//! Workspace CLI and original-model candidate validation. No solving is performed.

mod model;

use std::env;
use std::ffi::OsString;
use std::io::{self, Write};
use std::path::PathBuf;
use std::process::ExitCode;
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::thread;
use std::time::{Duration, Instant};

use optimizer_cuda::{DEFAULT_LOCK_PATH, GpuLease, discover};

const HELP: &str = "optimizer 0.1.0 (M1 model validation)
Usage:
  optimizer hello
  optimizer model validate --model <path>
    [--candidate <path> --absolute-tolerance <f64> --relative-tolerance <f64> --integrality-tolerance <f64>]
  optimizer gpu discover [--dry-run]
  optimizer gpu lease --simulate-ms <0..60000> [--timeout-ms <0..60000>]
  optimizer --help
  optimizer --version";

fn main() -> ExitCode {
    match run(env::args_os().skip(1).collect()) {
        Ok(code) => ExitCode::from(code),
        Err(error) => {
            eprintln!("optimizer: {error}");
            ExitCode::from(if error.kind() == io::ErrorKind::Interrupted {
                130
            } else {
                2
            })
        }
    }
}

fn run(args: Vec<OsString>) -> io::Result<u8> {
    if let [command, subcommand, options @ ..] = args.as_slice()
        && command == "model"
        && subcommand == "validate"
    {
        return model::validate(options);
    }
    let args: Vec<String> = args
        .into_iter()
        .map(|arg| {
            arg.into_string().map_err(|_| {
                io::Error::new(io::ErrorKind::InvalidInput, "argument: expected UTF-8 text")
            })
        })
        .collect::<io::Result<_>>()?;
    let words: Vec<&str> = args.iter().map(String::as_str).collect();
    match words.as_slice() {
        [] | ["--help"] | ["-h"] => println!("{HELP}"),
        ["--version"] => println!("optimizer {}", env!("CARGO_PKG_VERSION")),
        ["hello"] => println!("hello workspace"),
        ["gpu", "discover"] | ["gpu", "discover", "--dry-run"] => {
            println!("{}", serde_json::to_string_pretty(&discover())?);
        }
        ["gpu", "lease", options @ ..] => simulate_lease(options)?,
        _ => {
            return Err(io::Error::new(
                io::ErrorKind::InvalidInput,
                format!("argument: invalid command\n{HELP}"),
            ));
        }
    }
    Ok(0)
}

fn simulate_lease(options: &[&str]) -> io::Result<()> {
    let invalid = || io::Error::new(io::ErrorKind::InvalidInput, HELP);
    let mut hold = None;
    let mut timeout = None;
    for pair in options.chunks(2) {
        let [key, value] = pair else {
            return Err(invalid());
        };
        let value = value
            .parse::<u64>()
            .ok()
            .filter(|value| *value <= 60_000)
            .ok_or_else(invalid)?;
        let slot = match *key {
            "--simulate-ms" => &mut hold,
            "--timeout-ms" => &mut timeout,
            _ => return Err(invalid()),
        };
        if slot.replace(value).is_some() {
            return Err(invalid());
        }
    }
    let hold = Duration::from_millis(hold.ok_or_else(invalid)?);
    let timeout = Duration::from_millis(timeout.unwrap_or(5_000));
    let cancelled = Arc::new(AtomicBool::new(false));
    let signal = Arc::clone(&cancelled);
    ctrlc::set_handler(move || signal.store(true, Ordering::SeqCst)).map_err(io::Error::other)?;
    let path = env::var_os("AI_OPTIMIZER_GPU_LOCK")
        .map_or_else(|| PathBuf::from(DEFAULT_LOCK_PATH), PathBuf::from);
    writeln!(io::stdout(), "{{\"event\":\"waiting\",\"simulated\":true}}")?;
    io::stdout().flush()?;
    let lease = GpuLease::acquire(&path, timeout, &cancelled)?;
    writeln!(
        io::stdout(),
        "{{\"event\":\"acquired\",\"simulated\":true}}"
    )?;
    io::stdout().flush()?;
    let start = Instant::now();
    while start.elapsed() < hold && !cancelled.load(Ordering::SeqCst) {
        thread::sleep(Duration::from_millis(10));
    }
    drop(lease);
    writeln!(
        io::stdout(),
        "{{\"event\":\"released\",\"simulated\":true}}"
    )?;
    if cancelled.load(Ordering::SeqCst) {
        return Err(io::Error::new(
            io::ErrorKind::Interrupted,
            "GPU lease cancelled",
        ));
    }
    Ok(())
}
