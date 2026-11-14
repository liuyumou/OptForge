//! Delivery-only pipe batching and eager independent-checker startup.
//! Endpoint serialization and every assessment still use the retained checker.
use crate::identity::hex;
use crate::{Result, checker, checker::Endpoint, config};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::{
    fs,
    io::{self, BufRead, BufReader, Read, Write},
    path::Path,
    process::{Child, ChildStdin, ChildStdout, Command, Stdio},
    time::{Duration, Instant},
};
const FRAME_LIMIT: u64 = 8 << 20;

pub fn control() -> bool {
    !config::get().batch
}

// Read at most the admitted frame plus one byte; never allocate an unbounded
// line before checking its length. A partial final line is a transport failure.
fn frame(input: &mut impl BufRead) -> Result<Option<Vec<u8>>> {
    let mut bytes = Vec::new();
    let n = input.take(FRAME_LIMIT + 1).read_until(b'\n', &mut bytes)?;
    if n == 0 {
        return Ok(None);
    }
    if n as u64 > FRAME_LIMIT || bytes.last() != Some(&b'\n') {
        return Err("checker frame limit or truncated frame".into());
    }
    Ok(Some(bytes))
}

fn send(output: &mut impl Write, value: &impl Serialize, baseline: bool) -> Result<()> {
    if baseline {
        serde_json::to_writer(&mut *output, value)?;
        output.write_all(b"\n")?;
    } else {
        let mut bytes = serde_json::to_vec(value)?;
        bytes.push(b'\n');
        if bytes.len() as u64 > FRAME_LIMIT {
            return Err("checker outgoing frame limit".into());
        }
        output.write_all(&bytes)?;
    }
    output.flush()?;
    Ok(())
}

