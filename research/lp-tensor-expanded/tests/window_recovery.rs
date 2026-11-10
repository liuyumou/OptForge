#![allow(dead_code)]
pub use lp_tensor_expanded_research::value;
pub use optimizer_lp::{Engine, control, exec, precision, quant, reduce, research};
#[path = "../src/outward.rs"]
mod outward;
#[path = "../src/solver.rs"]
mod tensor_cost;
#[path = "../src/prepared.rs"]
mod tensor_cost_prepare;
use optimizer_core::{CancellationToken, LpSettings, Model};
use optimizer_lp::{LinearProgram, control::Fp64State};
use tensor_cost::{Generation, HostOracle, Layout, Operator, Oracle, Window};

fn model() -> Model {
    let variables=(0..32).map(|id|serde_json::json!({"id":id,"domain":"continuous","lower":{"kind":"finite","value":0.},"upper":{"kind":"finite","value":1.}})).collect::<Vec<_>>();
    let constraints=(0..32).map(|id|serde_json::json!({"id":id,"lower":{"kind":"negative_infinity"},"upper":{"kind":"finite","value":16.},"terms":(0..32).map(|j|serde_json::json!({"variable_id":j,"coefficient":if j==id {2.}else{0.125}})).collect::<Vec<_>>()})).collect::<Vec<_>>();
    Model::from_json(&serde_json::to_vec(&serde_json::json!({"schema_version":1,"model_id":"expanded-recovery-new","variables":variables,"constraints":constraints,"objective":{"sense":"minimize","offset":0.,"terms":(0..32).map(|id|serde_json::json!({"variable_id":id,"coefficient":-1.})).collect::<Vec<_>>()}})).unwrap()).unwrap()
}
fn settings() -> quant::Settings {
    serde_json::from_value(serde_json::json!({"audit_absolute":1e-7,"audit_interval":32,"audit_relative":1e-7,"dual_budget":1e-7,"format":"fp64","policy":"uniform","primal_budget":1e-7,"rounding":"nearest_even","tile_size":32})).unwrap()
}
fn method() -> LpSettings {
    LpSettings::from_json(include_bytes!("../../../examples/lp-settings-v1.json")).unwrap()
}

struct RejectOnce {
    rejected: bool,
}
impl Oracle for RejectOnce {
    fn window(
        &mut self,
        e: &Engine<'_>,
        op: &Operator,
        g: &Generation,
        s: &Fp64State,
        len: u64,
    ) -> Result<Window, String> {
        let mut result = HostOracle.window(e, op, g, s, len)?;
        if !self.rejected {
            assert!(result.failure.is_none());
            result.failure = Some("injected_expanded_numerical_refusal".into());
            result.bad = (0..op.tiles.len())
                .filter(|&i| !g.promotion().mask[i])
                .collect();
            self.rejected = true;
        } else {
            assert!(g.promotion().native);
        }
        Ok(result)
    }
}
#[test]
fn rejection_charges_whole_window_and_native_promotion_stays_sticky() {
    let model = model();
    let program = LinearProgram::new(&model).unwrap();
    let mut engine = Engine::new(&program, method());
    let op = Operator::new(&engine, settings(), Layout::Int8).unwrap();
    engine.restrict_step(op.step).unwrap();
    let result = tensor_cost::run(
        &engine,
        &op,
        &mut RejectOnce { rejected: false },
        64,
        &CancellationToken::new(),
        None,
        |_, _| false,
    );
    assert_eq!(result.core.stop, "work_horizon");
    assert_eq!(result.core.iterations, 64);
    assert_eq!(result.core.physical, 98);
    assert_eq!(result.core.work.rejected, 32);
    assert_eq!(result.core.work.replays, 32);
    assert!(result.core.promotion.native);
    assert_eq!(result.core.promotion.transitions, 1);
    assert_eq!(result.counts.useful_windows, 0);
}

