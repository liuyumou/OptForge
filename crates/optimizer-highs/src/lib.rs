//! Safe, pinned CPU HiGHS 1.11.0 backend under SPEC-0002 and ADR-0003.
//!
//! This crate owns the only native boundary in the workspace. Raw handles stay
//! private, are destroyed exactly once, and never cross the public API. Native
//! termination is numerical evidence recorded under explicit settings: it is not
//! an exact-arithmetic certificate, and every published incumbent is
//! re-validated against the original model by [`optimizer_core`].
//!
//! When the pinned library is not provisioned the same API compiles and reports
//! an explicit unsupported backend, so a missing native build can never be
//! mistaken for a solved model.

mod ffi;

#[cfg(highs_native)]
mod native;

use optimizer_core::{
    Arithmetic, Backend, BackendCapabilities, Basis, CancellationToken, DeviceClass, Model,
    ProblemClass, SolveOptions, SolveRecord, ValidationError, WarmStart,
};

/// Backend identifier recorded in every solve record.
pub const BACKEND_NAME: &str = "highs";

/// The pinned HiGHS release this adapter is written against.
pub const PINNED_VERSION: &str = "1.11.0";

/// Version recorded when this build linked no native library.
///
/// A record must not name a library version it never called. Writing
/// [`PINNED_VERSION`] here would let a build with no pinned library produce a
/// record indistinguishable from one that solved against the real thing.
pub const UNAVAILABLE_VERSION: &str = "unavailable";

/// Whether this build linked the pinned native library.
pub const fn is_native() -> bool {
    cfg!(highs_native)
}

/// CPU HiGHS backend adapter.
///
/// The adapter holds no shared mutable state; each solve creates and destroys
/// its own native instance.
#[derive(Clone, Debug, Default)]
pub struct HighsBackend;

impl HighsBackend {
    /// Construct an adapter with no shared mutable state.
    pub fn new() -> Self {
        Self
    }

    /// Native library version, when this build linked it.
    pub fn version(&self) -> Option<String> {
        #[cfg(highs_native)]
        {
            Some(native::version())
        }
        #[cfg(not(highs_native))]
        {
            None
        }
    }

    /// Solve and also return the final LP basis when the backend produced one.
    ///
    /// [`Backend::solve`] stays object-safe and basis-free; callers that want to
    /// warm start a later solve use this instead. A basis is never returned for
    /// a discrete model.
    pub fn solve_with_basis(
        &self,
        model: &Model,
        options: &SolveOptions,
        cancel: &CancellationToken,
        warm_start: Option<WarmStart<'_>>,
    ) -> Result<(SolveRecord, Option<Basis>), ValidationError> {
        self.dispatch(model, options, cancel, warm_start, true)
    }

    /// Shared body of both entry points.
    ///
    /// `want_basis` decides only whether the final basis is extracted. Every
    /// other step, including the pre-cancellation short circuit and the
    /// unprovisioned-library refusal, is common, so the two entry points cannot
    /// drift apart in anything but the basis.
    fn dispatch(
        &self,
        model: &Model,
        options: &SolveOptions,
        cancel: &CancellationToken,
        warm_start: Option<WarmStart<'_>>,
        want_basis: bool,
    ) -> Result<(SolveRecord, Option<Basis>), ValidationError> {
        let options = options.validate()?;

        // A pre-cancelled solve performs no native work by definition, so it is
        // answered identically whether or not the library is provisioned.
        if cancel.is_cancelled() {
            return Ok((interrupted_record(model, &options), None));
        }

        #[cfg(highs_native)]
        {
            let request = if want_basis {
                native::BasisRequest::Extract
            } else {
                native::BasisRequest::Skip
            };
            native::solve(model, &options, cancel, warm_start, request)
        }
        #[cfg(not(highs_native))]
        {
            let _ = (warm_start, want_basis);
            Err(ValidationError::new(
                optimizer_core::ErrorKind::Unsupported,
                "HiGHS native library is not provisioned; run bash tools/setup_highs.sh",
            ))
        }
    }
}

/// Record for a solve cancelled before any native work began.
///
/// This path is reachable without the pinned library, so the recorded version is
/// the adapter's own report rather than the pinned constant: a record produced by
/// a build that linked nothing must not claim the version it was written against.
fn interrupted_record(model: &Model, options: &SolveOptions) -> SolveRecord {
    SolveRecord {
        schema_version: optimizer_core::SOLVE_SCHEMA_VERSION,
        model_id: model.document().model_id.clone(),
        backend: BACKEND_NAME.to_string(),
        backend_version: HighsBackend::new()
            .version()
            .unwrap_or_else(|| UNAVAILABLE_VERSION.to_string()),
        termination: optimizer_core::Termination::Interrupted,
        native_status: None,
        objective: None,
        best_bound: None,
        gap: None,
        candidate: None,
        validation: None,
        warnings: Vec::new(),
        elapsed_ms: 0,
        options: options.clone(),
    }
}

impl Backend for HighsBackend {
    fn capabilities(&self) -> BackendCapabilities {
        // The version reported is the one this build actually linked, never the
        // pinned constant: a declaration naming 1.11.0 on a build that linked
        // nothing would claim a library it may never call. This is the same rule
        // UNAVAILABLE_VERSION exists to enforce in a record.
        let version = self
            .version()
            .unwrap_or_else(|| UNAVAILABLE_VERSION.to_string());
        BackendCapabilities::declare(
            BACKEND_NAME,
            version,
            vec![ProblemClass::Continuous, ProblemClass::Discrete],
            Arithmetic::F64,
            true,
            DeviceClass::Cpu,
        )
        .expect("the pinned adapter's declaration is a constant and is well formed")
    }

    fn solve(
        &self,
        model: &Model,
        options: &SolveOptions,
        cancel: &CancellationToken,
        warm_start: Option<WarmStart<'_>>,
    ) -> Result<SolveRecord, ValidationError> {
        // No basis is extracted here. This method's caller cannot receive one, so
        // computing it would serialize the whole model on every branch-and-bound
        // node to build a value discarded on the next line.
        self.dispatch(model, options, cancel, warm_start, false)
            .map(|(record, _)| record)
    }
}
