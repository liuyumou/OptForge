//! SPEC-0035 delivery-only variant; retained numerical orchestration is unchanged.
#[path = "../../lp-fp4-checker/src/cached_certificate.rs"]
mod cached_certificate;
#[path = "../../lp-fp4-checker/src/checker.rs"]
mod checker;
mod device;
#[path = "../../lp-fp4-checker/src/exact_math.rs"]
mod exact_math;
mod model;
#[allow(dead_code)]
#[path = "../../../crates/optimizer-lp/src/outward.rs"]
mod outward;
#[path = "../../lp-fp4-accel/src/parallel_certificate.rs"]
mod parallel_certificate;
#[path = "../../lp-fp4-accel/src/policy.rs"]
mod policy;
#[path = "../../lp-fp4-checker/src/prepared_feasibility.rs"]
mod prepared_feasibility;
mod products;
#[path = "../../lp-fp4-checker/src/profile.rs"]
mod profile;
#[allow(dead_code)]
#[path = "../../../crates/optimizer-lp/src/reduce.rs"]
mod reduce;
use crate::identity::hex;
use checker::Endpoint;
use device::Engine;
use model::Data;
use optimizer_cuda_sys::{Context, Module, Stream};
#[cfg(test)]
use reduce::tree_sum;
use serde::Deserialize;
use serde_json::{Value, json};
use std::{
    collections::BTreeMap,
    fs,
    io::{self, BufRead, Read, Write},
    path::Path,
    rc::Rc,
    time::Instant,
};
type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;
const DEVICE: &str = "GPU-6721b13a-30f9-83ec-dace-ba2d9738556f";

