//! Process-level acceptance tests for SPEC-0000 and SPEC-0006.

use std::io::{BufRead, BufReader};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::mpsc::{self, Receiver};
use std::thread;
use std::time::{Duration, Instant};

static NEXT: AtomicUsize = AtomicUsize::new(0);

struct Job(Child, Receiver<String>);

impl Job {
    fn spawn(command: &mut Command) -> Self {
        let mut child = command.stdout(Stdio::piped()).spawn().unwrap();
        let output = child.stdout.take().unwrap();
        let (sender, receiver) = mpsc::channel();
        thread::spawn(move || {
            for line in BufReader::new(output).lines() {
                let _ = sender.send(line.unwrap());
            }
        });
        Self(child, receiver)
    }

    fn event(&self, expected: &str) {
        let start = Instant::now();
        loop {
            let remaining = Duration::from_secs(5)
                .checked_sub(start.elapsed())
                .expect("event deadline");
            let line = self.1.recv_timeout(remaining).expect("child event missing");
            let event: serde_json::Value = serde_json::from_str(&line).unwrap();
            if event["event"] == expected {
                return;
            }
        }
    }
}

impl Drop for Job {
    fn drop(&mut self) {
        let _ = self.0.kill();
        let _ = self.0.wait();
    }
}

struct Sandbox(PathBuf);

impl Sandbox {
    fn new() -> Self {
        let path = std::env::temp_dir().join(format!(
            "optimizer-test-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::SeqCst)
        ));
        std::fs::create_dir(&path).unwrap();
        Self(path)
    }

    fn command(&self) -> Command {
        let mut command = Command::new(env!("CARGO_BIN_EXE_optimizer"));
        command.env("AI_OPTIMIZER_GPU_LOCK", self.0.join("gpu.lock"));
        command
    }

    fn holder(&self) -> Job {
        let job = Job::spawn(
            self.command()
                .args(["gpu", "lease", "--simulate-ms", "60000"]),
        );
        job.event("acquired");
        job
    }
}

impl Drop for Sandbox {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

fn wait(job: &mut Job) -> std::process::ExitStatus {
    let start = Instant::now();
    loop {
        if let Some(status) = job.0.try_wait().unwrap() {
            return status;
        }
        assert!(
            start.elapsed() < Duration::from_secs(5),
            "child exceeded test deadline"
        );
        thread::sleep(Duration::from_millis(10));
    }
}

fn signal(job: &Job, name: &str) {
    assert!(
        Command::new("kill")
            .args([name, &job.0.id().to_string()])
            .status()
            .unwrap()
            .success()
    );
}

#[test]
fn hello_and_invalid_arguments_follow_cli_contract() {
    let sandbox = Sandbox::new();
    let output = sandbox.command().arg("hello").output().unwrap();
    assert!(output.status.success());
    assert_eq!(output.stdout, b"hello workspace\n");
    for args in [
        // `solve` now exists, so this is a missing-argument error rather than
        // an unknown command; both are categorized argument failures.
        vec!["solve"],
        vec!["solve", "--model", "examples/model-v1.json"],
        vec!["gpu", "lease"],
        vec!["gpu", "lease", "--simulate-ms", "60001"],
        vec!["gpu", "lease", "--simulate-ms", "0", "--simulate-ms", "1"],
        // A probe names exactly one device, because the host lease permits one
        // holder across device selections; omitting it or naming two are both
        // requests the lease could not satisfy.
        vec!["gpu", "probe"],
        vec!["gpu", "probe", "--device"],
        vec!["gpu", "probe", "--device", "GPU-a", "--device", "GPU-b"],
        vec!["gpu", "probe", "--device", "GPU-a", "--lease", "maybe"],
        vec!["gpu", "probe", "--device", "GPU-a", "--timeout-ms", "60001"],
        vec!["gpu", "probe", "--device", "GPU-a", "--unknown", "1"],
    ] {
        assert_eq!(
            sandbox.command().args(args).output().unwrap().status.code(),
            Some(2)
        );
    }
}

#[test]
fn absent_management_tool_is_explicitly_unavailable() {
    let sandbox = Sandbox::new();
    let output = sandbox
        .command()
        .env("PATH", &sandbox.0)
        .args(["gpu", "discover", "--dry-run"])
        .output()
        .unwrap();
    assert!(output.status.success());
    let record: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(record["status"], "unavailable");
    assert!(record["reason"].as_str().unwrap().contains("nvidia-smi"));
}

/// SPEC-0010 requirements 3 and 4: a probe without a driver refuses and says so.
///
/// This runs on any host, including one with no device at all, which is the case it
/// is about: the refusal must name what was missing rather than report an empty
/// success. A probe that printed a partial report when it could not reach a driver
/// would be read as one that reached it.
#[test]
fn a_probe_without_management_tooling_refuses_and_writes_no_report() {
    let sandbox = Sandbox::new();
    let output = sandbox
        .command()
        .env("PATH", &sandbox.0)
        .args([
            "gpu",
            "probe",
            "--device",
            "GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48",
        ])
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(2));
    assert!(output.stdout.is_empty(), "a refusal writes no report");
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        stderr.contains("nvidia-smi") || stderr.contains("driver"),
        "the refusal must name what was missing: {stderr}"
    );
}

