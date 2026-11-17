use lp_general_lowbit::engine::Engine;
use lp_general_lowbit::{control::Fp64Controller, merit::EngineMerit};
use lp_general_lowbit::{
    operator::{Format, Operator},
    solve::{Settings, cpu},
};
use optimizer_core::{CancellationToken, Model};
use optimizer_lp::LinearProgram;
use serde_json::json;

fn model(n: usize, m: usize) -> Model {
    let f = |v| json!({"kind":"finite","value":v});
    Model::from_json(&serde_json::to_vec(&json!({"schema_version":1,"model_id":"general-contract",
        "variables":(0..n).map(|j|json!({"id":3*j+7,"domain":"continuous","lower":f(-2.),"upper":f(3.)})).collect::<Vec<_>>(),
        "constraints":(0..m).map(|i|json!({"id":5*i+11,"lower":f(-1.),"upper":f(1.),
            "terms":(0..n.min(5)).map(|j|json!({"variable_id":3*((j+i)%n)+7,"coefficient":((13*i+7*j)%17) as f64/19.+0.01})).collect::<Vec<_>>() })).collect::<Vec<_>>(),
        "objective":{"sense":"minimize","offset":3.25,"terms":[{"variable_id":7,"coefficient":1.}]}
    })).unwrap()).unwrap()
}
fn settings(format: Format) -> Settings {
    Settings {
        format,
        tolerance: 1e-9,
        iteration_limit: 24,
        check_interval: 8,
        reference_window: 4,
        wall_ms: 30000,
        equilibrate: true,
        force_recovery_after: None,
        cancel_after: None,
    }
}
#[test]
fn large_rectangular_storage_is_linear_and_transpose_is_canonical() {
    let model = model(32769, 3);
    let p = LinearProgram::new(&model).unwrap();
    let e = Engine::new(&p, settings(Format::Native).lp());
    let op = Operator::new(&e).unwrap();
    assert_eq!(op.rows.offsets.len(), 4);
    assert_eq!(op.columns.offsets.len(), 32770);
    assert!(op.storage_bytes() < 64 * p.nonzeros() + 8 * (p.row_count() + p.column_count()) + 256);
    for (q, &id) in op.columns.ids.iter().enumerate() {
        assert_eq!(
            op.columns.original[q].to_bits(),
            op.rows.original[id as usize].to_bits()
        );
        for f in [Format::Fp4x1, Format::Fp4x2, Format::Fp32] {
            assert!(op.parts(id as usize, f).iter().all(|v| v.is_finite()));
        }
    }
}
#[test]
fn scaling_and_precision_factors_are_effective() {
    let mut v: serde_json::Value = serde_json::from_str(&model(9, 5).to_json().unwrap()).unwrap();
    for (i, row) in v["constraints"]
        .as_array_mut()
        .unwrap()
        .iter_mut()
        .enumerate()
    {
        for t in row["terms"].as_array_mut().unwrap() {
            t["coefficient"] =
                json!(t["coefficient"].as_f64().unwrap() * 2f64.powi(i as i32 * 4 - 8));
        }
    }
    let model = Model::from_json(&serde_json::to_vec(&v).unwrap()).unwrap();
    let p = LinearProgram::new(&model).unwrap();
    let e = Engine::new(&p, settings(Format::Fp4x2).lp());
    let op = Operator::new(&e).unwrap();
    assert!(
        e.preconditioner()
            .row()
            .iter()
            .chain(e.preconditioner().column())
            .any(|v| *v != 1.)
    );
    assert!((0..p.nonzeros()).any(|i| {
        let a = op.parts(i, Format::Fp4x2);
        (a[0] + a[1]).to_bits() != op.rows.original[i].to_bits()
    }));
}
#[test]
fn native_uses_the_shared_restart_controller_exactly() {
    let model = model(9, 5);
    let s = settings(Format::Native);
    let p = LinearProgram::new(&model).unwrap();
    let e = Engine::new(&p, s.lp());
    let mut c = Fp64Controller::new_with_merit(&e, |x, y, w| e.projected_residual(x, y, w));
    let result = cpu(&model, &s).unwrap();
    let physical = result["physical"].as_u64().unwrap();
    while c.physical_iterations() < physical {
        if c.check_pending() {
            c.continue_after_check_with_merit(|x, y, w| e.projected_residual(x, y, w));
        }
        c.advance_host(
            (physical - c.physical_iterations()).min(4),
            &CancellationToken::new(),
        );
    }
    let endpoint = c.iterate();
    for (field, expected) in [("primal", endpoint.primal), ("dual", endpoint.dual)] {
        let actual: Vec<f64> = serde_json::from_value(result[field].clone()).unwrap();
        assert_eq!(
            actual.iter().map(|v| v.to_bits()).collect::<Vec<_>>(),
            expected.iter().map(|v| v.to_bits()).collect::<Vec<_>>()
        );
    }
    assert_eq!(result["restarts"], json!(c.state().restarts));
}
#[test]
fn recovery_restores_all_controller_state_and_retains_physical_work() {
    let model = model(9, 5);
    let mut s = settings(Format::Fp4x2);
    s.force_recovery_after = Some(2);
    let r = cpu(&model, &s).unwrap();
    let recoveries = r["recoveries"].as_array().unwrap();
    assert!(!recoveries.is_empty());
    assert!(recoveries.iter().all(|x| x["restored_exact"] == true));
    assert!(r["physical"].as_u64().unwrap() > r["logical"].as_u64().unwrap());
    assert_eq!(
        r["accepted"]
            .as_array()
            .unwrap()
            .iter()
            .map(|v| v.as_u64().unwrap())
            .sum::<u64>(),
        r["logical"].as_u64().unwrap()
    );
}
#[test]
fn cancellation_cannot_acquire_a_certificate() {
    let model = model(9, 5);
    let mut s = settings(Format::Fp4x2);
    s.cancel_after = Some(2);
    let r = cpu(&model, &s).unwrap();
    assert_eq!(r["status"], "cancelled");
    assert_eq!(r["certified"], false);
    assert_eq!(r["physical"], 2);
    assert_eq!(r["logical"], 0);
}
#[test]
fn malformed_vectors_and_limits_refuse() {
    let model = model(9, 5);
    let p = LinearProgram::new(&model).unwrap();
    let e = Engine::new(&p, settings(Format::Native).lp());
    let op = Operator::new(&e).unwrap();
    assert!(op.native(false, &[0.; 8]).is_err());
    assert!(op.native(false, &[f64::NAN; 9]).is_err());
    let mut s = settings(Format::Native);
    s.reference_window = 0;
    assert!(cpu(&model, &s).is_err());
}

