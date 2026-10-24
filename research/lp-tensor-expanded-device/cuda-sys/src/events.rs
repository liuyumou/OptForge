//! Bounded CUDA-event observations owned by the existing driver boundary.
use super::{Context, CuStream, DeviceError, Result, Stream, check, driver, symbol};
use std::{
    ffi::{c_int, c_uint, c_void},
    ptr,
    rc::Rc,
    sync::OnceLock,
};
type Raw = *mut c_void;
struct Api {
    create: unsafe extern "C" fn(*mut Raw, c_uint) -> c_int,
    destroy: unsafe extern "C" fn(Raw) -> c_int,
    record: unsafe extern "C" fn(Raw, CuStream) -> c_int,
    elapsed: unsafe extern "C" fn(*mut f32, Raw, Raw) -> c_int,
}
static API: OnceLock<Result<Api>> = OnceLock::new();
fn api() -> Result<&'static Api> {
    API.get_or_init(|| {
        let handle = driver()?._handle;
        // SAFETY: these signatures match cuda.h's driver event APIs. The retained
        // driver owns the live library handle for the process lifetime.
        unsafe {
            Ok(Api {
                create: symbol(handle, "cuEventCreate\0")?,
                destroy: symbol(handle, "cuEventDestroy_v2\0")?,
                record: symbol(handle, "cuEventRecord\0")?,
                elapsed: symbol(handle, "cuEventElapsedTime\0")?,
            })
        }
    })
    .as_ref()
    .map_err(Clone::clone)
}
/// Event with its creating context held until destruction.
pub struct Event {
    raw: Raw,
    context: Rc<Context>,
}
impl Event {
    /// Allocate a timing-enabled event. Caller limits the pool before allocation.
    pub fn new(context: &Rc<Context>) -> Result<Self> {
        let mut raw = ptr::null_mut();
        // SAFETY: writable output, default zero flags, current owned context.
        let status = unsafe { (api()?.create)(&mut raw, 0) };
        check(driver()?, "cuEventCreate", status)?;
        Ok(Self {
            raw,
            context: Rc::clone(context),
        })
    }
    /// Record on a live stream from exactly this context.
    pub fn record(&self, stream: &Stream) -> Result<()> {
        if !Rc::ptr_eq(&self.context, &stream._context) {
            return Err(DeviceError::DriverUnavailable(
                "event/stream context mismatch".into(),
            ));
        }
        // SAFETY: owned event/stream share a live context; driver owns queued work.
        check(driver()?, "cuEventRecord", unsafe {
            (api()?.record)(self.raw, stream.raw)
        })
    }
    /// Elapsed milliseconds after the recording stream has been synchronized.
    pub fn elapsed_to(&self, end: &Self) -> Result<f32> {
        if !Rc::ptr_eq(&self.context, &end.context) {
            return Err(DeviceError::DriverUnavailable(
                "event pair context mismatch".into(),
            ));
        }
        let mut milliseconds = 0.;
        // SAFETY: two live timing events, writable output. Not-ready is a checked
        // driver error rather than an uninitialized duration.
        check(driver()?, "cuEventElapsedTime", unsafe {
            (api()?.elapsed)(&mut milliseconds, self.raw, end.raw)
        })?;
        if !milliseconds.is_finite() || milliseconds < 0. {
            return Err(DeviceError::DriverUnavailable(
                "invalid CUDA event duration".into(),
            ));
        }
        Ok(milliseconds)
    }
}
impl Drop for Event {
    fn drop(&mut self) {
        if let Ok(api) = api() {
            // SAFETY: this event was created successfully and is destroyed once; context
            // ownership remains live until after Drop returns.
            unsafe {
                (api.destroy)(self.raw);
            }
        }
    }
}
