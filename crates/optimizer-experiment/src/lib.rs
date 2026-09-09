//! Versioned artifact contracts; runtime experiment execution is planned for M6.

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
pub const SOLVE_RECORD_SCHEMA: &str = include_str!("../../../schemas/solve-record-v1.schema.json");
