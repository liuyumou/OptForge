//! The CUDA driver boundary, under SPEC-0010 and ADR-0009.
//!
//! This crate is the second and last native boundary in the workspace. It holds
//! foreign declarations and owned handles, and it knows nothing about optimization,
//! schedules or models: everything above it stays safe Rust, and `optimizer-cuda`
//! in particular keeps `unsafe_code = "forbid"` while consuming this.
//!
//! The driver library is resolved at runtime with `dlopen` rather than linked, which
//! is ADR-0009's decision and has three consequences the rest of the design depends
//! on. An ordinary `cargo build` needs neither the CUDA toolkit nor its driver stub.
//! A host with no driver produces [`DeviceError::DriverUnavailable`] instead of a
//! link failure, which is what makes SPEC-0010 requirement 37 reachable. And no
//! NVIDIA code is linked or redistributed.
//!
//! Every handle here releases its driver resource on drop, and every one of them
//! holds a shared reference to the [`Context`] it belongs to. That is what makes a
//! context outlive its modules, streams and allocations no matter what order a
//! caller drops them in. A borrowed lifetime would express the same rule and would
//! also force every holder to be borrowed from something, which a candidate producer
//! owning its own residency cannot be.

use std::ffi::{CStr, CString, c_char, c_int, c_uint, c_void};
use std::fmt;
use std::marker::PhantomData;
use std::path::Path;
use std::ptr;
use std::rc::Rc;
use std::sync::OnceLock;

mod status;

pub use status::DriverStatus;

/// Opaque driver handles. The driver defines these as pointers; we never
/// dereference them, so a raw pointer is the whole of the representation.
type CuContext = *mut c_void;
type CuModule = *mut c_void;
type CuFunction = *mut c_void;
type CuStream = *mut c_void;
/// The driver's device ordinal type, which is a plain `int`.
type CuDevice = c_int;
/// A device address. This is an integer, not a pointer: it is not dereferenceable
/// by the host and must never be turned into one.
type CuDevicePtr = u64;

/// Anything that can go wrong reaching or using a device.
///
/// The distinction SPEC-0010 draws between an availability failure and a
/// disagreement is drawn here too: everything in this enum is an availability
/// failure, and a disagreement is not representable, because this crate never
/// computes a result to disagree about.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DeviceError {
    /// `libcuda.so.1` could not be opened. No driver is installed, or the process
    /// cannot see it.
    DriverUnavailable(String),
    /// The library opened but does not export something this crate requires, which
    /// means it is older than the contract assumes.
    SymbolMissing(&'static str),
    /// A driver call failed, carrying the exhaustively mapped status.
    Driver {
        /// The call that failed.
        call: &'static str,
        /// The mapped status.
        status: DriverStatus,
        /// The driver's own description.
        detail: String,
    },
    /// A code object was requested that this build does not have.
    CodeObjectMissing(String),
    /// The device the driver reported is not the device that was requested.
    DeviceMismatch {
        /// What the caller asked for.
        requested: String,
        /// What the driver reported.
        found: String,
    },
    /// No device carries the requested UUID.
    DeviceNotFound(String),
    /// A request that cannot be satisfied on this device.
    Unsupported(String),
    /// The caller cancelled between launch chunks.
    ///
    /// Not a failure of the device. It is here so a caller can tell a cancelled
    /// run from a failed one without parsing a message, which matters because
    /// SPEC-0010 requirement 30 forbids reporting either as a solver outcome but
    /// they are recorded differently.
    Cancelled,
    /// A fault inside a kernel left this context permanently unusable.
    ///
    /// Every later call on the same context fails too, so continuing to launch
    /// would turn one fault into a stream of them. Requirement 29 forbids that:
    /// the context is finished, and the caller rebuilds or falls back.
    ContextPoisoned(DriverStatus),
}

impl fmt::Display for DeviceError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::DriverUnavailable(detail) => {
                write!(formatter, "CUDA driver unavailable: {detail}")
            }
            Self::SymbolMissing(name) => {
                write!(formatter, "CUDA driver does not export {name}")
            }
            Self::Driver {
                call,
                status,
                detail,
            } => write!(formatter, "{call} failed: {} ({detail})", status.as_str()),
            Self::CodeObjectMissing(path) => {
                write!(formatter, "no device code object at {path}")
            }
            Self::DeviceMismatch { requested, found } => write!(
                formatter,
                "requested device {requested} but the driver reported {found}"
            ),
            Self::DeviceNotFound(uuid) => write!(formatter, "no device with UUID {uuid}"),
            Self::Unsupported(detail) => write!(formatter, "unsupported: {detail}"),
            Self::Cancelled => write!(formatter, "cancelled between launch chunks"),
            Self::ContextPoisoned(status) => write!(
                formatter,
                "context is unusable after {}; it cannot be reused",
                status.as_str()
            ),
        }
    }
}