#[test]
fn projected_merit_detects_nonoptimal_feasible_bounded_point() {
    let model = model(9, 5);
    let p = LinearProgram::new(&model).unwrap();
    let e = Engine::new(&p, settings(Format::Native).lp());
    assert!(e.projected_residual(&e.start_primal(), &e.start_dual(), 1.) > 0.);
    assert_eq!(
        e.projected_residual(&e.start_primal(), &e.start_dual(), f64::NAN),
        f64::INFINITY
    );
}

#[test]
fn local_budget_has_state_units_and_refuses_invalid_residuals() {
    use lp_general_lowbit::merit::local_budget;
    // A change of state units must change both the displacement and its budget
    // by the same factor, including across the former arbitrary unit cap.
    for residual in [
        0.0001,
        0.9194926669165853,
        2.1827966242708032,
        44.907396156528996,
    ] {
        for exponent in [-20, -1, 0, 1, 20] {
            let factor = 2f64.powi(exponent);
            assert_eq!(
                local_budget(residual * factor),
                local_budget(residual) * factor
            );
        }
    }
    for residual in [0., -1., f64::NAN, f64::INFINITY, f64::NEG_INFINITY] {
        assert_eq!(local_budget(residual), 0.);
    }
}

#[test]
fn empty_operator_can_certify_and_state_comparison_preserves_zero_sign() {
    let mut value: serde_json::Value =
        serde_json::from_str(&model(9, 0).to_json().unwrap()).unwrap();
    value["objective"]["terms"] = json!([]);
    let model = Model::from_json(&serde_json::to_vec(&value).unwrap()).unwrap();
    let s = settings(Format::Fp4x2);
    let result = cpu(&model, &s).unwrap();
    assert_eq!(result["certified"], true);
    assert_eq!(result["logical"], 8);
    let p = LinearProgram::new(&model).unwrap();
    let e = Engine::new(&p, s.lp());
    let a = Fp64Controller::new(&e).state().clone();
    let mut b = a.clone();
    b.primal[0] = -0.;
    assert!(!lp_general_lowbit::solve::same_state(&a, &b));
}