pub struct Independent {
    child: Child,
    input: Option<ChildStdin>,
    output: BufReader<ChildStdout>,
    pub binary: String,
    baseline: bool,
    failed: bool,
    started: Instant,
    ready_ns: u128,
    profiles: Vec<Value>,
}
impl Independent {
    // The owned guard exists before readiness: setup failures still close/reap
    // the checker, including failures in subsequent CUDA initialization.
    pub fn spawn(path: &Path) -> Result<Self> {
        let started = Instant::now();
        let mut child = Command::new(std::env::current_exe()?)
            .arg("check-service")
            .arg(path)
            .env("CUDA_VISIBLE_DEVICES", "")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::inherit())
            .spawn()?;
        let input = child.stdin.take();
        let output = BufReader::new(child.stdout.take().ok_or("checker stdout")?);
        Ok(Self {
            child,
            input,
            output,
            binary: String::new(),
            baseline: control(),
            failed: false,
            started,
            ready_ns: 0,
            profiles: Vec::new(),
        })
    }
    pub fn ready(&mut self, model_hash: &str) -> Result<()> {
        let ready = self.read()?;
        if ready["ready"] != true || ready["model_sha256"] != model_hash {
            return Err("checker model binding".into());
        }
        self.binary = ready["checker_binary_sha256"]
            .as_str()
            .ok_or("checker image")?
            .into();
        if self.binary.len() != 64 || !self.binary.bytes().all(|b| b.is_ascii_hexdigit()) {
            return Err("checker image digest".into());
        }
        self.ready_ns = self.started.elapsed().as_nanos();
        Ok(())
    }
    pub fn ready_elapsed_ns(&self) -> u128 {
        self.ready_ns
    }
    pub fn take_profile(&mut self) -> Vec<Value> {
        std::mem::take(&mut self.profiles)
    }
    fn read(&mut self) -> Result<Value> {
        let bytes = frame(&mut self.output)?.ok_or("checker ended")?;
        Ok(serde_json::from_slice(&bytes)?)
    }
    pub fn assess(&mut self, endpoint: &Endpoint, tier: &str) -> Result<Value> {
        if self.failed || self.binary.is_empty() {
            return Err("checker unavailable".into());
        }
        // Poison the connection until a fully bound response arrives; a partial
        // write or stale response can never become a later successful request.
        self.failed = true;
        let started = config::get().profile.then(Instant::now);
        let input = self.input.as_mut().ok_or("closed checker")?;
        if self.baseline {
            send(input, &json!({"endpoint":endpoint,"tier":tier}), true)?;
        } else {
            #[derive(Serialize)]
            struct Request<'a> {
                endpoint: &'a Endpoint,
                tier: &'a str,
            }
            send(input, &Request { endpoint, tier }, false)?;
        }
        let sent_ns = started.map(|s| s.elapsed().as_nanos());
        let bytes = frame(&mut self.output)?.ok_or("checker ended")?;
        let read_ns = started.map(|s| s.elapsed().as_nanos());
        let result: Value = serde_json::from_slice(&bytes)?;
        let decoded_ns = started.map(|s| s.elapsed().as_nanos());
        if result["model_sha256"] != endpoint.model_sha256
            || result["endpoint_sha256"] != hex(&serde_json::to_vec(endpoint)?)
            || result["tier"] != tier
            || result["checker_binary_sha256"] != self.binary
        {
            return Err("checker receipt binding".into());
        }
        if let Some(started) = started {
            self.profiles
                .push(json!({"request_build_encode_write_flush_ns":sent_ns,
                "response_wait_read_end_ns":read_ns,"response_decode_end_ns":decoded_ns,
                "binding_end_ns":started.elapsed().as_nanos(),"response_bytes":bytes.len(),
                "batched":!self.baseline}));
        }
        self.failed = false;
        Ok(result)
    }
}
impl Drop for Independent {
    fn drop(&mut self) {
        let _scope = optimizer_core::lp_cost::scope("checker_eof_reap");
        self.input.take();
        for _ in 0..100 {
            if self.child.try_wait().ok().flatten().is_some() {
                return;
            }
            std::thread::sleep(Duration::from_millis(2));
        }
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct CheckRequest {
    endpoint: Endpoint,
    tier: String,
}

pub fn check_service(path: &Path) -> Result<()> {
    let started = config::get().profile.then(Instant::now);
    let mut bytes = Vec::new();
    fs::File::open(path)?
        .take((128 << 20) + 1)
        .read_to_end(&mut bytes)?;
    if bytes.len() > 128 << 20 {
        return Err("checker model limit".into());
    }
    let read_ns = started.map(|s| s.elapsed().as_nanos());
    let checker = checker::Checker::new(&bytes)?;
    let prepared_ns = started.map(|s| s.elapsed().as_nanos());
    let original = std::env::var_os("GPUP_CHECKER_ORIGINAL").is_some();
    let binary = hex(&fs::read(std::env::current_exe()?)?);
    let mut output = io::stdout().lock();
    send(
        &mut output,
        &json!({"ready":true,"model_sha256":hex(&bytes),"checker_binary_sha256":binary}),
        control(),
    )?;
    if let Some(started) = started {
        eprintln!(
            "{}",
            json!({"delivery4_checker_setup":{"read_ns":read_ns,"prepared_ns":prepared_ns,
            "ready_ns":started.elapsed().as_nanos()}})
        );
    }
    let mut serial = 0_u64;
    let mut input = io::stdin().lock();
    while let Some(bytes) = frame(&mut input)? {
        let started = config::get().profile.then(Instant::now);
        let request: CheckRequest = serde_json::from_slice(&bytes)?;
        let decoded_ns = started.map(|s| s.elapsed().as_nanos());
        let mut result = checker.assess_mode(&request.endpoint, &request.tier, original)?;
        let assessed_ns = started.map(|s| s.elapsed().as_nanos());
        result["checker_binary_sha256"] = json!(binary);
        send(&mut output, &result, control())?;
        if let Some(started) = started {
            eprintln!(
                "{}",
                json!({"delivery4_checker_assessment":{"serial":serial,
                "decode_ns":decoded_ns,"assessed_ns":assessed_ns,"sent_ns":started.elapsed().as_nanos(),
                "request_bytes":bytes.len(),"batched":!control()}})
            );
        }
        serial += 1;
    }
    Ok(())
}

/// CPU-only end-to-end IPC microprofile; no device or solve is created.
pub fn profile(args: &[String]) -> Result<()> {
    use std::time::Instant;
    if args.len() != 7 {
        return Err("transport-profile MODEL ENDPOINT TIER COUNT OUTPUT".into());
    }
    let endpoint: Endpoint = serde_json::from_slice(&fs::read(&args[3])?)?;
    let count: usize = args[5].parse()?;
    if !(1..=1000).contains(&count) {
        return Err("profile count".into());
    }
    let started = Instant::now();
    let mut child = Independent::spawn(Path::new(&args[2]))?;
    child.ready(&endpoint.model_sha256)?;
    let setup_ns = started.elapsed().as_nanos();
    let mut rows = Vec::new();
    for _ in 0..count {
        let before = Instant::now();
        let certificate = child.assess(&endpoint, &args[4])?;
        rows.push(json!({"ns":before.elapsed().as_nanos(),"certificate":certificate}));
    }
    let before = Instant::now();
    drop(child);
    let value = json!({"setup_ns":setup_ns,"teardown_ns":before.elapsed().as_nanos(),"rows":rows});
    let mut file = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&args[6])?;
    file.write_all(&serde_json::to_vec(&value)?)?;
    file.sync_all()?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[derive(Default)]
    struct Writer {
        bytes: Vec<u8>,
        writes: usize,
    }
    impl Write for Writer {
        fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
            self.writes += 1;
            self.bytes.extend_from_slice(bytes);
            Ok(bytes.len())
        }
        fn flush(&mut self) -> io::Result<()> {
            Ok(())
        }
    }
    #[test]
    fn batches_exact_bytes_with_signed_zero_and_extremes() {
        let e = Endpoint {
            model_sha256: "a".repeat(64),
            primal: vec![-0.0, 0.0, f64::MAX, f64::MIN_POSITIVE, f64::from_bits(1)],
            dual: vec![1.0; 1024],
            transport: "completed".into(),
        };
        let request = json!({"endpoint":e,"tier":"certified-1e-9"});
        let mut old = Writer::default();
        let mut new = Writer::default();
        send(&mut old, &request, true).unwrap();
        send(&mut new, &request, false).unwrap();
        assert_eq!(old.bytes, new.bytes);
        assert_eq!(new.writes, 1);
        assert!(old.writes > 1000);
        let decoded: CheckRequest = serde_json::from_slice(&new.bytes).unwrap();
        assert_eq!(
            decoded
                .endpoint
                .primal
                .iter()
                .map(|x| x.to_bits())
                .collect::<Vec<_>>(),
            e.primal.iter().map(|x| x.to_bits()).collect::<Vec<_>>()
        );
    }
    #[test]
    fn bounded_frames_distinguish_eof_from_truncation() {
        let mut input = io::Cursor::new(b"{}\n{}\n");
        assert_eq!(frame(&mut input).unwrap().unwrap(), b"{}\n");
        assert_eq!(frame(&mut input).unwrap().unwrap(), b"{}\n");
        assert!(frame(&mut input).unwrap().is_none());
        assert!(frame(&mut io::Cursor::new(b"{}")).is_err());
        let mut over = io::Cursor::new(vec![b'x'; FRAME_LIMIT as usize + 20]);
        assert!(frame(&mut over).is_err());
        assert_eq!(over.position(), FRAME_LIMIT + 1);
        let mut exact = vec![b' '; FRAME_LIMIT as usize];
        *exact.last_mut().unwrap() = b'\n';
        assert_eq!(
            frame(&mut io::Cursor::new(exact)).unwrap().unwrap().len(),
            FRAME_LIMIT as usize
        );
    }
    #[test]
    fn duplicate_unknown_and_nonfinite_requests_refuse() {
        for bytes in [
            br#"{"endpoint":null,"tier":"a","tier":"b"}"#.as_slice(),
            br#"{"endpoint":null,"tier":"a","extra":1}"#,
            br#"{"endpoint":{"primal":[1e999]},"tier":"a"}"#,
        ] {
            assert!(serde_json::from_slice::<CheckRequest>(bytes).is_err());
        }
    }
}
