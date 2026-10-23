//! Versioned artifact contracts and provenance-bearing run records.
//!
//! The embedded JSON Schemas are the bootstrap artifact contract under
//! SPEC-0007. [`RunRecord`] is the C4 run surface's own document under
//! SPEC-0005: one search record plus the provenance needed to repeat it, and the
//! comparison that decides whether a repeat agreed.
//!
//! Comparative experiment execution over a benchmark manifest is not
//! implemented here; this crate records single runs.

pub mod lp;
pub mod lp_batch;
pub mod lp_compact;
mod run;
mod serde_strict;
pub mod sha256;

pub use run::{
    EXAMPLE_REVISION, EnvironmentDifference, ExtensionDifference, Hardware, InputDocument,
    InputRole, RUN_SCHEMA_VERSION, RunRecord, Toolchain,
};

/// JSON Schema for benchmark manifests, version 1.
pub const MANIFEST_SCHEMA: &str =
    include_str!("../../../schemas/benchmark-manifest-v1.schema.json");

/// JSON Schema for reproducible result records, version 1.
pub const RESULT_SCHEMA: &str = include_str!("../../../schemas/experiment-result-v1.schema.json");

/// JSON Schema for explicit resource configuration, version 1.
pub const CONFIG_SCHEMA: &str = include_str!("../../../schemas/run-config-v1.schema.json");

/// JSON Schema for explicit solve configuration, version 1.
pub const SOLVE_CONFIG_SCHEMA: &str = include_str!("../../../schemas/solve-config-v1.schema.json");

/// JSON Schema for reproducible solve records, version 1.
pub const SOLVE_RECORD_SCHEMA: &str = include_str!("../../../schemas/solve-record-v2.schema.json");

/// JSON Schema for reproducible run records, version 1.
pub const RUN_RECORD_SCHEMA: &str = include_str!("../../../schemas/run-record-v2.schema.json");

/// JSON Schema for embedded search records, version 2.
pub const SEARCH_RECORD_SCHEMA: &str =
    include_str!("../../../schemas/search-record-v3.schema.json");

/// Independently checked external LP study witnesses.
pub mod lp_external;

/// Strict isolated GPUP-5B study evidence; no runtime selector.
#[cfg(feature = "precision-research")]
pub mod lp_research;

/// Explicit-method COPT study evidence, version two.
pub mod lp_external_v2;

/// ADR-0035 isolated exact-product research evidence.
#[cfg(feature = "precision-research")]
pub mod lp_exec;

/// ADR-0037 original-residual refinement study.
#[cfg(feature = "precision-research")]
pub mod lp_refine;

/// ADR-0039 assessment scheduling study.
#[cfg(feature = "precision-research")]
pub mod lp_assess;

/// ADR-0040 strict quantized study evidence.
#[cfg(feature = "precision-research")]
pub mod lp_quant;

/// ADR-0041 strict resident quantization research evidence.
#[cfg(feature = "precision-research")]
pub mod lp_quant_resident;

/// ADR-0041 product/guard diagnostics, without LP certificate authority.
#[cfg(feature = "precision-research")]
pub mod lp_quant_resident_micro;

/// ADR-0042 isolated hybrid Tensor Core research.
#[cfg(feature = "precision-research")]
pub mod lp_tensor;