impl DeviceError {
    /// Whether this failure left the context permanently unusable.
    ///
    /// True for a sticky driver status as well as for an already-poisoned context,
    /// so a caller can make the same decision from either without knowing which
    /// call first observed the fault.
    #[must_use]
    pub fn poisons_context(&self) -> bool {
        match self {
            Self::ContextPoisoned(_) => true,
            Self::Driver { status, .. } => status.is_sticky(),
            _ => false,
        }
    }
}

impl std::error::Error for DeviceError {}

/// Shorthand for this crate's results.
pub type Result<T> = std::result::Result<T, DeviceError>;

// ---- The resolved driver ----

macro_rules! driver_api {
    ($($field:ident : $symbol:literal => unsafe extern "C" fn($($argument:ty),* $(,)?) -> $ret:ty,)*) => {
        /// Function pointers resolved once from `libcuda.so.1`.
        ///
        /// Every signature here is a hand-written claim about the driver's ABI that
        /// no compiler checks, which ADR-0009 records as the cost of `dlsym`. The
        /// mitigation is that the surface is small, every entry is a call this
        /// project makes deliberately, and the versioned symbol names are the ones
        /// the CUDA headers actually alias to.
        struct Driver {
            _handle: *mut c_void,
            $($field: unsafe extern "C" fn($($argument),*) -> $ret,)*
        }

        impl Driver {
            unsafe fn resolve(handle: *mut c_void) -> Result<Self> {
                Ok(Self {
                    _handle: handle,
                    $($field: unsafe { symbol(handle, concat!($symbol, "\0"))? },)*
                })
            }
        }
    };
}

driver_api! {
    init: "cuInit" => unsafe extern "C" fn(c_uint) -> c_int,
    driver_version: "cuDriverGetVersion" => unsafe extern "C" fn(*mut c_int) -> c_int,
    device_count: "cuDeviceGetCount" => unsafe extern "C" fn(*mut c_int) -> c_int,
    device_get: "cuDeviceGet" => unsafe extern "C" fn(*mut CuDevice, c_int) -> c_int,
    device_name: "cuDeviceGetName" => unsafe extern "C" fn(*mut c_char, c_int, CuDevice) -> c_int,
    device_uuid: "cuDeviceGetUuid" => unsafe extern "C" fn(*mut [u8; 16], CuDevice) -> c_int,
    device_attribute: "cuDeviceGetAttribute" => unsafe extern "C" fn(*mut c_int, c_int, CuDevice) -> c_int,
    device_total_memory: "cuDeviceTotalMem_v2" => unsafe extern "C" fn(*mut usize, CuDevice) -> c_int,
    context_create: "cuCtxCreate_v2" => unsafe extern "C" fn(*mut CuContext, c_uint, CuDevice) -> c_int,
    context_destroy: "cuCtxDestroy_v2" => unsafe extern "C" fn(CuContext) -> c_int,
    context_set_current: "cuCtxSetCurrent" => unsafe extern "C" fn(CuContext) -> c_int,
    module_load_data: "cuModuleLoadData" => unsafe extern "C" fn(*mut CuModule, *const c_void) -> c_int,
    module_unload: "cuModuleUnload" => unsafe extern "C" fn(CuModule) -> c_int,
    module_get_function: "cuModuleGetFunction" => unsafe extern "C" fn(*mut CuFunction, CuModule, *const c_char) -> c_int,
    function_set_attribute: "cuFuncSetAttribute" => unsafe extern "C" fn(CuFunction, c_int, c_int) -> c_int,
    memory_allocate: "cuMemAlloc_v2" => unsafe extern "C" fn(*mut CuDevicePtr, usize) -> c_int,
    memory_free: "cuMemFree_v2" => unsafe extern "C" fn(CuDevicePtr) -> c_int,
    memory_info: "cuMemGetInfo_v2" => unsafe extern "C" fn(*mut usize, *mut usize) -> c_int,
    copy_to_device: "cuMemcpyHtoDAsync_v2" => unsafe extern "C" fn(CuDevicePtr, *const c_void, usize, CuStream) -> c_int,
    copy_to_host: "cuMemcpyDtoHAsync_v2" => unsafe extern "C" fn(*mut c_void, CuDevicePtr, usize, CuStream) -> c_int,
    stream_create: "cuStreamCreate" => unsafe extern "C" fn(*mut CuStream, c_uint) -> c_int,
    stream_destroy: "cuStreamDestroy_v2" => unsafe extern "C" fn(CuStream) -> c_int,
    stream_synchronize: "cuStreamSynchronize" => unsafe extern "C" fn(CuStream) -> c_int,
    launch: "cuLaunchKernel" => unsafe extern "C" fn(CuFunction, c_uint, c_uint, c_uint, c_uint, c_uint, c_uint, c_uint, CuStream, *mut *mut c_void, *mut *mut c_void) -> c_int,
    error_string: "cuGetErrorString" => unsafe extern "C" fn(c_int, *mut *const c_char) -> c_int,
}