#[test]
fn controls_do_not_pay_for_unreachable_lowbit_representations() {
    let model = model(33, 17);
    let p = LinearProgram::new(&model).unwrap();
    let e = Engine::new(&p, settings(Format::Native).lp());
    let native = Operator::new_for(&e, Format::Native).unwrap();
    let float = Operator::new_for(&e, Format::Fp32).unwrap();
    let mixed = Operator::new_for(&e, Format::Fp4x2).unwrap();
    assert!(native.codes.is_empty() && native.exponents.is_empty() && native.fp32.is_empty());
    assert!(native.rows.ids.is_empty() && native.columns.ids.is_empty());
    assert!(float.codes.is_empty() && float.exponents.is_empty() && !float.fp32.is_empty());
    assert!(
        native.storage_bytes() < float.storage_bytes()
            && float.storage_bytes() < mixed.storage_bytes()
    );
    let x = vec![0.25; 33];
    let anchor = vec![0.; 33];
    assert_eq!(
        native.native(false, &x).unwrap(),
        mixed.native(false, &x).unwrap()
    );
    assert!(native.product(false, &x, &anchor, Format::Fp32).is_err());
    assert!(float.product(false, &x, &anchor, Format::Fp4x2).is_err());
}

#[test]
fn original_row_proof_can_bound_an_infinite_declared_direction() {
    let m = Model::from_json(br#"{"schema_version":1,"model_id":"implied",
        "variables":[{"id":7,"domain":"continuous","lower":{"kind":"finite","value":0},"upper":{"kind":"positive_infinity"}}],
        "constraints":[{"id":11,"lower":{"kind":"negative_infinity"},"upper":{"kind":"finite","value":3},"terms":[{"variable_id":7,"coefficient":1}]}],
        "objective":{"sense":"minimize","offset":0,"terms":[{"variable_id":7,"coefficient":-1}]}}"#).unwrap();
    let original = m.to_json().unwrap();
    let p = LinearProgram::new(&m).unwrap();
    let y = [-1. + 1e-12];
    assert!(optimizer_lp::certify(&p, &y).is_err());
    let context = lp_general_lowbit::implied::Context::new(&m, &p).unwrap();
    assert_eq!(context.proof.len(), 1);
    assert!(context.proof[0].value >= 3.);
    let certificate =
        lp_general_lowbit::solve::assess(&m, context.program(&p), &[3.], &y, 1e-9).unwrap();
    assert_eq!(certificate["accepted"], true);
    assert_eq!(original, m.to_json().unwrap());
    assert!(p.same_matrix_objective_rows(context.program(&p)));
}

#[test]
fn dual_repair_is_only_a_proposal_to_the_unchanged_checker() {
    let m = Model::from_json(br#"{"schema_version":1,"model_id":"dual-repair",
        "variables":[{"id":7,"domain":"continuous","lower":{"kind":"finite","value":0},"upper":{"kind":"positive_infinity"}},
                     {"id":8,"domain":"continuous","lower":{"kind":"finite","value":0},"upper":{"kind":"positive_infinity"}}],
        "constraints":[{"id":11,"lower":{"kind":"finite","value":0},"upper":{"kind":"finite","value":0},"terms":[{"variable_id":7,"coefficient":1},{"variable_id":8,"coefficient":-1}]}],
        "objective":{"sense":"minimize","offset":0,"terms":[{"variable_id":7,"coefficient":1},{"variable_id":8,"coefficient":-0.9}]}}"#).unwrap();
    let p = LinearProgram::new(&m).unwrap();
    let y = [1. + f64::EPSILON];
    assert!(optimizer_lp::certify(&p, &y).is_err());
    let (witness, corrections) = lp_general_lowbit::repair::propose(&p, &y).unwrap();
    assert_eq!(corrections, 1);
    assert!(optimizer_lp::certify(&p, &witness).is_ok());
    assert_eq!(
        lp_general_lowbit::solve::assess_repaired(&m, &p, &[0., 0.], &y, 1e-9).unwrap()["accepted"],
        true
    );
    assert!(lp_general_lowbit::repair::propose(&p, &[2.]).is_none());
}

