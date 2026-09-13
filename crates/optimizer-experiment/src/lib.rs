//! Versioned artifact contracts and provenance-bearing run records.
//!
//! The embedded JSON Schemas are the bootstrap artifact contract under
//! SPEC-0007. [`RunRecord`] is the C4 run surface's own document under
//! SPEC-0005: one search record plus the provenance needed to repeat it, and the
//! comparison that decides whether a repeat agreed.
//!
//! Comparative experiment execution over a benchmark manifest is not
//! implemented here; this crate records single runs.

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
