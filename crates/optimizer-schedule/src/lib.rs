//! Flow-shop scheduling under SPEC-0008 and ADR-0007.
//!
//! The contract is accepted and no behavior is implemented yet. The slice it
//! specifies is a permutation flow shop: a versioned instance document, a
//! makespan recurrence that is the sole authority on what a schedule costs, a
//! positional encoding into an `optimizer-core` model, and deterministic
//! NEH and insertion candidate producers registered through the C3 extension
//! runtime.
//!
//! The reason the recurrence is separate from everything that proposes a schedule
//! is that it is the only independent check available: two computations sharing an
//! implementation agree by construction, and their agreement establishes nothing.
//!
//! Nothing here claims tractability. The positional encoding is correct by
//! construction and its linear relaxation is weak, so proven-optimal claims belong
//! to tiny instances checked against exhaustive permutation enumeration, and the
//! frozen development subset carries feasibility and determinism evidence only.
