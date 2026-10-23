//! Source-only strict Tensor JSON shape counterexamples.
#![cfg(feature = "precision-research")]
use optimizer_experiment::lp_tensor_residual::{Evidence, Request};
#[test]
fn tensor_json_rejects_missing_unknown_duplicate_and_alias_fields() {
    let bytes = include_bytes!("../../../tests/fixtures/lp-tensor-residual-evidence-v1.json");
    let original: serde_json::Value = serde_json::from_slice(bytes).unwrap();
    Evidence::from_json(bytes).unwrap();
    for key in original.as_object().unwrap().keys() {
        let mut bad = original.clone();
        bad.as_object_mut().unwrap().remove(key);
        assert!(
            Evidence::from_json(&serde_json::to_vec(&bad).unwrap()).is_err(),
            "{key}"
        );
    }
    let mut bad = original.clone();
    bad["outcome"]["counts"]["unexpected"] = serde_json::json!(1);
    assert!(Evidence::from_json(&serde_json::to_vec(&bad).unwrap()).is_err());
    let request = serde_json::to_vec(&original["request"]).unwrap();
    Request::from_json(&request).unwrap();
    let text = String::from_utf8(request).unwrap();
    let duplicate = text.replacen('{', "{\"schema_version\":1,", 1);
    assert!(Request::from_json(duplicate.as_bytes()).is_err());
    let mut bad = original["request"].clone();
    bad["settings"]["primal_budget"] = serde_json::json!(1e-6);
    assert!(Request::from_json(&serde_json::to_vec(&bad).unwrap()).is_err());
}