// The driver is documented as thread-safe, and the handle is only ever read after
// initialization, so sharing the resolved table across threads is sound. Nothing in
// this crate mutates it.
unsafe impl Send for Driver {}
unsafe impl Sync for Driver {}

unsafe fn symbol<T>(handle: *mut c_void, name: &'static str) -> Result<T> {
    // SAFETY: `name` is a literal with an explicit trailing NUL appended by the
    // macro, so it is a valid C string, and `handle` came from a successful
    // `dlopen`.
    let pointer = unsafe { libc::dlsym(handle, name.as_ptr().cast::<c_char>()) };
    if pointer.is_null() {
        // Trim the NUL the macro appended before reporting the name.
        return Err(DeviceError::SymbolMissing(
            name.strip_suffix('\0').unwrap_or(name),
        ));
    }
    debug_assert_eq!(
        size_of::<T>(),
        size_of::<*mut c_void>(),
        "a driver entry point must be pointer-sized"
    );
    // SAFETY: `T` is a function pointer type supplied by the macro and asserted
    // pointer-sized above, and `pointer` is a non-null symbol address.
    Ok(unsafe { std::mem::transmute_copy::<*mut c_void, T>(&pointer) })
}

static DRIVER: OnceLock<std::result::Result<Driver, DeviceError>> = OnceLock::new();

fn driver() -> Result<&'static Driver> {
    let resolved = DRIVER.get_or_init(|| {
        // SAFETY: a literal NUL-terminated path, and the flags are the documented
        // ones. `RTLD_NOW` surfaces a missing symbol here rather than at first call.
        let handle =
            unsafe { libc::dlopen(c"libcuda.so.1".as_ptr(), libc::RTLD_NOW | libc::RTLD_LOCAL) };
        if handle.is_null() {
            // SAFETY: `dlerror` returns either null or a valid C string.
            let detail = unsafe {
                let message = libc::dlerror();
                if message.is_null() {
                    "libcuda.so.1 could not be opened".to_string()
                } else {
                    CStr::from_ptr(message).to_string_lossy().into_owned()
                }
            };
            return Err(DeviceError::DriverUnavailable(detail));
        }
        // SAFETY: `handle` is a live library handle from `dlopen`.
        let driver = unsafe { Driver::resolve(handle) }?;
        // SAFETY: resolved above; flags must be zero per the driver contract.
        let status = unsafe { (driver.init)(0) };
        check(&driver, "cuInit", status)?;
        Ok(driver)
    });
    resolved.as_ref().map_err(Clone::clone)
}

/// Whether a driver is present at all, without creating a context.
///
/// This is the availability question SPEC-0010 requirement 24 turns into a
/// fallback rather than a failure, so it is answerable without taking a lease.
pub fn driver_available() -> bool {
    driver().is_ok()
}

/// The driver version as `(major, minor)`, or an availability failure.
///
/// # Errors
///
/// Returns [`DeviceError::DriverUnavailable`] when no driver is present.
pub fn driver_version() -> Result<(u32, u32)> {
    let driver = driver()?;
    let mut raw = 0;
    // SAFETY: `raw` is a live, writable `c_int`.
    let status = unsafe { (driver.driver_version)(&mut raw) };
    check(driver, "cuDriverGetVersion", status)?;
    let raw = u32::try_from(raw).unwrap_or(0);
    Ok((raw / 1000, (raw % 1000) / 10))
}

fn check(driver: &Driver, call: &'static str, status: c_int) -> Result<()> {
    if status == 0 {
        return Ok(());
    }
    let mut text: *const c_char = ptr::null();
    // SAFETY: `text` is a live, writable pointer slot. The driver either fills it
    // with a static string or leaves it null.
    let detail = unsafe {
        if (driver.error_string)(status, &mut text) == 0 && !text.is_null() {
            CStr::from_ptr(text).to_string_lossy().into_owned()
        } else {
            format!("driver status {status}")
        }
    };
    Err(DeviceError::Driver {
        call,
        status: DriverStatus::from_raw(status),
        detail,
    })
}

