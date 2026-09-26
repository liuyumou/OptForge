//! Opt-in, thread-local hierarchical host wall costs for development studies.
//!
//! Disabled scopes read no clock and allocate nothing. A study owns one session
//! on its solving thread; device activity and worker-process wall time remain
//! separate observations. These timings never affect mathematical authority.
use serde::Serialize;
use std::cell::RefCell;
use std::collections::BTreeMap;
use std::marker::PhantomData;
use std::rc::Rc;
use std::time::Instant;

thread_local! {
    static STATE: RefCell<Option<State>> = const { RefCell::new(None) };
}

#[derive(Debug)]
struct Frame {
    path: Vec<String>,
    started: Instant,
    children: u64,
}
struct State {
    origin: Instant,
    stack: Vec<Frame>,
    rows: BTreeMap<Vec<String>, CostScope>,
    counters: BTreeMap<String, u64>,
    unavailable: Vec<String>,
}
/// One aggregated scope; paths distinguish the same operation in different parents.
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct CostScope {
    /// Outermost to innermost scope names.
    pub path: Vec<String>,
    /// Completed invocations.
    pub calls: u64,
    /// Wall time including nested scopes.
    pub inclusive_ns: u64,
    /// Wall time after subtracting nested scopes on this thread.
    pub exclusive_ns: u64,
    /// Smallest completed inclusive observation.
    pub min_ns: u64,
    /// Largest completed inclusive observation.
    pub max_ns: u64,
}
/// Raw process-local observation; the study binds it to requests and endpoints.
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct CostProfile {
    /// One; independent of solve and endpoint versions.
    pub schema_version: u32,
    /// Monotonic wall time on one host solving thread.
    pub clock: String,
    /// Session envelope, excluding its own final serialization.
    pub elapsed_ns: u64,
    /// Disjoint exclusive costs sum to at most the session envelope.
    pub scopes: Vec<CostScope>,
    /// Explicit work/byte counters; names state units.
    pub counters: BTreeMap<String, u64>,
    /// Incomplete observations or attribution limitations.
    pub unavailable: Vec<String>,
}
/// Owning session. Neither sessions nor scopes can move to another thread.
pub struct Session(PhantomData<Rc<()>>);
/// Stack scope closed on ordinary returns and unwinding.
pub struct Scope {
    depth: Option<(usize, Instant)>,
    _thread: PhantomData<Rc<()>>,
}
fn nanos(value: std::time::Duration) -> u64 {
    u64::try_from(value.as_nanos()).unwrap_or(u64::MAX)
}
impl Session {
    /// Start an explicit study observation; nested sessions are rejected.
    pub fn begin() -> Result<Self, &'static str> {
        STATE.with(|cell| {
            let mut slot = cell.borrow_mut();
            if slot.is_some() {
                return Err("component profiling session already active");
            }
            *slot = Some(State {
                origin: Instant::now(),
                stack: Vec::new(),
                rows: BTreeMap::new(),
                counters: BTreeMap::new(),
                unavailable: Vec::new(),
            });
            Ok(Self(PhantomData))
        })
    }
    /// End after all scopes have returned; unresolved scopes are explicitly partial.
    #[must_use]
    pub fn finish(self) -> CostProfile {
        STATE.with(|cell| {
            let mut state = cell.borrow_mut().take().expect("owned profiling session");
            if !state.stack.is_empty() {
                state
                    .unavailable
                    .push("unclosed scopes: partial host attribution".into());
            }
            CostProfile {
                schema_version: 1,
                clock: "monotonic_host_thread".into(),
                elapsed_ns: nanos(state.origin.elapsed()),
                scopes: state.rows.into_values().collect(),
                counters: state.counters,
                unavailable: state.unavailable,
            }
        })
    }
}
impl Drop for Session {
    fn drop(&mut self) {
        STATE.with(|cell| {
            cell.borrow_mut().take();
        });
    }
}
/// Enter a named scope only when the study explicitly enabled collection.
#[must_use]
pub fn scope(name: &str) -> Scope {
    let depth = STATE.with(|cell| {
        let mut slot = cell.borrow_mut();
        let state = slot.as_mut()?;
        if state.stack.len() >= 64 || state.rows.len() >= 4096 {
            if !state
                .unavailable
                .iter()
                .any(|v| v == "scope capacity exceeded")
            {
                state.unavailable.push("scope capacity exceeded".into());
            }
            return None;
        }
        let mut path = state.stack.last().map_or_else(Vec::new, |f| f.path.clone());
        path.push(name.into());
        state.stack.push(Frame {
            path,
            started: Instant::now(),
            children: 0,
        });
        Some((state.stack.len(), state.origin))
    });
    Scope {
        depth,
        _thread: PhantomData,
    }
}
impl Drop for Scope {
    fn drop(&mut self) {
        let Some((depth, origin)) = self.depth else {
            return;
        };
        STATE.with(|cell| {
            let mut slot = cell.borrow_mut();
            let Some(state) = slot.as_mut() else {
                return;
            };
            if state.origin != origin {
                return;
            }
            if state.stack.len() != depth {
                state
                    .unavailable
                    .push("scope closed out of stack order".into());
                return;
            }
            let frame = state.stack.pop().expect("checked scope depth");
            let inclusive = nanos(frame.started.elapsed());
            let exclusive = inclusive.saturating_sub(frame.children);
            if let Some(parent) = state.stack.last_mut() {
                parent.children = parent.children.saturating_add(inclusive);
            }
            let row = state.rows.entry(frame.path.clone()).or_insert(CostScope {
                path: frame.path,
                calls: 0,
                inclusive_ns: 0,
                exclusive_ns: 0,
                min_ns: u64::MAX,
                max_ns: 0,
            });
            row.calls += 1;
            row.inclusive_ns = row.inclusive_ns.saturating_add(inclusive);
            row.exclusive_ns = row.exclusive_ns.saturating_add(exclusive);
            row.min_ns = row.min_ns.min(inclusive);
            row.max_ns = row.max_ns.max(inclusive);
        });
    }
}
/// Accumulate an explicitly named unit only in an active session.
pub fn count(name: &str, value: u64) {
    STATE.with(|cell| {
        if let Some(state) = cell.borrow_mut().as_mut() {
            let entry = state.counters.entry(name.into()).or_default();
            *entry = entry.saturating_add(value);
        }
    });
}
/// Enter a bounded indexed category, for example one adaptive ladder rung.
#[must_use]
pub fn indexed_scope(name: &str, index: usize) -> Scope {
    if STATE.with(|cell| cell.borrow().is_some()) {
        scope(&format!("{name}_{index}"))
    } else {
        Scope {
            depth: None,
            _thread: PhantomData,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn nested_costs_reconcile_and_disabled_scopes_are_empty() {
        drop(scope("disabled"));
        let session = Session::begin().unwrap();
        assert!(Session::begin().is_err());
        {
            let _parent = scope("parent");
            for _ in 0..3 {
                let _child = scope("child");
                count("items", 2);
            }
        }
        let p = session.finish();
        let parent = p.scopes.iter().find(|v| v.path.len() == 1).unwrap();
        let child = p.scopes.iter().find(|v| v.path.len() == 2).unwrap();
        assert_eq!(child.calls, 3);
        assert_eq!(
            parent.inclusive_ns,
            parent.exclusive_ns + child.inclusive_ns
        );
        assert!(p.scopes.iter().map(|v| v.exclusive_ns).sum::<u64>() <= p.elapsed_ns);
        assert_eq!(p.counters["items"], 6);
        assert!(p.unavailable.is_empty());
    }
    #[test]
    fn unwinding_closes_scopes_and_incomplete_collection_is_explicit() {
        let session = Session::begin().unwrap();
        let _ = std::panic::catch_unwind(|| {
            let _s = scope("failed");
            panic!("fixture");
        });
        assert_eq!(session.finish().scopes[0].calls, 1);
        let session = Session::begin().unwrap();
        let guard = scope("incomplete");
        assert!(!session.finish().unavailable.is_empty());
        drop(guard);
    }
}