mod config;
mod identity;
mod startup;
mod transport;
use transport::{Independent, check_service};
fn emit(value: &Value) -> Result<()> {
    let mut out = io::stdout().lock();
    if !config::get().batch {
        serde_json::to_writer(&mut out, value)?;
        out.write_all(b"\n")?;
    } else {
        let mut bytes = serde_json::to_vec(value)?;
        bytes.push(b'\n');
        out.write_all(&bytes)?;
    }
    out.flush()?;
    Ok(())
}
fn default_limit() -> u32 {
    10000
}
fn default_wall() -> u64 {
    30000
}
fn default_audit() -> u32 {
    200
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Request {
    op: String,
    #[serde(default)]
    solve_id: u64,
    #[serde(default)]
    generation: u32,
    #[serde(default)]
    lane: String,
    #[serde(default)]
    tier: String,
    #[serde(default = "default_limit")]
    max_updates: u32,
    #[serde(default = "default_wall")]
    wall_ms: u64,
    #[serde(default = "default_audit")]
    audit_max: u32,
    #[serde(default)]
    cancel_after: Option<u32>,
    #[serde(default)]
    cancel_file: Option<String>,
    #[serde(default)]
    count: u32,
    #[serde(default)]
    limit: f64,
    #[serde(default)]
    raw: Option<Vec<f64>>,
    #[serde(default)]
    fault: Option<String>,
}
impl Request {
    fn cancelled(&self, physical: u32) -> bool {
        self.cancel_after.is_some_and(|v| physical >= v)
            || self
                .cancel_file
                .as_ref()
                .is_some_and(|p| Path::new(p).exists())
    }
}
struct Session {
    data: Data,
    ctx: Rc<Context>,
    module: Module,
    stream: Stream,
    pool: BTreeMap<usize, Engine>,
    checker: Independent,
    solve_id: u64,
    physical_total: u64,
    debug: Option<usize>,
    debug_physical: u32,
    debug_cap: u32,
    setup_ns: u128,
    setup_profile: Value,
    image: String,
    cancelled: bool,
}
impl Session {
    fn new(image: &Path, path: &Path, equilibrate: bool) -> Result<Self> {
        if std::env::var("AI_OPTIMIZER_GPU_LEASE").as_deref() != Ok("inherited")
            || std::env::var("CUDA_VISIBLE_DEVICES").as_deref() != Ok(DEVICE)
        {
            return Err("pinned shared lease required".into());
        }
        let started = Instant::now();
        let mut spans = Vec::new();
        let mut mark = |name: &str, begin: u128| {
            if config::get().profile {
                spans.push(
                    json!({"phase":name,"begin_ns":begin,"end_ns":started.elapsed().as_nanos()}),
                );
            }
        };
        let data = Data::new(&fs::read(path)?, equilibrate)?;
        mark("host_model", 0);
        let begin = started.elapsed().as_nanos();
        let mut pending = if config::get().overlap {
            Some(Independent::spawn(path)?)
        } else {
            None
        };
        mark("early_checker_spawn", begin);
        let begin = started.elapsed().as_nanos();
        let ctx = Rc::new(Context::create(DEVICE)?);
        let module = ctx.load_module_file(image)?;
        let stream = ctx.stream()?;
        mark("device_context_module_stream", begin);
        let begin = started.elapsed().as_nanos();
        let mut checker = match pending.take() {
            Some(checker) => checker,
            None => Independent::spawn(path)?,
        };
        checker.ready(&data.hash)?;
        mark("checker_spawn_or_join", begin);
        let begin = started.elapsed().as_nanos();
        let image = hex(&fs::read(image)?);
        mark("image_binding", begin);
        let setup_profile = json!({"variant":config::get().name,"spans":spans,
            "checker_lifetime_to_ready_ns":checker.ready_elapsed_ns()});
        Ok(Self {
            data,
            ctx,
            module,
            stream,
            pool: BTreeMap::new(),
            checker,
            solve_id: 0,
            physical_total: 0,
            debug: None,
            debug_physical: 0,
            debug_cap: 0,
            setup_ns: started.elapsed().as_nanos(),
            setup_profile,
            image,
            cancelled: false,
        })
    }
    fn respond(&mut self, request: Request) -> Result<Value> {
        let mut value = self.command(request)?;
        if config::get().profile {
            value["delivery_profile"] = json!({"setup":self.setup_profile,
                "assessments":self.checker.take_profile()});
        }
        Ok(value)
    }
    fn lane(&self, name: &str) -> Result<usize> {
        match name {
            "native" => Ok(0),
            "nativefast" => Ok(if self.data.dense { 32 } else { 0 }),
            "gridnative" => Ok(32),
            "gridfp4x2" => Ok(34),
            "gridfp4x4" => Ok(36),
            "fp4x2" => Ok(2),
            "fp4x4" => Ok(4),
            "scalarfp4x2" => Ok(18),
            "scalarfp4x4" => Ok(20),
            "auto" => Ok(if self.data.dense && self.data.p >= 512 {
                34
            } else if self.data.dense {
                32
            } else {
                0
            }),
            _ => Err("unknown lane".into()),
        }
    }
    fn prepare(&mut self, k: usize) -> Result<()> {
        if !self.pool.contains_key(&k) {
            let e = Engine::new(&self.data, k, &self.ctx, &self.module, &self.stream)?;
            self.pool.insert(k, e);
        }
        Ok(())
    }
    fn solve(&mut self, r: &Request) -> Result<Value> {
        if r.solve_id != self.solve_id || r.generation != 0 || self.debug.is_some() {
            return Err("stale or active solve".into());
        }
        if r.max_updates == 0
            || r.max_updates > 10000
            || r.audit_max == 0
            || r.audit_max > 200
            || r.wall_ms > 30000
        {
            return Err("solve limits".into());
        }
        if !matches!(
            r.fault.as_deref(),
            None | Some("local_budget") | Some("conversion_failure")
        ) {
            return Err("unknown fault injection".into());
        }
        let tolerance = match r.tier.as_str() {
            "certified-1e-7" => 1e-7,
            "certified-1e-9" => 1e-9,
            _ => return Err("unknown final tier".into()),
        };
        let start = Instant::now();
        let mut times = BTreeMap::<&str, u128>::new();
        let mut events = Vec::new();
        let mut audits = Vec::new();
        let mut k = self.lane(&r.lane)?;
        let mut physical = 0;
        let mut gpu_us = 0.;
        let mut work = BTreeMap::<usize, u32>::new();
        let mut raw = self.data.initial.clone();
        let mut observation = self.data.observe(&raw)?;
        let mut accepted_rho = observation.rho;
        let mut saved_observation = observation.clone();
        let mut stalls = 0;
        let mut saved_stalls = 0;
        let mut saved_logical = 0;
        let mut interval = r.audit_max;
        let mut local_estimate = 0_f64;
        let mut final_certificate = None;
        let mut checked_endpoint = None;
        let mut status = "limit";
        let mut fault_used = false;
        let phase = Instant::now();
        self.prepare(k)?;
        self.pool
            .get_mut(&k)
            .unwrap()
            .reset(&self.module, &self.stream, &raw, 0, 0)?;
        times.insert("prepare_reset", phase.elapsed().as_nanos());
        if self.data.unbounded_direction.is_some() {
            status = "unbounded_direction";
        }
        while physical < r.max_updates && status == "limit" {
            if start.elapsed().as_millis() >= u128::from(r.wall_ms) || r.cancelled(physical) {
                let phase = Instant::now();
                self.pool
                    .get_mut(&k)
                    .unwrap()
                    .checkpoint(&self.module, &self.stream, true)?;
                *times.entry("rollback").or_default() += phase.elapsed().as_nanos();
                status = if r.cancelled(physical) {
                    "cancelled"
                } else {
                    "deadline"
                };
                break;
            }
            let e = self.pool.get_mut(&k).unwrap();
            let mut count = 32
                .min(interval - e.since_audit)
                .min(r.max_updates - physical);
            if let Some(cancel) = r.cancel_after {
                count = count.min(cancel.saturating_sub(physical));
            }
            let allowance = policy::allowance(observation.rho, tolerance, observation.scale);
            let phase = Instant::now();
            let step = e.run(&self.module, &self.stream, 1, count, allowance)?;
            *times.entry("iteration").or_default() += phase.elapsed().as_nanos();
            if step.done == 0 || step.done > count {
                return Err("physical work report".into());
            }
            physical += step.done;
            self.physical_total += u64::from(step.done);
            *work.entry(k).or_default() += step.done;
            gpu_us += step.gpu_us;
            let mut reason = if step.flags.iter().any(|v| *v != 0) {
                Some(if step.flags.contains(&5) {
                    "projection_ambiguous"
                } else if step.flags.contains(&1) || step.flags.contains(&2) {
                    "nonfinite"
                } else {
                    "local_budget"
                })
            } else {
                None
            };
            for terms in step.terms.chunks(8) {
                local_estimate = local_estimate.max(terms[..7].iter().map(|v| f64::from(*v)).sum());
            }
            events.push(json!({"kind":"window","lane":k,"physical":physical,"logical":e.logical,"step":step}));
            // Cancellation/deadline wins at a completed device boundary, before certification.
            if r.cancelled(physical) || start.elapsed().as_millis() >= u128::from(r.wall_ms) {
                let phase = Instant::now();
                e.checkpoint(&self.module, &self.stream, true)?;
                *times.entry("rollback").or_default() += phase.elapsed().as_nanos();
                status = if r.cancelled(physical) {
                    "cancelled"
                } else {
                    "deadline"
                };
                break;
            }
            if !fault_used && r.fault.as_deref() == Some("local_budget") {
                reason = Some("local_budget");
                fault_used = true;
            }
            if !fault_used && r.fault.as_deref() == Some("conversion_failure") {
                reason = Some("local_budget");
            }
            if reason != Some("nonfinite")
                && (e.since_audit >= interval || physical == r.max_updates || reason.is_some())
            {
                let phase = Instant::now();
                raw = e.raw(&self.module, &self.stream)?;
                *times.entry("export").or_default() += phase.elapsed().as_nanos();
                let phase = Instant::now();
                observation = self.data.observe(&raw)?;
                *times.entry("audit").or_default() += phase.elapsed().as_nanos();
                let endpoint = self.data.endpoint(&raw, "completed");
                let phase = Instant::now();
                let certificate = self.checker.assess(&endpoint, &r.tier)?;
                *times.entry("checker").or_default() += phase.elapsed().as_nanos();
                let accepted = certificate["accepted"] == true;
                audits.push(json!({"physical":physical,"logical":e.logical,"trigger":reason.unwrap_or("periodic"),"observation":observation,"endpoint":endpoint,"certificate":certificate}));
                checked_endpoint = Some(endpoint);
                final_certificate = Some(certificate);
                if accepted {
                    status = "certified";
                    break;
                }
                if reason.is_none() {
                    // Noise is the unrepresented arithmetic estimate, NOT the retained tail.
                    stalls = policy::stalled(accepted_rho, observation.rho, local_estimate, stalls);
                    if k % 16 != 0 && observation.rho > 2. * accepted_rho.max(tolerance) {
                        reason = Some("residual_growth");
                    } else if k % 16 != 0 && stalls >= 3 {
                        reason = Some("noise_limited_stagnation");
                    } else {
                        let phase = Instant::now();
                        e.checkpoint(&self.module, &self.stream, false)?;
                        *times.entry("checkpoint").or_default() += phase.elapsed().as_nanos();
                        accepted_rho = observation.rho;
                        saved_observation = observation.clone();
                        saved_logical = e.logical;
                        saved_stalls = stalls;
                        interval =
                            policy::audit_interval(observation.rho, local_estimate, r.audit_max);
                        if (16..32).contains(&k)
                            && local_estimate
                                > policy::allowance(observation.rho, tolerance, observation.scale)
                        {
                            reason = Some("anticipated_local_budget");
                        }
                        local_estimate = 0.;
                    }
                }
            }
            if let Some(reason) = reason {
                if k % 16 == 0 {
                    let phase = Instant::now();
                    self.pool
                        .get_mut(&k)
                        .unwrap()
                        .checkpoint(&self.module, &self.stream, true)?;
                    *times.entry("rollback").or_default() += phase.elapsed().as_nanos();
                    status = "numerical_failure";
                    break;
                }
                let phase = Instant::now();
                let e = self.pool.get_mut(&k).unwrap();
                e.checkpoint(&self.module, &self.stream, true)?;
                let restored = e.raw(&self.module, &self.stream)?;
                let generation = e.generation;
                if e.logical != saved_logical {
                    return Err("rollback controller mismatch".into());
                }
                *times.entry("rollback").or_default() += phase.elapsed().as_nanos();
                let old = k;
                let mut next = match k {
                    2 => 4,
                    18 => 20,
                    34 => 36,
                    36 => 32,
                    _ => 0,
                };
                let phase = Instant::now();
                self.prepare(next)?;
                let mut conversion_input = restored.clone();
                if !fault_used && r.fault.as_deref() == Some("conversion_failure") {
                    conversion_input[0] = f64::MAX;
                    fault_used = true;
                }
                let conversion = self.pool.get_mut(&next).unwrap().reset(
                    &self.module,
                    &self.stream,
                    &conversion_input,
                    saved_logical,
                    generation,
                );
                let changed = conversion.is_err()
                    || self.pool[&next].raw(&self.module, &self.stream)? != restored;
                if changed {
                    events.push(json!({"kind":"conversion_failure","from":old,"attempted":next,"physical":physical}));
                    fault_used = true;
                    next = 0;
                    self.prepare(next)?;
                    self.pool.get_mut(&next).unwrap().reset(
                        &self.module,
                        &self.stream,
                        &restored,
                        saved_logical,
                        generation,
                    )?;
                    if self.pool[&next].raw(&self.module, &self.stream)? != restored {
                        return Err("native conversion changed checkpoint".into());
                    }
                }
                *times.entry("conversion").or_default() += phase.elapsed().as_nanos();
                k = next;
                observation = saved_observation.clone();
                accepted_rho = observation.rho;
                stalls = saved_stalls;
                interval = policy::audit_interval(observation.rho, 0., r.audit_max);
                local_estimate = 0.;
                events.push(json!({"kind":"recovery","reason":reason,"from":old,"to":k,"physical":physical,"logical":saved_logical,"generation":generation}));
            }
        }
        let phase = Instant::now();
        let terminal = self.pool[&k].snapshot(&self.module, &self.stream)?;
        let saved = self.pool[&k].saved_snapshot(&self.stream)?;
        *times.entry("export").or_default() += phase.elapsed().as_nanos();
        let transport = match status {
            "cancelled" => "cancelled",
            "deadline" => "limit",
            "numerical_failure" => "error",
            "unbounded_direction" => "refused",
            _ => "completed",
        };
        let endpoint = self.data.endpoint(&terminal.raw, transport);
        if checked_endpoint.as_ref() != Some(&endpoint) {
            let phase = Instant::now();
            final_certificate = Some(self.checker.assess(&endpoint, &r.tier)?);
            *times.entry("checker").or_default() += phase.elapsed().as_nanos();
        }
        let certificate = final_certificate.ok_or("missing independent certificate")?;
        if status == "limit" && certificate["accepted"] == true {
            status = "certified";
        }
        let elapsed = start.elapsed().as_nanos();
        let assigned: u128 = times.values().sum();
        times.insert(
            "coordination",
            elapsed.checked_sub(assigned).ok_or("overlapping phases")?,
        );
        let result = json!({"schema_version":1,"kind":"lp-fp4-accel-solve","solve_id":self.solve_id,"status":status,"certified":certificate["accepted"],"lane":r.lane,"final_lane":k,"tier":r.tier,
            "physical":physical,"logical":terminal.logical,"physical_total":self.physical_total,"attempted":work,"gpu_us":gpu_us,"solve_ns":elapsed,"costs_ns":times,"setup_ns":self.setup_ns,
            "model_sha256":self.data.hash,"image_sha256":self.image,"checker_binary_sha256":self.checker.binary,"row_scale":self.data.row_scale,"shift":self.data.shift,
            "endpoint":endpoint,"certificate":certificate,"audits":audits,"events":events,
            "checkpoint":{"device":saved,"accepted_observation":saved_observation,"stalls":saved_stalls,"logical":saved_logical,"physical_outside_rollback":physical},"terminal":terminal,
            "representation":if work.keys().all(|k|k%16==0) {"FP64 state and products"} else {"FP32-pair state; FP4 increment products with original-coefficient FP64 references per <=32 updates, or explicitly selected scalar correction; native recovery recorded in attempted; operational estimates"}});
        self.cancelled = status == "cancelled";
        self.solve_id = self
            .solve_id
            .checked_add(1)
            .ok_or("solve identity overflow")?;
        Ok(result)
    }
    fn command(&mut self, r: Request) -> Result<Value> {
        if self.cancelled {
            return Err("cancelled service is terminal".into());
        }
        if r.solve_id != self.solve_id {
            return Err("stale solve identity".into());
        }
        if r.op == "prepare" {
            let k = self.lane(&r.lane)?;
            self.prepare(k)?;
            return Ok(json!({"prepared":k,"solve_id":self.solve_id}));
        }
        if r.op == "solve" {
            return self.solve(&r);
        }
        if r.op == "debug_reset" {
            if self.debug.is_some() {
                return Err("active debug solve must finish before reset".into());
            }
            let k = self.lane(&r.lane)?;
            self.prepare(k)?;
            let raw = r.raw.as_ref().unwrap_or(&self.data.initial);
            self.pool
                .get_mut(&k)
                .unwrap()
                .reset(&self.module, &self.stream, raw, 0, 0)?;
            self.debug = Some(k);
            self.debug_physical = 0;
            self.debug_cap = r.max_updates;
            return Ok(
                json!({"reset":true,"generation":0,"shift":self.data.shift,"row_scale":self.data.row_scale}),
            );
        }
        let k = self.debug.ok_or("debug state not loaded")?;
        let e = self.pool.get_mut(&k).unwrap();
        if r.generation != e.generation {
            return Err("stale generation".into());
        }
        match r.op.as_str() {
            "debug_forward" | "debug_transpose" => {
                Ok(json!({"product":e.product(&self.module,&self.stream,r.op=="debug_transpose")?}))
            }
            "debug_step" => {
                if self.debug_physical + r.count > self.debug_cap {
                    return Err("physical cap".into());
                }
                let step = e.run(&self.module, &self.stream, 1, r.count, r.limit)?;
                self.debug_physical += step.done;
                Ok(
                    json!({"step":step,"logical":e.logical,"physical":self.debug_physical,"generation":e.generation}),
                )
            }
            "debug_saved" => Ok(serde_json::to_value(e.saved_snapshot(&self.stream)?)?),
            "debug_export" => Ok(serde_json::to_value(
                e.snapshot(&self.module, &self.stream)?,
            )?),
            "debug_restore" | "debug_save" => {
                e.checkpoint(&self.module, &self.stream, r.op == "debug_restore")?;
                Ok(json!({"generation":e.generation,"logical":e.logical}))
            }
            "debug_finish" => {
                self.debug = None;
                self.solve_id += 1;
                Ok(json!({"solve_id":self.solve_id}))
            }
            _ => Err("unknown command".into()),
        }
    }
}
fn main() -> Result<()> {
    config::init()?;
    let profile = config::get().profile;
    let costs = if profile {
        Some(optimizer_core::lp_cost::Session::begin()?)
    } else {
        None
    };
    let started = Instant::now();
    let result = program();
    if let Some(costs) = costs {
        eprintln!(
            "{}",
            json!({"delivery4_process":{"role":std::env::args().nth(1),"main_ns":started.elapsed().as_nanos(),"success":result.is_ok(),"costs":costs.finish()}})
        );
    }
    result
}
fn program() -> Result<()> {
    let a: Vec<_> = std::env::args().collect();
    if a.get(1).map(String::as_str) == Some("product-pilot") {
        return products::run(&a);
    }
    if a.get(1).map(String::as_str) == Some("startup-profile") {
        return startup::run(&a);
    }
    if a.get(1).map(String::as_str) == Some("transport-profile") {
        return transport::profile(&a);
    }
    if a.get(1).map(String::as_str) == Some("profile") {
        return profile::run(&a);
    }
    if a.len() >= 3 && a[1] == "inspect" {
        let d = Data::new(&fs::read(&a[2])?, !a.iter().any(|x| x == "unscaled"))?;
        return emit(
            &json!({"n":d.original.column_count(),"m":d.original.row_count(),"p":d.p,"a":d.a,"initial":d.initial,"row_scale":d.row_scale,"shift":d.shift,"unbounded_direction":d.unbounded_direction,"packs":{"2":d.pack(2)?,"4":d.pack(4)?}}),
        );
    }
    if a.len() == 3 && a[1] == "check-service" {
        return check_service(Path::new(&a[2]));
    }
    if a.len() == 6 && ["check", "check-serial"].contains(&a[1].as_str()) {
        let bytes = fs::read(&a[2])?;
        let e: Endpoint = serde_json::from_slice(&fs::read(&a[3])?)?;
        let c = checker::Checker::new(&bytes)?;
        let mut result = if a[1] == "check-serial" {
            c.assess_serial(&e, &a[4])?
        } else {
            c.assess(&e, &a[4])?
        };
        result["checker_binary_sha256"] = json!(hex(&fs::read(std::env::current_exe()?)?));
        let mut f = fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&a[5])?;
        serde_json::to_writer(&mut f, &result)?;
        f.write_all(b"\n")?;
        f.sync_all()?;
        return Ok(());
    }
    if a.len() >= 4 && ["serve", "once"].contains(&a[1].as_str()) {
        let setup_scope = optimizer_core::lp_cost::scope("session_setup");
        let mut s = Session::new(
            Path::new(&a[2]),
            Path::new(&a[3]),
            !a.iter().any(|x| x == "unscaled"),
        )?;
        drop(setup_scope);
        if a[1] == "once" {
            let r: Request = serde_json::from_slice(&fs::read(a.get(4).ok_or("request file")?)?)?;
            let responding = optimizer_core::lp_cost::scope("response_construction");
            let response = s.respond(r)?;
            drop(responding);
            let output = optimizer_core::lp_cost::scope("response_emit");
            emit(&response)?;
            drop(output);
            let destruction = optimizer_core::lp_cost::scope("session_destruction");
            drop(s);
            drop(destruction);
            return Ok(());
        }
        emit(
            &json!({"ready":true,"model_sha256":s.data.hash,"setup_ns":s.setup_ns,"solve_id":0,"delivery_variant":config::get().name,"delivery_profile":if config::get().profile {s.setup_profile.clone()} else {Value::Null}}),
        )?;
        let mut input = io::stdin().lock();
        loop {
            let mut line = String::new();
            let got = (&mut input).take((8 << 20) + 1).read_line(&mut line)?;
            if got == 0 {
                break;
            }
            if got > 8 << 20 {
                return Err("command frame limit".into());
            }
            let r: Request = serde_json::from_str(&line)?;
            let responding = optimizer_core::lp_cost::scope("response_construction");
            let response = s.respond(r)?;
            drop(responding);
            let output = optimizer_core::lp_cost::scope("response_emit");
            emit(&response)?;
            drop(output);
        }
        let destruction = optimizer_core::lp_cost::scope("session_destruction");
        drop(s);
        drop(destruction);
        return Ok(());
    }
    Err("usage: serve IMAGE MODEL [unscaled] | once IMAGE MODEL REQUEST [unscaled] | check-service MODEL | check MODEL ENDPOINT TIER OUTPUT".into())
}