// ---- Devices ----

/// A device's identity and the properties a caller needs before using it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DeviceInfo {
    /// Driver-reported UUID in the `GPU-` form the rest of the project uses.
    pub uuid: String,
    /// Driver-reported model name.
    pub name: String,
    /// Compute capability major version.
    pub capability_major: u32,
    /// Compute capability minor version.
    pub capability_minor: u32,
    /// Streaming multiprocessor count.
    pub multiprocessors: u32,
    /// Maximum shared memory a single block may opt into, in bytes.
    pub max_shared_memory_per_block: u32,
    /// Total device memory in bytes.
    pub total_memory: u64,
    /// The driver's ordinal, which is not stable across processes and is therefore
    /// never accepted as an identifier.
    ordinal: c_int,
}

/// Driver attribute numbers, from `cuda.h`. Only the ones this crate reads.
const ATTRIBUTE_CAPABILITY_MAJOR: c_int = 75;
const ATTRIBUTE_CAPABILITY_MINOR: c_int = 76;
const ATTRIBUTE_MULTIPROCESSOR_COUNT: c_int = 16;
const ATTRIBUTE_MAX_SHARED_MEMORY_PER_BLOCK_OPTIN: c_int = 97;

/// Every device the driver reports, in UUID order.
///
/// Ordering by UUID rather than by ordinal matches the existing discovery contract
/// and is what keeps two processes with different `CUDA_VISIBLE_DEVICES` agreeing
/// about which device a name refers to.
///
/// # Errors
///
/// Returns an availability failure when the driver is absent or a query fails.
pub fn devices() -> Result<Vec<DeviceInfo>> {
    let driver = driver()?;
    let mut count = 0;
    // SAFETY: `count` is a live, writable `c_int`.
    let status = unsafe { (driver.device_count)(&mut count) };
    check(driver, "cuDeviceGetCount", status)?;

    let mut found = Vec::new();
    for ordinal in 0..count {
        let mut device: CuDevice = 0;
        // SAFETY: `device` is live and `ordinal` is within the reported count.
        let status = unsafe { (driver.device_get)(&mut device, ordinal) };
        check(driver, "cuDeviceGet", status)?;
        found.push(describe(driver, device, ordinal)?);
    }
    found.sort_by(|left, right| left.uuid.cmp(&right.uuid));
    Ok(found)
}

fn describe(driver: &Driver, device: CuDevice, ordinal: c_int) -> Result<DeviceInfo> {
    let mut raw = [0u8; 16];
    // SAFETY: the driver writes exactly sixteen bytes into this array.
    let status = unsafe { (driver.device_uuid)(&mut raw, device) };
    check(driver, "cuDeviceGetUuid", status)?;

    let mut name = [0 as c_char; 256];
    // SAFETY: `name` is 256 writable bytes and the length passed matches it. The
    // driver NUL-terminates within that bound.
    let status = unsafe {
        (driver.device_name)(
            name.as_mut_ptr(),
            c_int::try_from(name.len()).unwrap_or(c_int::MAX),
            device,
        )
    };
    check(driver, "cuDeviceGetName", status)?;
    // SAFETY: the driver NUL-terminated the buffer above.
    let name = unsafe { CStr::from_ptr(name.as_ptr()) }
        .to_string_lossy()
        .into_owned();

    let mut total_memory = 0usize;
    // SAFETY: `total_memory` is a live, writable `usize`.
    let status = unsafe { (driver.device_total_memory)(&mut total_memory, device) };
    check(driver, "cuDeviceTotalMem_v2", status)?;

    Ok(DeviceInfo {
        uuid: format_uuid(&raw),
        name,
        capability_major: attribute(driver, device, ATTRIBUTE_CAPABILITY_MAJOR)?,
        capability_minor: attribute(driver, device, ATTRIBUTE_CAPABILITY_MINOR)?,
        multiprocessors: attribute(driver, device, ATTRIBUTE_MULTIPROCESSOR_COUNT)?,
        max_shared_memory_per_block: attribute(
            driver,
            device,
            ATTRIBUTE_MAX_SHARED_MEMORY_PER_BLOCK_OPTIN,
        )?,
        total_memory: total_memory as u64,
        ordinal,
    })
}

fn attribute(driver: &Driver, device: CuDevice, attribute: c_int) -> Result<u32> {
    let mut value = 0;
    // SAFETY: `value` is a live, writable `c_int` and `attribute` is a documented
    // attribute number.
    let status = unsafe { (driver.device_attribute)(&mut value, attribute, device) };
    check(driver, "cuDeviceGetAttribute", status)?;
    Ok(u32::try_from(value).unwrap_or(0))
}