#[test]
fn tensor_packing_stays_sparse_on_large_rectangles() {
    use lp_general_lowbit::tensor::{Config, Packed};
    let model = model(32769, 3);
    let p = LinearProgram::new(&model).unwrap();
    let e = Engine::new(&p, settings(Format::Native).lp());
    let op = Operator::new_for(&e, Format::Native).unwrap();
    let packed = Packed::new(&op, &Config::default()).unwrap();
    assert_eq!(packed.tile_count, 0);
    assert_eq!(packed.rows.residual.original.len(), p.nonzeros());
    assert_eq!(packed.columns.residual.original.len(), p.nonzeros());
    assert!(
        packed.storage_bytes() < 20 * (p.row_count() + p.column_count()) + 32 * p.nonzeros() + 256
    );
}
#[test]
fn tensor_transpose_must_bind_original_coefficient_bytes() {
    use lp_general_lowbit::tensor::{Config, Packed};
    let model = model(33, 17);
    let p = LinearProgram::new(&model).unwrap();
    let e = Engine::new(&p, settings(Format::Native).lp());
    let mut op = Operator::new_for(&e, Format::Native).unwrap();
    let config = Config {
        min_tile_nnz: 1,
        components: 4,
        control_interval: 32,
        incremental: true,
        compact_fragments: true,
        tensor_warps: 1,
    };
    let packed = Packed::new(&op, &config).unwrap();
    assert_eq!(
        packed
            .rows
            .covered
            .iter()
            .map(|v| *v as usize)
            .sum::<usize>(),
        p.nonzeros()
    );
    op.columns.original[0] = op.columns.original[0].next_up();
    assert!(Packed::new(&op, &config).is_err());
}

#[test]
fn proposal_packing_preserves_both_representations_without_unused_bounds() {
    use lp_general_lowbit::tensor::{Config, Packed};
    let model = model(65, 33);
    let p = LinearProgram::new(&model).unwrap();
    let e = Engine::new(&p, settings(Format::Native).lp());
    let op = Operator::new_for(&e, Format::Native).unwrap();
    for components in 1..=4 {
        let config = Config {
            min_tile_nnz: 1,
            components,
            ..Config::default()
        };
        let bounded = Packed::new(&op, &config).unwrap();
        let proposal = Packed::proposal(&op, &config).unwrap();
        for (a, b) in [
            (&bounded.rows, &proposal.rows),
            (&bounded.columns, &proposal.columns),
        ] {
            assert!(b.metadata.is_empty());
            assert_eq!(a.fragments, b.fragments);
            assert_eq!(a.exponents, b.exponents);
            assert_eq!(a.offsets, b.offsets);
            assert_eq!(a.columns, b.columns);
            assert_eq!(a.covered, b.covered);
            assert_eq!(a.residual.indices, b.residual.indices);
            assert_eq!(a.residual.original, b.residual.original);
        }
        assert!(proposal.storage_bytes() < bounded.storage_bytes());
    }
}

#[test]
fn fast_proposals_validate_explicit_execution_domains() {
    use lp_general_lowbit::fast_device::Config;
    for lanes in [0, 1, 4, 8, 32] {
        assert!(
            Config {
                lanes,
                fused_encode: true,
                combined: false,
                adaptive_rows: true,
                host_reductions: false,
                host_preparation: false,
                host_certificates: false,
                auto_schedule: false
            }
            .validate()
            .is_ok()
        );
    }
    for lanes in [2, 16, 64, usize::MAX] {
        assert!(
            Config {
                lanes,
                fused_encode: false,
                combined: true,
                adaptive_rows: false,
                host_reductions: true,
                host_preparation: true,
                host_certificates: true,
                auto_schedule: true
            }
            .validate()
            .is_err()
        );
    }
    assert!(serde_json::from_str::<Config>(r#"{"unknown":true}"#).is_err());
}
#[test]
fn extended_fp4_components_are_exclusive_to_the_tensor_backend() {
    use lp_general_lowbit::tensor::Config;
    let model = model(5, 3);
    let p = LinearProgram::new(&model).unwrap();
    let e = Engine::new(&p, settings(Format::Native).lp());
    for format in [Format::Fp4x3, Format::Fp4x4] {
        assert!(Operator::new_for(&e, format).is_err());
    }
    for bad in [
        Config {
            min_tile_nnz: 0,
            ..Config::default()
        },
        Config {
            components: 5,
            ..Config::default()
        },
        Config {
            control_interval: 0,
            ..Config::default()
        },
    ] {
        assert!(bad.validate().is_err());
    }
}
