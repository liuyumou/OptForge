//! Local extension registry and conformance under SPEC-0009 and ADR-0008.
//!
//! [C3](../optimizer_extension/index.html) established what an extension may
//! propose and what the core refuses, but registration was an in-memory slice
//! valid for one search, so nothing outside Rust test code could build one. The
//! consequence was visible in two places: the
//! [C4 run surface](../optimizer_experiment/index.html) refused any configuration
//! naming an extension, and a C5 scheduling run performed with a producer could
//! not be verified by re-execution at all. This crate is the seam both refusals
//! pointed at.
//!
//! A registry entry is a **claim** about an extension, never a grant. Resolution
//! checks every recorded field against what the extension itself declares and
//! refuses a mismatch in either direction, because reconciling would mean
//! preferring one untrusted statement over another. Authority stays derived from
//! the category by [`optimizer_extension::Category::authority`], so an entry
//! recording an authority is stating a checkable fact rather than choosing a
//! privilege.
//!
//! Resolution is all-or-nothing and happens before a search starts. A search
//! never begins with a subset of the extensions its configuration named, because
//! the resulting record would describe a search the caller did not request.
//!
//! The registry **resolves**; it does not **load**. An entry names an extension
//! this build already provides, through the caller-owned [`Provider`] seam, the
//! same way [`optimizer_core::Backend`] keeps numerical backends replaceable
//! without naming one. Dynamic loading of separately distributed native
//! components needs a second unsafe boundary ADR-0003 prohibits outside
//! optimizer-highs, so a registry deliberately cannot name one. That makes the
//! deferral more visible rather than closing it.
//!
//! Nothing here measures anything. Promotion means the
//! [conformance suite](conformance) passed, which is a statement about contracts;
//! whether a registered extension improves a search is a C7 question and
//! SPEC-0009 requirement 27 forbids recording an answer to it here.

pub mod conformance;
mod document;
mod resolve;
mod serde_strict;

pub use conformance::{
    CONFORMANCE_SCHEMA_VERSION, ConformanceCheck, ConformanceRecord, GRID_SIZE, MAX_DETAIL_BYTES,
};
pub use document::{
    DataRequirement, HardwareRequirement, MAX_LICENSE_BYTES, Promotion, REGISTRY_SCHEMA_VERSION,
    RegistryDocument, RegistryEntry,
};
pub use resolve::{
    ConformanceSource, NoConformance, Options, Provided, Provider, ProviderContext, ResolvedSet,
    resolve, resolve_with,
};