/// Render a raw UUID in the `GPU-8-4-4-4-12` form `nvidia-smi` prints.
fn format_uuid(raw: &[u8; 16]) -> String {
    let hex: String = raw.iter().map(|byte| format!("{byte:02x}")).collect();
    format!(
        "GPU-{}-{}-{}-{}-{}",
        &hex[0..8],
        &hex[8..12],
        &hex[12..16],
        &hex[16..20],
        &hex[20..32]
    )
}

// ---- Context ----

/// An owned CUDA context bound to exactly one device.
///
/// Creating one requires naming a UUID, and the UUID the driver reports is compared
/// against it, which is SPEC-0010 requirement 3: a record must not be able to claim
/// a device the run did not use. There is deliberately no constructor taking an
/// ordinal, because `CUDA_VISIBLE_DEVICES` renumbers ordinals per process.
pub struct Context {
    raw: CuContext,
    info: DeviceInfo,
}

impl Context {
    /// Create a context on the device with `uuid`.
    ///
    /// # Errors
    ///
    /// Returns [`DeviceError::DeviceNotFound`] when no visible device carries the
    /// UUID, [`DeviceError::DeviceMismatch`] when the driver reports a different one
    /// after creation, and an availability failure for any driver error.
    pub fn create(uuid: &str) -> Result<Self> {
        let driver = driver()?;
        let info = devices()?
            .into_iter()
            .find(|candidate| candidate.uuid == uuid)
            .ok_or_else(|| DeviceError::DeviceNotFound(uuid.to_string()))?;

        let mut device: CuDevice = 0;
        // SAFETY: `device` is live and the ordinal came from this driver.
        let status = unsafe { (driver.device_get)(&mut device, info.ordinal) };
        check(driver, "cuDeviceGet", status)?;

        let mut raw: CuContext = ptr::null_mut();
        // SAFETY: `raw` is a live slot; flags of zero is the documented default.
        let status = unsafe { (driver.context_create)(&mut raw, 0, device) };
        check(driver, "cuCtxCreate_v2", status)?;
        let context = Self { raw, info };

        // Read the identity back through the handle we actually hold, rather than
        // trusting the lookup that produced the ordinal. This is the assertion
        // requirement 3 is about, and it is made after creation on purpose: an
        // ordinal that was correct at lookup time is not evidence about the context.
        let observed = describe(driver, device, context.info.ordinal)?;
        if observed.uuid != uuid {
            return Err(DeviceError::DeviceMismatch {
                requested: uuid.to_string(),
                found: observed.uuid,
            });
        }
        Ok(context)
    }

    /// The device this context is bound to.
    #[must_use]
    pub fn device(&self) -> &DeviceInfo {
        &self.info
    }

    /// Free and total device memory in bytes.
    ///
    /// # Errors
    ///
    /// Returns an availability failure when the query fails.
    pub fn memory_info(&self) -> Result<(u64, u64)> {
        let driver = driver()?;
        self.make_current(driver)?;
        let (mut free, mut total) = (0usize, 0usize);
        // SAFETY: both slots are live and writable.
        let status = unsafe { (driver.memory_info)(&mut free, &mut total) };
        check(driver, "cuMemGetInfo_v2", status)?;
        Ok((free as u64, total as u64))
    }

    fn make_current(&self, driver: &Driver) -> Result<()> {
        // SAFETY: `self.raw` is a live context this value owns.
        let status = unsafe { (driver.context_set_current)(self.raw) };
        check(driver, "cuCtxSetCurrent", status)
    }

    /// Load a module from a code object already in memory.
    ///
    /// # Errors
    ///
    /// Returns an availability failure when the image is not loadable on this
    /// device, which includes a cubin built for another compute capability.
    pub fn load_module(self: &Rc<Self>, image: &[u8]) -> Result<Module> {
        let driver = driver()?;
        self.make_current(driver)?;
        // The driver reads a NUL-terminated image for PTX and a length-prefixed one
        // for cubin; appending a NUL is safe for both and is what lets one entry
        // point accept either.
        let mut owned = Vec::with_capacity(image.len() + 1);
        owned.extend_from_slice(image);
        owned.push(0);
        let mut raw: CuModule = ptr::null_mut();
        // SAFETY: `raw` is a live slot and `owned` is a NUL-terminated image that
        // outlives the call.
        let status = unsafe { (driver.module_load_data)(&mut raw, owned.as_ptr().cast()) };
        check(driver, "cuModuleLoadData", status)?;
        Ok(Module {
            raw,
            _context: Rc::clone(self),
        })
    }

