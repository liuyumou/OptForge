//! ADR-0039 assessment scheduling. Indicators have no mathematical authority.
#![allow(missing_docs)]
use crate::{
    Engine, Iterate,
    control::{Fp64Checkpoint, Fp64Controller},
    precision::{PrecisionOperator, step},
};
use optimizer_core::{CancellationToken, LpPrecisionSettings, LpWidth};
use serde::{Deserialize, Serialize};
use std::time::Instant;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Arithmetic {
    TunedFp64,
    AccumulationFp32,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Policy {
    #[serde(rename = "fixed_200")]
    Fixed200,
    #[serde(rename = "bounded_800")]
    Bounded800,
}
impl Arithmetic {
    pub fn precision(self) -> LpPrecisionSettings {
        let w = if self == Self::AccumulationFp32 {
            LpWidth::F32
        } else {
            LpWidth::F64
        };
        LpPrecisionSettings {
            schema_version: 1,
            matrix: w,
            product_operands: w,
            products: w,
            accumulation: w,
            updates: LpWidth::F64,
            working_state: LpWidth::F64,
            correction_interval: None,
            rounding: "nearest_even".into(),
        }
    }
}
#[derive(Clone, Debug, PartialEq)]
pub struct Scheduler {
    policy: Policy,
    previous: Vec<f64>,
    sample_iteration: u64,
    last_assessment: u64,
    reference: Option<f64>,
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Decision {
    pub iteration: u64,
    pub movement: Option<f64>,
    pub assess: bool,
    pub reason: String,
}
impl Scheduler {
    pub fn new(policy: Policy, primal: &[f64], dual: &[f64]) -> Self {
        Self {
            policy,
            previous: primal.iter().chain(dual).copied().collect(),
            sample_iteration: 0,
            last_assessment: 0,
            reference: None,
        }
    }
    pub fn sample(
        &mut self,
        iteration: u64,
        primal: &[f64],
        dual: &[f64],
    ) -> Result<Decision, String> {
        if iteration != self.sample_iteration + 200
            || primal.len() + dual.len() != self.previous.len()
        {
            return Err("assessment_sample_position_or_shape".into());
        }
        if self.policy == Policy::Fixed200 {
            self.sample_iteration = iteration;
            self.last_assessment = iteration;
            return Ok(Decision {
                iteration,
                movement: None,
                assess: true,
                reason: "fixed".into(),
            });
        }
        let mut movement = Some(0.0_f64);
        for (previous, current) in self.previous.iter_mut().zip(primal.iter().chain(dual)) {
            if !previous.is_finite() || !current.is_finite() {
                movement = None;
            } else if let Some(q) = &mut movement {
                let scale = 1.0_f64.max(previous.abs()).max(current.abs());
                *q = q.max((current / scale - *previous / scale).abs());
            }
            *previous = *current;
        }
        self.sample_iteration = iteration;
        let reason = if self.policy == Policy::Fixed200 {
            "fixed"
        } else if self.last_assessment == 0 {
            "first"
        } else if movement.is_none() {
            "invalid_indicator"
        } else if iteration - self.last_assessment >= 800 {
            "maximum_spacing"
        } else if self
            .reference
            .is_some_and(|r| r > 0.0 && movement.is_some_and(|q| q <= r / 2.0))
        {
            "movement"
        } else {
            "defer"
        };
        let assess = reason != "defer";
        if assess {
            self.last_assessment = iteration;
            self.reference = movement;
        }
        Ok(Decision {
            iteration,
            movement,
            assess,
            reason: reason.into(),
        })
    }
}
#[derive(Clone)]
pub struct Checkpoint<'e, 'p> {
    controller: Fp64Checkpoint<'e, 'p>,
    scheduler: Scheduler,
}
pub struct Session<'e, 'p> {
    pub controller: Fp64Controller<'e, 'p>,
    scheduler: Scheduler,
}
impl<'e, 'p> Session<'e, 'p> {
    pub fn new(engine: &'e Engine<'p>, policy: Policy, deadline: Option<Instant>) -> Self {
        let mut controller = Fp64Controller::new(engine);
        controller.set_deadline(deadline);
        let scheduler =
            Scheduler::new(policy, &controller.state().primal, &controller.state().dual);
        Self {
            controller,
            scheduler,
        }
    }
    pub fn checkpoint(&self) -> Checkpoint<'e, 'p> {
        Checkpoint {
            controller: self.controller.checkpoint(),
            scheduler: self.scheduler.clone(),
        }
    }
    pub fn restore(&mut self, snapshot: &Checkpoint<'e, 'p>) -> Result<(), String> {
        if self.scheduler.policy != snapshot.scheduler.policy {
            return Err("assessment_checkpoint_policy".into());
        }
        self.controller
            .restore(&snapshot.controller)
            .map_err(str::to_string)?;
        self.scheduler = snapshot.scheduler.clone();
        Ok(())
    }
    pub fn sample(&mut self) -> Result<Decision, String> {
        let s = self.controller.state();
        self.scheduler.sample(s.iterations, &s.primal, &s.dual)
    }
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Point {
    pub iteration: u64,
    pub primal: Vec<f64>,
    pub dual: Vec<f64>,
}
impl From<Iterate> for Point {
    fn from(p: Iterate) -> Self {
        Self {
            iteration: p.iterations,
            primal: p.primal,
            dual: p.dual,
        }
    }
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Frame {
    pub point: Point,
    pub scaled_primal: Vec<f64>,
    pub scaled_dual: Vec<f64>,
    pub weight: f64,
    pub restarts: u64,
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Event {
    pub decision: Decision,
    pub closed: bool,
    pub restarts: u64,
    pub weight: f64,
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Outcome {
    pub status: String,
    pub failure: Option<String>,
    pub point: Option<Point>,
    pub physical_steps: Option<u64>,
    pub logical_steps: u64,
    pub proposed_steps: u64,
    pub assessments: u64,
    pub controller_checks: u64,
    pub kkt_evaluations: u64,
    pub restarts: u64,
    pub events: Vec<Event>,
    pub frames: Vec<Frame>,
}
/// The executor commits only synchronized, range-clean steps; rejected work is charged.
/// Device errors must start with `device:` so an unknown endpoint stays unpublished.
#[allow(clippy::too_many_arguments)]
pub fn run<'e, 'p>(
    engine: &'e Engine<'p>,
    policy: Policy,
    diagnostic: bool,
    cancel: &CancellationToken,
    deadline: Option<Instant>,
    chunk_limit: u64,
    mut advance: impl FnMut(&mut Fp64Controller<'e, 'p>, u64) -> Result<(), String>,
    mut assess: impl FnMut(&Point) -> bool,
) -> Outcome {
    let mut session = Session::new(engine, policy, deadline);
    let mut status = "iteration_limit".to_string();
    let mut failure = None;
    let mut events = Vec::new();
    let mut frames = Vec::new();
    let mut assessments = 0;
    let mut controller_checks = 0;
    let mut proposed_steps = 0;
    let mut unknown = false;
    while session.controller.remaining() > 0 {
        if cancel.is_cancelled() {
            status = "interrupted".into();
            break;
        }
        if session.controller.expired() {
            status = "time_limit".into();
            break;
        }
        let chunk = session.controller.next_chunk(chunk_limit);
        proposed_steps += chunk;
        let before = session.controller.physical_iterations();
        if let Err(reason) = advance(&mut session.controller, chunk) {
            if reason.starts_with("preflight:") {
                proposed_steps -= chunk;
            }
            unknown = reason.starts_with("device:");
            status = if unknown {
                "device_failure"
            } else {
                "numerical_failure"
            }
            .into();
            failure = Some(
                reason
                    .strip_prefix("preflight:")
                    .unwrap_or(&reason)
                    .to_string(),
            );
            break;
        }
        if session.controller.physical_iterations() == before {
            status = "interrupted".into();
            break;
        }
        if cancel.is_cancelled() || session.controller.expired() {
            status = if cancel.is_cancelled() {
                "interrupted"
            } else {
                "time_limit"
            }
            .into();
            break;
        }
        if session.controller.check_pending() {
            let decision = session.sample().expect("contiguous assessment boundary");
            let point = Point::from(session.controller.iterate());
            let closed = if decision.assess {
                assessments += 1;
                assess(&point)
            } else {
                false
            };
            let s = session.controller.state();
            if diagnostic {
                frames.push(Frame {
                    point,
                    scaled_primal: s.primal.clone(),
                    scaled_dual: s.dual.clone(),
                    weight: s.weight,
                    restarts: s.restarts,
                });
            }
            events.push(Event {
                decision,
                closed,
                restarts: s.restarts,
                weight: s.weight,
            });
            if closed && !diagnostic {
                status = "accepted".into();
                break;
            }
            // Every nonterminal check retains the inherited recurrence, even when
            // expensive original-model assessment was deferred.
            session.controller.continue_after_check();
            controller_checks += 1;
        }
    }
    let point = if unknown {
        None
    } else {
        Some(Point::from(session.controller.iterate()))
    };
    if let Some(p) = &point {
        assessments += 1;
        let final_closed = assess(p);
        // A completed work limit may discover success; interruption/failure takes
        // precedence, including a deadline reached inside the final assessment.
        if cancel.is_cancelled() && status != "numerical_failure" {
            status = "interrupted".into();
        } else if session.controller.expired() && status != "numerical_failure" {
            status = "time_limit".into();
        } else if final_closed
            && !diagnostic
            && (status == "accepted" || status == "iteration_limit")
        {
            status = "accepted".into();
        } else if status == "accepted" && !final_closed {
            status = "numerical_failure".into();
            failure = Some("final_certification_rejected".into());
        }
    }
    Outcome {
        status,
        failure,
        point,
        physical_steps: (!unknown).then(|| session.controller.physical_iterations()),
        logical_steps: session.controller.state().iterations,
        proposed_steps,
        assessments,
        controller_checks,
        kkt_evaluations: session.controller.kkt_evaluations(),
        restarts: session.controller.state().restarts,
        events,
        frames,
    }
}
/// CPU common-trajectory executor, with the existing warp32 FP32 step oracle.
pub fn run_cpu(
    engine: &Engine<'_>,
    arithmetic: Arithmetic,
    policy: Policy,
    diagnostic: bool,
    cancel: &CancellationToken,
    deadline: Option<Instant>,
    mut assess: impl FnMut(&Point) -> bool,
) -> Outcome {
    let op = if arithmetic == Arithmetic::AccumulationFp32 {
        PrecisionOperator::new(engine, &arithmetic.precision()).ok()
    } else {
        None
    };
    run(
        engine,
        policy,
        diagnostic,
        cancel,
        deadline,
        64,
        |c, chunk| {
            let (rows, cols) = if arithmetic == Arithmetic::TunedFp64 {
                engine.scaled_matrix()
            } else {
                let op = op.as_ref().ok_or("preflight:precision_operator_refusal")?;
                (&op.rows[..], &op.columns[..])
            };
            let width = if arithmetic == Arithmetic::TunedFp64 {
                LpWidth::F64
            } else {
                LpWidth::F32
            };
            // Keep the last safe host endpoint if any step in a guarded window fails.
            let primal_step = engine.step() / c.state().weight;
            let dual_step = engine.step() * c.state().weight;
            if !primal_step.is_finite()
                || !dual_step.is_finite()
                || primal_step == 0.0
                || dual_step == 0.0
            {
                return Err("preflight:update_step_range".into());
            }
            let saved = c.checkpoint();
            let before = c.physical_iterations();
            for _ in 0..chunk {
                match step(engine, c.state(), rows, cols, width, width) {
                    Ok((x, y)) => {
                        let (cx, cy, _, _) = c.buffers();
                        cx.copy_from_slice(&x);
                        cy.copy_from_slice(&y);
                        c.commit_steps(1)?;
                    }
                    Err(reason) => {
                        let completed = c.physical_iterations() - before;
                        c.restore(&saved)?;
                        c.charge_extra(chunk - completed)?;
                        return Err(reason.into());
                    }
                }
            }
            Ok(())
        },
        |p| assess(p),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{LinearProgram, LpSettings};
    use optimizer_core::Model;
    fn model() -> Model {
        Model::from_json(include_bytes!("../../../examples/lp-model-v1.json")).unwrap()
    }
    #[test]
    fn bounded_spacing_zero_and_deceptive_indicators() {
        let mut s = Scheduler::new(Policy::Bounded800, &[0.0], &[]);
        let mut selected = Vec::new();
        for k in 1..=13 {
            let d = s.sample(200 * k, &[0.0], &[]).unwrap();
            if d.assess {
                selected.push(d.iteration);
            }
        }
        assert_eq!(selected, vec![200, 1000, 1800, 2600]);
        assert!(s.sample(3000, &[0.0], &[]).is_err());
        let mut s = Scheduler::new(Policy::Bounded800, &[0.0], &[]);
        assert!(s.sample(200, &[f64::MAX], &[]).unwrap().assess);
        let d = s.sample(400, &[f64::MAX], &[]).unwrap();
        assert!(d.assess);
        assert_eq!(d.movement, Some(0.0));
        assert!(s.sample(600, &[f64::NAN], &[]).unwrap().assess);
    }
    #[test]
    fn subnormal_motion_has_scheduling_authority_only() {
        let mut s = Scheduler::new(Policy::Bounded800, &[0.0], &[]);
        assert!(s.sample(200, &[f64::from_bits(1)], &[]).unwrap().assess);
        assert!(!s.sample(400, &[f64::from_bits(2)], &[]).unwrap().assess);
    }
    #[test]
    fn checkpoint_restores_both_logical_states_and_keeps_work_deadline() {
        let m = model();
        let p = LinearProgram::new(&m).unwrap();
        let settings = LpSettings::published(2000, 200);
        let e = Engine::new(&p, settings);
        let other = Engine::new(&p, settings);
        let deadline = Instant::now() + std::time::Duration::from_secs(20);
        let mut s = Session::new(&e, Policy::Bounded800, Some(deadline));
        for _ in 0..4 {
            s.controller.advance_host(64, &CancellationToken::new());
        }
        s.sample().unwrap();
        s.controller.continue_after_check();
        let cp = s.checkpoint();
        for _ in 0..4 {
            s.controller.advance_host(64, &CancellationToken::new());
        }
        let next = s.sample().unwrap();
        s.controller.continue_after_check();
        let physical = s.controller.physical_iterations();
        let kkt = s.controller.kkt_evaluations();
        s.restore(&cp).unwrap();
        assert_eq!(s.controller.state().iterations, 200);
        assert_eq!(s.controller.physical_iterations(), physical);
        assert_eq!(s.controller.kkt_evaluations(), kkt);
        assert!(s.controller.expired_at(deadline));
        for _ in 0..4 {
            s.controller.advance_host(64, &CancellationToken::new());
        }
        assert_eq!(s.sample().unwrap(), next);
        assert!(
            Session::new(&other, Policy::Bounded800, None)
                .restore(&cp)
                .is_err()
        );
        assert!(
            Session::new(&e, Policy::Fixed200, None)
                .restore(&cp)
                .is_err()
        );
    }
    #[test]
    fn policies_keep_numerical_trajectory_and_final_partial_point() {
        let m = model();
        let p = LinearProgram::new(&m).unwrap();
        let mut e = Engine::new(&p, LpSettings::published(1801, 200));
        let op = PrecisionOperator::new(&e, &Arithmetic::AccumulationFp32.precision()).unwrap();
        e.restrict_step(op.step).unwrap();
        for arithmetic in [Arithmetic::TunedFp64, Arithmetic::AccumulationFp32] {
            let a = run_cpu(
                &e,
                arithmetic,
                Policy::Fixed200,
                true,
                &CancellationToken::new(),
                None,
                |_| false,
            );
            let b = run_cpu(
                &e,
                arithmetic,
                Policy::Bounded800,
                true,
                &CancellationToken::new(),
                None,
                |_| false,
            );
            assert_eq!(a.frames, b.frames);
            assert_eq!(a.point, b.point);
            assert_eq!(b.point.as_ref().unwrap().iteration, 1801);
            assert_eq!(a.controller_checks, b.controller_checks);
            assert!(a.assessments > b.assessments);
            assert_eq!(a.physical_steps, Some(1801));
        }
    }
    #[test]
    fn final_discovery_and_cancellation_keep_distinct_termination() {
        let m = model();
        let p = LinearProgram::new(&m).unwrap();
        let e = Engine::new(&p, LpSettings::published(201, 200));
        let o = run_cpu(
            &e,
            Arithmetic::TunedFp64,
            Policy::Bounded800,
            false,
            &CancellationToken::new(),
            None,
            |p| p.iteration == 201,
        );
        assert_eq!(o.status, "accepted");
        assert_eq!(o.point.unwrap().iteration, 201);
        let cancel = CancellationToken::new();
        cancel.cancel();
        let o = run_cpu(
            &e,
            Arithmetic::TunedFp64,
            Policy::Bounded800,
            false,
            &cancel,
            None,
            |_| true,
        );
        assert_eq!(o.status, "interrupted");
        assert_eq!(o.physical_steps, Some(0));
        let o = run_cpu(
            &e,
            Arithmetic::TunedFp64,
            Policy::Bounded800,
            false,
            &CancellationToken::new(),
            Some(Instant::now()),
            |_| true,
        );
        assert_eq!(o.status, "time_limit");
        assert_eq!(o.physical_steps, Some(0));
    }
}
