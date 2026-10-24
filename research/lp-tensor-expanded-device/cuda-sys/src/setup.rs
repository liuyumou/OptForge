//! Scoped setup observations for SPEC-0018. Observation never selects policy.
use serde::{Deserialize, Serialize};
use std::cell::RefCell;
use std::marker::PhantomData;
use std::rc::Rc;

/// Explicit experimental study context policy.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum ContextMode {
    /// Historical owned user context.
    #[default]
    User,
    /// One fresh primary-context retain/release, without persistence.
    PrimaryExperimental,
}
impl ContextMode {
    /// Stable request value.
    #[must_use]
    pub fn as_str(self) -> &'static str {
        match self {
            Self::User => "user",
            Self::PrimaryExperimental => "primary-experimental",
        }
    }
    pub(crate) fn creation_event(self) -> &'static str {
        match self {
            Self::User => "context_create_user",
            Self::PrimaryExperimental => "context_retain_primary",
        }
    }
}
/// One checked lifecycle operation, never a mathematical claim.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SetupEvent {
    /// Operation name.
    pub operation: String,
    /// Whether the operation succeeded.
    pub ok: bool,
    /// Observed identity, state or driver status.
    pub detail: String,
}
thread_local! { static EVENTS: RefCell<Option<Vec<SetupEvent>>> = const { RefCell::new(None) }; }
/// An explicitly enabled observation on one thread, including ordinary unwinding.
pub struct SetupObservation(PhantomData<Rc<()>>);
impl SetupObservation {
    /// Begin one observation; nested observation is refused.
    /// # Errors
    /// Returns an error when another observer is active on this thread.
    pub fn begin() -> Result<Self, &'static str> {
        EVENTS.with(|slot| {
            let mut slot = slot.borrow_mut();
            if slot.is_some() {
                return Err("setup observation already active");
            }
            *slot = Some(Vec::new());
            Ok(Self(PhantomData))
        })
    }
    /// Finish after all context resources have dropped.
    #[must_use]
    pub fn finish(self) -> Vec<SetupEvent> {
        EVENTS.with(|slot| slot.borrow_mut().take().expect("owned observer"))
    }
}
impl Drop for SetupObservation {
    fn drop(&mut self) {
        EVENTS.with(|slot| {
            slot.borrow_mut().take();
        });
    }
}
pub(crate) fn event(operation: &str, ok: bool, detail: &str) {
    EVENTS.with(|slot| {
        if let Some(events) = slot.borrow_mut().as_mut() {
            if events.len() >= 4095 {
                if events.len() == 4095 {
                    events.push(SetupEvent {
                        operation: "observation_capacity".into(),
                        ok: false,
                        detail: "partial observation".into(),
                    });
                }
                return;
            }
            events.push(SetupEvent {
                operation: operation.into(),
                ok,
                detail: detail.into(),
            });
        }
    });
}
/// Require one completed lifecycle with no failed checks.
#[must_use]
pub fn complete(mode: ContextMode, events: &[SetupEvent]) -> bool {
    let lifecycle: Vec<&str> = events
        .iter()
        .filter(|e| {
            !matches!(
                e.operation.as_str(),
                "module_unload" | "stream_destroy" | "memory_free"
            )
        })
        .map(|e| e.operation.as_str())
        .collect();
    let expected: &[&str] = match mode {
        ContextMode::User => &["context_create_user", "context_destroy_user"],
        ContextMode::PrimaryExperimental => &[
            "current_context_empty",
            "primary_inactive",
            "primary_flags",
            "primary_make_current",
            "primary_uuid_check",
            "context_retain_primary",
            "primary_detach",
            "context_release_primary",
            "primary_inactive_after_release",
        ],
    };
    !events.is_empty()
        && events.iter().all(|e| e.ok)
        && lifecycle == expected
        && events
            .last()
            .is_some_and(|e| e.operation == *expected.last().expect("nonempty"))
}
pub(crate) fn status_event(operation: &str, status: i32) {
    EVENTS.with(|slot| {
        if let Some(events) = slot.borrow_mut().as_mut() {
            if events.len() >= 4095 {
                if events.len() == 4095 {
                    events.push(SetupEvent {
                        operation: "observation_capacity".into(),
                        ok: false,
                        detail: "partial observation".into(),
                    });
                }
                return;
            }
            events.push(SetupEvent {
                operation: operation.into(),
                ok: status == 0,
                detail: status.to_string(),
            });
        }
    });
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn disabled_nested_and_failed_observations() {
        event("ignored", false, "");
        let observer = SetupObservation::begin().unwrap();
        assert!(SetupObservation::begin().is_err());
        event("context_create_user", true, "GPU-test");
        event("context_destroy_user", true, "0");
        let mut events = observer.finish();
        assert!(complete(ContextMode::User, &events));
        assert!(!complete(ContextMode::PrimaryExperimental, &events));
        events[1].ok = false;
        assert!(!complete(ContextMode::User, &events));
        assert!(SetupObservation::begin().unwrap().finish().is_empty());
    }
}