    /// Load a module from a code object on disk.
    ///
    /// # Errors
    ///
    /// Returns [`DeviceError::CodeObjectMissing`] when the file is absent, and
    /// whatever [`Context::load_module`] returns otherwise.
    pub fn load_module_file(self: &Rc<Self>, path: &Path) -> Result<Module> {
        let image = std::fs::read(path)
            .map_err(|_| DeviceError::CodeObjectMissing(path.display().to_string()))?;
        self.load_module(&image)
    }

    /// Create a stream on this context.
    ///
    /// # Errors
    ///
    /// Returns an availability failure when creation fails.
    pub fn stream(self: &Rc<Self>) -> Result<Stream> {
        let driver = driver()?;
        self.make_current(driver)?;
        let mut raw: CuStream = ptr::null_mut();
        // SAFETY: `raw` is a live slot; flags of zero is the documented default.
        let status = unsafe { (driver.stream_create)(&mut raw, 0) };
        check(driver, "cuStreamCreate", status)?;
        Ok(Stream {
            raw,
            _context: Rc::clone(self),
        })
    }

    /// Allocate `count` elements of device memory.
    ///
    /// # Errors
    ///
    /// Returns an availability failure when the allocation fails, which SPEC-0010
    /// requirement 24 makes a fallback rather than an abort.
    pub fn allocate<T: Copy>(self: &Rc<Self>, count: usize) -> Result<DeviceBuffer<T>> {
        let driver = driver()?;
        self.make_current(driver)?;
        let bytes = count
            .checked_mul(size_of::<T>())
            .ok_or_else(|| DeviceError::Unsupported("allocation size overflowed".into()))?;
        // A zero-byte allocation is not meaningful and the driver rejects it; make
        // that an explicit refusal rather than a driver error a caller must decode.
        if bytes == 0 {
            return Err(DeviceError::Unsupported("allocation of zero bytes".into()));
        }
        let mut raw: CuDevicePtr = 0;
        // SAFETY: `raw` is a live slot and `bytes` is nonzero.
        let status = unsafe { (driver.memory_allocate)(&mut raw, bytes) };
        check(driver, "cuMemAlloc_v2", status)?;
        Ok(DeviceBuffer {
            raw,
            count,
            _context: Rc::clone(self),
            _element: PhantomData,
        })
    }
}

impl Drop for Context {
    fn drop(&mut self) {
        // A failure here cannot be reported and must not panic in a drop. The
        // process is either exiting or has already recorded the failure that led
        // here, and the driver reclaims the context when the process ends.
        if let Ok(driver) = driver() {
            // SAFETY: `self.raw` is a live context this value owns, dropped once.
            unsafe {
                let _ = (driver.context_destroy)(self.raw);
            }
        }
    }
}

// A context is bound to a device, not to a thread, and this crate sets it current
// before every use. It is not `Sync`, because two threads using one context
// concurrently would race on the current-context slot.
unsafe impl Send for Context {}

// ---- Module and function ----

/// A loaded code object. Borrowing its context is what prevents unloading after the
/// context it belongs to has been destroyed.
pub struct Module {
    raw: CuModule,
    // Keeps the context alive for at least as long as this module. Unloading a
    // module into a destroyed context is the failure this prevents, and it cannot
    // be prevented by drop order alone once a caller owns both.
    _context: Rc<Context>,
}

impl Module {
    /// Look up a kernel by its exported name.
    ///
    /// # Errors
    ///
    /// Returns an availability failure when the module exports no such name, which
    /// in practice means the code object is older than the caller.
    pub fn function(&self, name: &str) -> Result<Function<'_>> {
        let driver = driver()?;
        let name = CString::new(name)
            .map_err(|_| DeviceError::Unsupported("kernel name contains a NUL".into()))?;
        let mut raw: CuFunction = ptr::null_mut();
        // SAFETY: `raw` is a live slot, `self.raw` is a loaded module, and `name`
        // is a valid C string that outlives the call.
        let status = unsafe { (driver.module_get_function)(&mut raw, self.raw, name.as_ptr()) };
        check(driver, "cuModuleGetFunction", status)?;
        Ok(Function {
            raw,
            _module: PhantomData,
        })
    }
}

impl Drop for Module {
    fn drop(&mut self) {
        if let Ok(driver) = driver() {
            // SAFETY: `self.raw` is a live module this value owns, dropped once.
            unsafe {
                let _ = (driver.module_unload)(self.raw);
            }
        }
    }
}

