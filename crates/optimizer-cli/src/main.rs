//! Workspace CLI and original-model candidate validation. No solving is performed.

mod input;
mod model;
mod provenance;
mod registry;
mod schedule;
mod search;
mod solve;

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

const HELP: &str = "optimizer 0.1.0 (C8 local extension registry)
Usage:
  optimizer hello
  optimizer model validate --model <path>
    [--candidate <path> --absolute-tolerance <f64> --relative-tolerance <f64> --integrality-tolerance <f64>]
  optimizer solve --model <path> --config <path> [--candidate <path> | --basis <path>]
    [--backend highs|host-lp] [--lp-settings <path>]
  optimizer search --model <path> --config <path> [--output <path>] [REGISTRY]
  optimizer verify --record <path> --model <path> [--instance <path>] [REGISTRY]
  optimizer schedule generate --instance-id <text> --seed <u32> --jobs <n> --machines <m> [--output <path>]
  optimizer schedule solve --instance <path> --config <path> [--output <path>] [--output-model <path>] [REGISTRY]
  optimizer registry list --registry <path>
  optimizer registry check --registry <path> --extension <id> [--instance <path>] [--output <path>]
  optimizer gpu discover [--dry-run]
  optimizer gpu lease --simulate-ms <0..60000> [--timeout-ms <0..60000>]
  optimizer gpu probe --device GPU-<uuid> [--lease acquire|inherited] [--timeout-ms <0..60000>]
  optimizer --help
  optimizer --version

REGISTRY is [--registry <path>] [--allow-experimental]. A configuration naming an
extension requires --registry; there is deliberately no default registry location,
so a run's extensions depend on the command rather than on the filesystem.";

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
    // Path-bearing commands are dispatched before any UTF-8 conversion so
    // native filenames keep their OS representation.
    match args.as_slice() {
        [command, subcommand, options @ ..] if command == "model" && subcommand == "validate" => {
            return model::validate(options);
        }
        [command, options @ ..] if command == "solve" => {
            return solve::solve(options);
        }
        [command, options @ ..] if command == "search" => {
            return search::search(options);
        }
        [command, options @ ..] if command == "verify" => {
            return search::verify(options);
        }
        [command, subcommand, options @ ..]
            if command == "schedule" && subcommand == "generate" =>
        {
            return schedule::generate(options);
        }
        [command, subcommand, options @ ..] if command == "schedule" && subcommand == "solve" => {
            return schedule::solve(options);
        }
        [command, subcommand, options @ ..] if command == "registry" && subcommand == "list" => {
            return registry::list(options);
        }
        [command, subcommand, options @ ..] if command == "registry" && subcommand == "check" => {
            return registry::check(options);
        }
        _ => {}
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
        ["gpu", "probe", options @ ..] => probe_device(options)?,
        _ => {
            return Err(io::Error::new(
                io::ErrorKind::InvalidInput,
                format!("argument: invalid command\n{HELP}"),
            ));
        }
    }
    Ok(0)
}

/// Probe one device, under SPEC-0010 requirements 3, 4 and 9.
///
/// Unlike `gpu discover`, which asks management tooling and never touches the
/// driver, this creates a context and therefore takes the host lease. That is why
/// it names exactly one UUID: the lease permits one holder across device
/// selections, so probing "everything" would be a command the lease forbids.
fn probe_device(options: &[&str]) -> io::Result<()> {
    let invalid = || io::Error::new(io::ErrorKind::InvalidInput, HELP);
    let mut device = None;
    let mut lease = None;
    let mut timeout = None;
    for pair in options.chunks(2) {
        let [key, value] = pair else {
            return Err(invalid());
        };
        // Each flag is stored once. A repeated flag is an error rather than a
        // last-one-wins, matching every other command here, because a caller who
        // passed two devices did not mean either of them.
        match *key {
            "--device" => {
                if device.replace((*value).to_string()).is_some() {
                    return Err(invalid());
                }
            }
            "--lease" => {
                let mode = match *value {
                    "acquire" | "inherited" => (*value).to_string(),
                    _ => return Err(invalid()),
                };
                if lease.replace(mode).is_some() {
                    return Err(invalid());
                }
            }
            "--timeout-ms" => {
                let parsed = value
                    .parse::<u64>()
                    .ok()
                    .filter(|value| *value <= 60_000)
                    .ok_or_else(invalid)?;
                if timeout.replace(parsed).is_some() {
                    return Err(invalid());
                }
            }
            _ => return Err(invalid()),
        }
    }
    let device = device.ok_or_else(invalid)?;

    // The lease decision is passed as an argument rather than through the
    // environment. Setting a variable here would need unsafe under edition 2024,
    // which this crate forbids, and the prohibition is right: a command that
    // mutates its own environment to reach a library is harder to follow than one
    // that says what it wants.
    let request = match lease.as_deref() {
        None => optimizer_cuda::probe::LeaseRequest::Auto,
        Some("acquire") => optimizer_cuda::probe::LeaseRequest::Acquire,
        Some("inherited") => optimizer_cuda::probe::LeaseRequest::Inherited,
        Some(_) => return Err(invalid()),
    };

    let path = env::var_os("AI_OPTIMIZER_GPU_LOCK")
        .map_or_else(|| PathBuf::from(DEFAULT_LOCK_PATH), PathBuf::from);
    let timeout = Duration::from_millis(timeout.unwrap_or(5_000));
    match optimizer_cuda::probe::probe(&device, &path, timeout, request) {
        Ok(report) => {
            println!("{}", serde_json::to_string_pretty(&report)?);
            Ok(())
        }
        // Every refusal is exit 2 and writes no report. A probe that printed a
        // partial report on failure would be read as a successful one.
        Err(error) => Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            error.to_string(),
        )),
    }
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