struct Cancel<'a> {
    token: &'a CancellationToken,
    after_reference: bool,
}
impl Oracle for Cancel<'_> {
    fn window(
        &mut self,
        e: &Engine<'_>,
        op: &Operator,
        g: &Generation,
        s: &Fp64State,
        len: u64,
    ) -> Result<Window, String> {
        let result = HostOracle.window(e, op, g, s, len)?;
        if !self.after_reference {
            self.token.cancel();
        }
        Ok(result)
    }
    fn reference(&mut self, e: &Engine<'_>, s: &Fp64State) -> Result<(Vec<f64>, Vec<f64>), String> {
        let point = precision::correction(e, s).map_err(str::to_string)?;
        if self.after_reference {
            self.token.cancel();
        }
        Ok(point)
    }
}
#[test]
fn cancellation_on_either_side_of_audit_never_publishes_candidate() {
    let model = model();
    let program = LinearProgram::new(&model).unwrap();
    let mut engine = Engine::new(&program, method());
    let op = Operator::new(&engine, settings(), Layout::Int8).unwrap();
    engine.restrict_step(op.step).unwrap();
    for after_reference in [false, true] {
        let token = CancellationToken::new();
        let result = tensor_cost::run(
            &engine,
            &op,
            &mut Cancel {
                token: &token,
                after_reference,
            },
            64,
            &token,
            None,
            |_, _| false,
        );
        assert_eq!(result.core.stop, "interrupted");
        assert_eq!(result.core.iterations, 0);
        assert_eq!(result.core.physical, 32 + u64::from(after_reference));
        assert_eq!(
            result.core.primal,
            engine.unscale_primal(&engine.start_primal())
        );
        assert_eq!(result.core.dual, engine.unscale_dual(&engine.start_dual()));
    }
}
struct FailedReference;
impl Oracle for FailedReference {
    fn window(
        &mut self,
        e: &Engine<'_>,
        op: &Operator,
        g: &Generation,
        s: &Fp64State,
        len: u64,
    ) -> Result<Window, String> {
        HostOracle.window(e, op, g, s, len)
    }
    fn reference(&mut self, _: &Engine<'_>, _: &Fp64State) -> Result<(Vec<f64>, Vec<f64>), String> {
        Err("injected_reference_failure".into())
    }
}
#[test]
fn reference_failure_rolls_back_and_retains_audit_charge() {
    let model = model();
    let program = LinearProgram::new(&model).unwrap();
    let mut engine = Engine::new(&program, method());
    let op = Operator::new(&engine, settings(), Layout::Int8).unwrap();
    engine.restrict_step(op.step).unwrap();
    let result = tensor_cost::run(
        &engine,
        &op,
        &mut FailedReference,
        64,
        &CancellationToken::new(),
        None,
        |_, _| false,
    );
    assert_eq!(result.core.stop, "numerical_failure");
    assert_eq!(result.core.iterations, 0);
    assert_eq!(result.core.physical, 33);
    assert_eq!(
        result.core.failure.as_deref(),
        Some("injected_reference_failure")
    );
    assert!(!result.core.promotion.native);
}
#[test]
fn checkpoints_reject_wrong_session_and_stale_generation() {
    let model = model();
    let program = LinearProgram::new(&model).unwrap();
    let engine = Engine::new(&program, method());
    let op = Operator::new(&engine, settings(), Layout::Int8).unwrap();
    let mut first = tensor_cost::Session::new(&engine, &op, None).unwrap();
    let mut second = tensor_cost::Session::new(&engine, &op, None).unwrap();
    let checkpoint = first.checkpoint();
    let stale = std::sync::Arc::new(());
    assert_eq!(
        second.restore(&checkpoint, &stale),
        Err("resident_checkpoint_session")
    );
    assert_eq!(
        first.restore(&checkpoint, &stale),
        Err("expanded_stale_generation")
    );
}
#[derive(Default)]
struct Trace {
    windows: Vec<(u64, u64, u64)>,
}
impl Oracle for Trace {
    fn window(
        &mut self,
        e: &Engine<'_>,
        op: &Operator,
        g: &Generation,
        s: &Fp64State,
        len: u64,
    ) -> Result<Window, String> {
        self.windows.push((s.iterations, len, s.checked_iteration));
        HostOracle.window(e, op, g, s, len)
    }
}
#[test]
fn controller_clipping_and_full_candidate_replay_are_deterministic() {
    let model = model();
    let program = LinearProgram::new(&model).unwrap();
    let mut engine = Engine::new(&program, method());
    let op = Operator::new(&engine, settings(), Layout::Int8).unwrap();
    engine.restrict_step(op.step).unwrap();
    let mut first = Trace::default();
    let mut second = Trace::default();
    let a = tensor_cost::run(
        &engine,
        &op,
        &mut first,
        208,
        &CancellationToken::new(),
        None,
        |_, _| false,
    );
    let b = tensor_cost::run(
        &engine,
        &op,
        &mut second,
        208,
        &CancellationToken::new(),
        None,
        |_, _| false,
    );
    assert_eq!(a.core.stop, "work_horizon");
    assert_eq!(a.core.iterations, 208);
    assert_eq!(a.core.physical, 216);
    assert_eq!(
        serde_json::to_vec(&a).unwrap(),
        serde_json::to_vec(&b).unwrap()
    );
    assert_eq!(first.windows, second.windows);
    assert!(first.windows.contains(&(192, 8, 0)));
    assert!(first.windows.contains(&(200, 8, 200)));
    assert!(
        first
            .windows
            .iter()
            .all(|(i, n, _)| *n > 0 && *n <= 32 && *n <= 200 - i % 200)
    );
}