/// `CU_FUNC_ATTRIBUTE_MAX_DYNAMIC_SHARED_SIZE_BYTES`, from `cuda.h`.
///
/// Opting in is mandatory above 48 KB. At compute capability 12.0 the ceiling is
/// 99 KB per block, which is what sizes the schedule evaluator's tables.
const FUNCTION_ATTRIBUTE_MAX_DYNAMIC_SHARED: c_int = 8;

/// A kernel entry point.
pub struct Function<'module> {
    raw: CuFunction,
    _module: PhantomData<&'module ()>,
}

impl Function<'_> {
    /// Opt into more than the default 48 KB of dynamic shared memory.
    ///
    /// # Errors
    ///
    /// Returns an availability failure when the device refuses the request, which is
    /// how a kernel sized for one compute capability is rejected on another rather
    /// than launched and silently truncated.
    pub fn set_max_dynamic_shared_memory(&self, bytes: u32) -> Result<()> {
        let driver = driver()?;
        let bytes = c_int::try_from(bytes)
            .map_err(|_| DeviceError::Unsupported("shared memory request overflowed".into()))?;
        // SAFETY: `self.raw` is a live function and the attribute number is the
        // documented one.
        let status = unsafe {
            (driver.function_set_attribute)(self.raw, FUNCTION_ATTRIBUTE_MAX_DYNAMIC_SHARED, bytes)
        };
        check(driver, "cuFuncSetAttribute", status)
    }
}

// ---- Stream and memory ----

/// An owned stream. Work is ordered within one and this crate uses exactly one per
/// residency, so ordering is explicit rather than implied by the default stream.
pub struct Stream {
    raw: CuStream,
    _context: Rc<Context>,
}

impl Stream {
    /// Block until everything queued on this stream has finished.
    ///
    /// # Errors
    ///
    /// Returns an availability failure, which after a launch is where a kernel fault
    /// surfaces.
    pub fn synchronize(&self) -> Result<()> {
        let driver = driver()?;
        // SAFETY: `self.raw` is a live stream this value owns.
        let status = unsafe { (driver.stream_synchronize)(self.raw) };
        check(driver, "cuStreamSynchronize", status)
    }
}

impl Drop for Stream {
    fn drop(&mut self) {
        if let Ok(driver) = driver() {
            // SAFETY: `self.raw` is a live stream this value owns, dropped once.
            unsafe {
                let _ = (driver.stream_destroy)(self.raw);
            }
        }
    }
}

/// An owned device allocation of `T`.
///
/// `T: Copy` is required because the bytes are transferred verbatim: a type with a
/// destructor or an interior pointer would be meaningless on a device.
pub struct DeviceBuffer<T: Copy> {
    raw: CuDevicePtr,
    count: usize,
    _context: Rc<Context>,
    _element: PhantomData<T>,
}

impl<T: Copy> DeviceBuffer<T> {
    /// Element count.
    #[must_use]
    pub fn len(&self) -> usize {
        self.count
    }

    /// Whether the allocation holds no elements. It never does: a zero-length
    /// allocation is refused at construction.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.count == 0
    }

    /// The device address, for passing as a kernel argument.
    #[must_use]
    pub fn as_device_ptr(&self) -> u64 {
        self.raw
    }

    /// Copy `source` onto the device, queued on `stream`.
    ///
    /// # Errors
    ///
    /// Returns [`DeviceError::Unsupported`] when `source` is longer than the
    /// allocation, and an availability failure when the copy fails.
    pub fn copy_from(&mut self, source: &[T], stream: &Stream) -> Result<()> {
        if source.len() > self.count {
            return Err(DeviceError::Unsupported(format!(
                "copy of {} elements into a buffer of {}",
                source.len(),
                self.count
            )));
        }
        if source.is_empty() {
            return Ok(());
        }
        let driver = driver()?;
        // SAFETY: `source` is a live slice of exactly the byte count passed, the
        // destination allocation is at least that large as checked above, and the
        // stream is live. The copy is asynchronous, and `Stream::synchronize` is
        // what every caller in this workspace uses before reading the result.
        let status = unsafe {
            (driver.copy_to_device)(
                self.raw,
                source.as_ptr().cast(),
                std::mem::size_of_val(source),
                stream.raw,
            )
        };
        check(driver, "cuMemcpyHtoDAsync_v2", status)?;
        // The source is borrowed only for this call, so the copy must complete
        // before it returns. Synchronizing here is what makes that true, and it is
        // the reason this method is not the one a hot loop uses.
        stream.synchronize()
    }

    /// Copy the device contents into `destination`, queued on `stream`.
    ///
    /// # Errors
    ///
    /// Returns [`DeviceError::Unsupported`] when `destination` is longer than the
    /// allocation, and an availability failure when the copy fails.
    pub fn copy_to(&self, destination: &mut [T], stream: &Stream) -> Result<()> {
        if destination.len() > self.count {
            return Err(DeviceError::Unsupported(format!(
                "copy of {} elements out of a buffer of {}",
                destination.len(),
                self.count
            )));
        }
        if destination.is_empty() {
            return Ok(());
        }
        let driver = driver()?;
        let bytes = std::mem::size_of_val(destination);
        // SAFETY: `destination` is a live, writable slice of exactly `bytes`, the
        // source allocation is at least that large as checked above, and the stream
        // is live.
        let status = unsafe {
            (driver.copy_to_host)(destination.as_mut_ptr().cast(), self.raw, bytes, stream.raw)
        };
        check(driver, "cuMemcpyDtoHAsync_v2", status)?;
        stream.synchronize()
    }
}