/// Requirement 8: a probe under the wrapper does not block on the lock its parent
/// holds, and asking it to is bounded rather than a hang.
///
/// `--lease acquire` inside an inherited lease is the deadlock requirement 8 exists
/// to prevent, expressed deliberately. It must time out and refuse, not wait for the
/// wrapper's 300 seconds, so the mistake is visible in a test run rather than in a
/// stuck CI job.
#[test]
fn acquiring_inside_an_inherited_lease_times_out_rather_than_hanging() {
    let sandbox = Sandbox::new();
    let holder = sandbox.holder();
    let started = std::time::Instant::now();
    let output = sandbox
        .command()
        .args([
            "gpu",
            "probe",
            "--device",
            "GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48",
            "--lease",
            "acquire",
            "--timeout-ms",
            "300",
        ])
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(2));
    assert!(
        started.elapsed() < std::time::Duration::from_secs(30),
        "the wait must be bounded by the timeout, not by the wrapper's"
    );
    assert!(
        String::from_utf8_lossy(&output.stderr).contains("lease"),
        "the refusal must name the lease"
    );
    signal(&holder, "-TERM");
}

/// Requirement 9: asserting an inherited lease does not take the lock.
///
/// The assertion is a caller's, and a caller that makes it wrongly gets an unleased
/// run. That is why the wrapper is the thing that normally makes it and why the flag
/// exists at all: without it, a wrapped child would block on its own parent.
#[test]
fn an_asserted_inherited_lease_does_not_wait_for_the_lock() {
    let sandbox = Sandbox::new();
    let holder = sandbox.holder();
    let output = sandbox
        .command()
        .env("PATH", &sandbox.0)
        .args([
            "gpu",
            "probe",
            "--device",
            "GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48",
            "--lease",
            "inherited",
        ])
        .output()
        .unwrap();
    // It still refuses, because this sandbox has no management tooling on PATH.
    // What matters is which refusal: it reached discovery rather than blocking on
    // a lock another process holds.
    assert_eq!(output.status.code(), Some(2));
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        !stderr.contains("lease"),
        "an asserted inherited lease must not wait for the lock: {stderr}"
    );
    signal(&holder, "-TERM");
}

#[test]
fn exclusive_lease_times_out_and_serializes_waiters() {
    let sandbox = Sandbox::new();
    let mut holder = sandbox.holder();
    let output = sandbox
        .command()
        .args(["gpu", "lease", "--simulate-ms", "0", "--timeout-ms", "30"])
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&output.stderr).contains("timed out"));
    let mut waiter = Job::spawn(sandbox.command().args([
        "gpu",
        "lease",
        "--simulate-ms",
        "0",
        "--timeout-ms",
        "4000",
    ]));
    waiter.event("waiting");
    assert!(waiter.0.try_wait().unwrap().is_none());
    signal(&holder, "-TERM");
    assert_eq!(wait(&mut holder).code(), Some(130));
    assert!(wait(&mut waiter).success());
}

#[test]
fn normal_exit_and_process_death_release_the_same_lock_inode() {
    let sandbox = Sandbox::new();
    for _ in 0..2 {
        assert!(
            sandbox
                .command()
                .args(["gpu", "lease", "--simulate-ms", "0", "--timeout-ms", "0"])
                .output()
                .unwrap()
                .status
                .success()
        );
    }
    let mut holder = sandbox.holder();
    signal(&holder, "-KILL");
    assert!(!wait(&mut holder).success());
    assert!(
        sandbox
            .command()
            .args(["gpu", "lease", "--simulate-ms", "0", "--timeout-ms", "0"])
            .output()
            .unwrap()
            .status
            .success()
    );
}

#[test]
fn cancellation_while_waiting_does_not_release_another_jobs_lease() {
    let sandbox = Sandbox::new();
    let _holder = sandbox.holder();
    let mut waiter = Job::spawn(sandbox.command().args([
        "gpu",
        "lease",
        "--simulate-ms",
        "0",
        "--timeout-ms",
        "4000",
    ]));
    waiter.event("waiting");
    signal(&waiter, "-INT");
    assert_eq!(wait(&mut waiter).code(), Some(130));
    assert_eq!(
        sandbox
            .command()
            .args(["gpu", "lease", "--simulate-ms", "0", "--timeout-ms", "0"])
            .output()
            .unwrap()
            .status
            .code(),
        Some(2)
    );
}

#[test]
fn shell_runner_and_rust_use_the_same_host_lock() {
    let sandbox = Sandbox::new();
    let mut holder = sandbox.holder();
    let path = sandbox.0.join("gpu.lock");
    assert_eq!(
        Command::new("flock")
            .arg("--nonblock")
            .arg(&path)
            .arg("true")
            .status()
            .unwrap()
            .code(),
        Some(1)
    );
    signal(&holder, "-TERM");
    assert_eq!(wait(&mut holder).code(), Some(130));
    assert!(
        Command::new("flock")
            .arg("--nonblock")
            .arg(&path)
            .arg("true")
            .status()
            .unwrap()
            .success()
    );
}
