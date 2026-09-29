//! Optional primary-context lifecycle. All foreign calls stay in this boundary.
use crate::{CuContext, CuDevice, DeviceError, Driver, Result, check, setup, symbol};
use std::ffi::{c_int, c_uint};
use std::ptr;
use std::sync::OnceLock;

struct Api {
    current: unsafe extern "C" fn(*mut CuContext) -> c_int,
    state: unsafe extern "C" fn(CuDevice, *mut c_uint, *mut c_int) -> c_int,
    flags: unsafe extern "C" fn(CuDevice, c_uint) -> c_int,
    retain: unsafe extern "C" fn(*mut CuContext, CuDevice) -> c_int,
    release: unsafe extern "C" fn(CuDevice) -> c_int,
}
static API: OnceLock<Result<Api>> = OnceLock::new();
const SYMBOLS: [&str; 5] = [
    "cuCtxGetCurrent",
    "cuDevicePrimaryCtxGetState",
    "cuDevicePrimaryCtxSetFlags_v2",
    "cuDevicePrimaryCtxRetain",
    "cuDevicePrimaryCtxRelease_v2",
];
fn required_symbols(mut resolve: impl FnMut(&'static str) -> Result<()>) -> Result<()> {
    for name in SYMBOLS {
        resolve(name)?;
    }
    Ok(())
}
fn api(driver: &Driver) -> Result<&'static Api> {
    API.get_or_init(|| {
        let _cost = optimizer_core::lp_cost::scope("primary_symbol_resolution");
        // Validate all optional exports before retaining any resource. Their absence
        // never affects the historical driver table or user-context path.
        required_symbols(|name| {
            let c_name = std::ffi::CString::new(name).expect("literal symbol");
            // SAFETY: live driver handle, NUL-terminated name; pointer not invoked.
            if unsafe { libc::dlsym(driver._handle, c_name.as_ptr()) }.is_null() {
                Err(DeviceError::SymbolMissing(name))
            } else {
                Ok(())
            }
        })?;
        // SAFETY: CUDA 13.0 headers specify these exact signatures and versioned
        // aliases; the driver handle remains loaded for the process lifetime.
        unsafe {
            Ok(Api {
                current: symbol(driver._handle, "cuCtxGetCurrent\0")?,
                state: symbol(driver._handle, "cuDevicePrimaryCtxGetState\0")?,
                flags: symbol(driver._handle, "cuDevicePrimaryCtxSetFlags_v2\0")?,
                retain: symbol(driver._handle, "cuDevicePrimaryCtxRetain\0")?,
                release: symbol(driver._handle, "cuDevicePrimaryCtxRelease_v2\0")?,
            })
        }
    })
    .as_ref()
    .map_err(Clone::clone)
}
trait Calls {
    fn current(&self) -> Result<CuContext>;
    fn state(&self, device: CuDevice) -> Result<(u32, bool)>;
    fn flags(&self, device: CuDevice) -> Result<()>;
    fn retain(&self, device: CuDevice) -> Result<CuContext>;
    fn set_current(&self, raw: CuContext) -> Result<()>;
    fn uuid(&self, device: CuDevice) -> Result<String>;
    fn release(&self, device: CuDevice) -> Result<()>;
}
struct Native<'a> {
    driver: &'a Driver,
    api: &'a Api,
    ordinal: c_int,
}
impl Calls for Native<'_> {
    fn current(&self) -> Result<CuContext> {
        let mut raw = ptr::null_mut();
        // SAFETY: live output slot and resolved ABI.
        check(self.driver, "cuCtxGetCurrent", unsafe {
            (self.api.current)(&mut raw)
        })?;
        Ok(raw)
    }
    fn state(&self, device: CuDevice) -> Result<(u32, bool)> {
        let mut flags = 0;
        let mut active = 0;
        // SAFETY: driver-selected device and live output slots.
        check(self.driver, "cuDevicePrimaryCtxGetState", unsafe {
            (self.api.state)(device, &mut flags, &mut active)
        })?;
        Ok((flags, active != 0))
    }
    fn flags(&self, device: CuDevice) -> Result<()> {
        // SAFETY: driver-selected inactive primary context; zero preserves AUTO.
        check(self.driver, "cuDevicePrimaryCtxSetFlags_v2", unsafe {
            (self.api.flags)(device, 0)
        })
    }
    fn retain(&self, device: CuDevice) -> Result<CuContext> {
        let mut raw = ptr::null_mut();
        // SAFETY: live output slot and driver-selected device.
        check(self.driver, "cuDevicePrimaryCtxRetain", unsafe {
            (self.api.retain)(&mut raw, device)
        })?;
        Ok(raw)
    }
    fn set_current(&self, raw: CuContext) -> Result<()> {
        // SAFETY: a retained live context or null to detach this thread.
        check(self.driver, "cuCtxSetCurrent", unsafe {
            (self.driver.context_set_current)(raw)
        })
    }
    fn uuid(&self, device: CuDevice) -> Result<String> {
        Ok(crate::describe(self.driver, device, self.ordinal)?.uuid)
    }
    fn release(&self, device: CuDevice) -> Result<()> {
        // SAFETY: exactly one successful retain belongs to the calling guard.
        check(self.driver, "cuDevicePrimaryCtxRelease_v2", unsafe {
            (self.api.release)(device)
        })
    }
}
fn observed<T>(name: &str, result: Result<T>, detail: &str) -> Result<T> {
    match &result {
        Ok(_) => setup::event(name, true, detail),
        Err(error) => setup::event(name, false, &error.to_string()),
    }
    result
}
fn refusal(message: &str) -> DeviceError {
    DeviceError::Unsupported(message.into())
}
struct Retained<'a, C: Calls> {
    calls: &'a C,
    device: CuDevice,
    raw: CuContext,
    armed: bool,
}
impl<C: Calls> Drop for Retained<'_, C> {
    fn drop(&mut self) {
        if self.armed {
            cleanup(self.calls, self.device, self.raw);
        }
    }
}
fn cleanup(calls: &impl Calls, device: CuDevice, raw: CuContext) {
    let detach = optimizer_core::lp_cost::scope("primary_detach_api");
    let result = calls.current().and_then(|current| {
        if current.is_null() || current == raw {
            calls.set_current(ptr::null_mut())
        } else {
            Err(refusal(
                "another context became current before primary cleanup",
            ))
        }
    });
    let _ = observed("primary_detach", result, "current context detached");
    drop(detach);
    let release = optimizer_core::lp_cost::scope("primary_release_api");
    // Attempt release once even after failed detach; never reset or retry it.
    let _ = observed(
        "context_release_primary",
        calls.release(device),
        "one retained reference released",
    );
    drop(release);
    let _cost = optimizer_core::lp_cost::scope("primary_cleanup_check");
    let inactive = calls.state(device).and_then(|(_, active)| {
        if active {
            Err(refusal("primary context remains active after release"))
        } else {
            Ok(())
        }
    });
    let _ = observed("primary_inactive_after_release", inactive, "inactive");
}
fn acquire(calls: &impl Calls, device: CuDevice, uuid: &str) -> Result<CuContext> {
    let preconditions = optimizer_core::lp_cost::scope("primary_preconditions");
    observed(
        "current_context_empty",
        calls.current().and_then(|raw| {
            if raw.is_null() {
                Ok(())
            } else {
                Err(refusal("primary study requires no current context"))
            }
        }),
        "empty",
    )?;
    observed(
        "primary_inactive",
        calls.state(device).and_then(|(_, active)| {
            if active {
                Err(refusal("primary study refuses an active primary context"))
            } else {
                Ok(())
            }
        }),
        "inactive",
    )?;
    observed("primary_flags", calls.flags(device), "0 (AUTO)")?;
    drop(preconditions);
    let retain = optimizer_core::lp_cost::scope("primary_retain_api");
    let raw = calls.retain(device)?;
    let mut guard = Retained {
        calls,
        device,
        raw,
        armed: true,
    };
    drop(retain);
    let current = optimizer_core::lp_cost::scope("primary_make_current");
    observed(
        "primary_make_current",
        calls.set_current(raw),
        "retained context current",
    )?;
    drop(current);
    let identity = optimizer_core::lp_cost::scope("context_identity_check");
    let found = calls.uuid(device)?;
    observed(
        "primary_uuid_check",
        if found == uuid {
            Ok(())
        } else {
            Err(DeviceError::DeviceMismatch {
                requested: uuid.into(),
                found: found.clone(),
            })
        },
        &found,
    )?;
    drop(identity);
    guard.armed = false;
    Ok(raw)
}
pub(crate) fn create(
    driver: &Driver,
    device: CuDevice,
    ordinal: c_int,
    uuid: &str,
) -> Result<CuContext> {
    acquire(
        &Native {
            driver,
            api: api(driver)?,
            ordinal,
        },
        device,
        uuid,
    )
}
pub(crate) fn destroy(driver: &Driver, device: CuDevice, raw: CuContext) {
    match api(driver) {
        Ok(api) => cleanup(
            &Native {
                driver,
                api,
                ordinal: 0,
            },
            device,
            raw,
        ),
        Err(error) => setup::event("context_release_primary", false, &error.to_string()),
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    use std::cell::{Cell, RefCell};
    struct Fake {
        fail: &'static str,
        active: Cell<bool>,
        current: Cell<CuContext>,
        events: RefCell<Vec<&'static str>>,
    }
    impl Fake {
        fn new(fail: &'static str) -> Self {
            Self {
                fail,
                active: Cell::new(false),
                current: Cell::new(ptr::null_mut()),
                events: RefCell::new(vec![]),
            }
        }
        fn call(&self, name: &'static str) -> Result<()> {
            self.events.borrow_mut().push(name);
            if self.fail == name {
                Err(refusal(name))
            } else {
                Ok(())
            }
        }
    }
    fn handle() -> CuContext {
        ptr::without_provenance_mut(1)
    }
    impl Calls for Fake {
        fn current(&self) -> Result<CuContext> {
            self.call("current")?;
            Ok(self.current.get())
        }
        fn state(&self, _: CuDevice) -> Result<(u32, bool)> {
            self.call("state")?;
            Ok((0, self.active.get()))
        }
        fn flags(&self, _: CuDevice) -> Result<()> {
            self.call("flags")
        }
        fn retain(&self, _: CuDevice) -> Result<CuContext> {
            self.call("retain")?;
            self.active.set(true);
            Ok(handle())
        }
        fn set_current(&self, raw: CuContext) -> Result<()> {
            self.call(if raw.is_null() {
                "detach"
            } else {
                "make_current"
            })?;
            self.current.set(raw);
            Ok(())
        }
        fn uuid(&self, _: CuDevice) -> Result<String> {
            self.call("uuid")?;
            Ok(if self.fail == "mismatch" {
                "GPU-other"
            } else {
                "GPU-test"
            }
            .into())
        }
        fn release(&self, _: CuDevice) -> Result<()> {
            self.call("release")?;
            self.active.set(false);
            Ok(())
        }
    }
    #[test]
    fn primary_missing_symbols_refuse_without_resources() {
        for missing in SYMBOLS {
            assert!(
                required_symbols(|name| if name == missing {
                    Err(DeviceError::SymbolMissing(name))
                } else {
                    Ok(())
                })
                .is_err()
            );
        }
    }
    #[test]
    fn primary_preconditions_never_retain_or_reset() {
        for failure in ["current", "state", "flags", "retain"] {
            let calls = Fake::new(failure);
            assert!(acquire(&calls, 0, "GPU-test").is_err());
            assert!(!calls.events.borrow().contains(&"release"));
        }
        let calls = Fake::new("");
        calls.current.set(handle());
        assert!(acquire(&calls, 0, "GPU-test").is_err());
        assert!(!calls.events.borrow().contains(&"retain"));
        calls.current.set(ptr::null_mut());
        calls.active.set(true);
        assert!(acquire(&calls, 0, "GPU-test").is_err());
        assert!(!calls.events.borrow().contains(&"retain"));
    }
    #[test]
    fn primary_partial_initialization_releases_exactly_once() {
        for failure in ["make_current", "uuid", "mismatch"] {
            let calls = Fake::new(failure);
            assert!(acquire(&calls, 0, "GPU-test").is_err());
            assert_eq!(
                calls
                    .events
                    .borrow()
                    .iter()
                    .filter(|e| **e == "release")
                    .count(),
                1
            );
            assert!(!calls.active.get());
        }
    }
    #[test]
    fn primary_cleanup_failures_are_observed_without_retry() {
        for failure in ["", "detach", "release"] {
            let observer = setup::SetupObservation::begin().unwrap();
            let calls = Fake::new(failure);
            let raw = acquire(&calls, 0, "GPU-test").unwrap();
            setup::event("context_retain_primary", true, "GPU-test");
            cleanup(&calls, 0, raw);
            let events = observer.finish();
            assert_eq!(
                setup::complete(setup::ContextMode::PrimaryExperimental, &events),
                failure.is_empty()
            );
            assert_eq!(
                calls
                    .events
                    .borrow()
                    .iter()
                    .filter(|e| **e == "release")
                    .count(),
                1
            );
        }
    }
}