impl<T: Copy> Drop for DeviceBuffer<T> {
    fn drop(&mut self) {
        if let Ok(driver) = driver() {
            // SAFETY: `self.raw` is a live allocation this value owns, dropped once.
            unsafe {
                let _ = (driver.memory_free)(self.raw);
            }
        }
    }
}

/// How a kernel is launched: grid and block shape, and dynamic shared memory.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct LaunchConfig {
    /// Blocks in the grid.
    pub grid: u32,
    /// Threads per block.
    pub block: u32,
    /// Dynamic shared memory per block, in bytes.
    pub shared_memory: u32,
}

/// A kernel argument, kept as an owned value so the launch can take its address.
///
/// The driver wants an array of pointers to arguments. Building that from borrowed
/// values is where a launch API usually goes wrong, so arguments are copied into
/// this enum first and the pointer array is built from the copies, which live until
/// the launch returns.
#[derive(Debug, Clone, Copy)]
pub enum Argument {
    /// A device address.
    DevicePtr(u64),
    /// A 32-bit unsigned value.
    U32(u32),
}

/// Launch `function` with `arguments` on `stream`.
///
/// # Errors
///
/// Returns an availability failure when the launch is rejected. A fault inside the
/// kernel is asynchronous and surfaces at the next [`Stream::synchronize`], not here.
pub fn launch(
    function: &Function<'_>,
    config: LaunchConfig,
    arguments: &[Argument],
    stream: &Stream,
) -> Result<()> {
    let driver = driver()?;
    // Copy every argument into a local array first, then build the pointer array
    // from those copies. Both outlive the call below, which is the property the
    // driver's `kernelParams` contract requires and the one an API taking borrowed
    // arguments cannot guarantee.
    let mut storage: Vec<[u8; 8]> = Vec::with_capacity(arguments.len());
    for argument in arguments {
        let mut cell = [0u8; 8];
        match argument {
            Argument::DevicePtr(value) => cell.copy_from_slice(&value.to_ne_bytes()),
            Argument::U32(value) => cell[..4].copy_from_slice(&value.to_ne_bytes()),
        }
        storage.push(cell);
    }
    let mut pointers: Vec<*mut c_void> = storage
        .iter_mut()
        .map(|cell| cell.as_mut_ptr().cast())
        .collect();

    // SAFETY: `function` and `stream` are live, the pointer array has one entry per
    // declared parameter and each points at storage that outlives the call, and the
    // `extra` array is null as the driver documents for this form.
    let status = unsafe {
        (driver.launch)(
            function.raw,
            config.grid,
            1,
            1,
            config.block,
            1,
            1,
            config.shared_memory,
            stream.raw,
            pointers.as_mut_ptr(),
            ptr::null_mut(),
        )
    };
    check(driver, "cuLaunchKernel", status)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_raw_uuid_renders_in_the_form_management_tooling_prints() {
        let raw = [
            0xdf, 0xb2, 0x44, 0x9a, 0x9e, 0xff, 0xe8, 0x68, 0x35, 0x97, 0x2c, 0x44, 0x8c, 0x9a,
            0x8e, 0x48,
        ];
        assert_eq!(
            format_uuid(&raw),
            "GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48"
        );
    }

    #[test]
    fn an_absent_driver_is_an_availability_failure_rather_than_a_panic() {
        // This asserts the shape of the answer, not which answer this host gives:
        // the point is that asking is always safe and never aborts, which is what
        // SPEC-0010 requirement 24 needs in order to make a fallback possible.
        match driver_version() {
            Ok((major, _)) => assert!(major >= 12, "a CUDA 12 or later driver is expected"),
            Err(error) => assert!(matches!(
                error,
                DeviceError::DriverUnavailable(_) | DeviceError::SymbolMissing(_)
            )),
        }
        assert_eq!(driver_available(), driver_version().is_ok());
    }
}
