//! Isolated research ABI. CUDA proposals never constitute mathematical proofs.
//! All buffers remain owned by the synchronous caller until a call returns.

use std::ffi::c_void;

pub fn admitted_shape(rows: i32, cols: i32, width: i32) -> bool {
    rows > 0 && cols > 0 && cols % 2 == 0 && [1, 8, 32, 64].contains(&width)
        && (rows as i64) * (cols as i64) <= 100_000_000
        && rows <= i32::MAX / 64 && cols <= i32::MAX / 64
}

#[cfg(feature = "cuda")]
extern "C" {
    fn batch_create(r: i32, s: i32, sparse: i32, b: *const f64, out: *mut *mut c_void) -> i32;
    fn batch_propose(ctx: *mut c_void, width: i32, targets: *const i32,
        h: f64, eps: f64, steps: i32, mode: i32, x: *mut f64, u: *mut f64,
        milliseconds: *mut f64) -> i32;
    fn batch_propose_slots(ctx: *mut c_void, width: i32, targets: *const i32,
        h: f64, eps: f64, steps: i32, mode: i32, x: *mut f64, u: *mut f64,
        milliseconds: *mut f64) -> i32;
    fn batch_destroy(ctx: *mut c_void) -> i32;
}

/// # Safety
/// `b` addresses `rows*cols` doubles; `out` addresses one writable pointer.
#[no_mangle]
pub unsafe extern "C" fn sp_create(rows: i32, cols: i32, sparse: i32,
    b: *const f64, out: *mut *mut c_void) -> i32 {
    if !admitted_shape(rows, cols, 1) || b.is_null() || out.is_null()
        || !(0..=1).contains(&sparse) { return -1; }
    *out = std::ptr::null_mut();
    #[cfg(feature = "cuda")] { return batch_create(rows, cols, sparse, b, out); }
    #[cfg(not(feature = "cuda"))] { -2 }
}

/// # Safety
/// `ctx` is a live handle from `sp_create`, targets has width entries, and x/u
/// have width*rows / width*cols entries. Calls on one handle must be serialized.
#[no_mangle]
pub unsafe extern "C" fn sp_propose(ctx: *mut c_void, width: i32, targets: *const i32,
    h: f64, eps: f64, steps: i32, mode: i32, x: *mut f64, u: *mut f64,
    milliseconds: *mut f64) -> i32 {
    if ctx.is_null() || targets.is_null() || x.is_null() || u.is_null()
        || milliseconds.is_null() || ![1, 8, 32, 64].contains(&width)
        || !h.is_finite() || h <= 0.0 || !eps.is_finite() || eps <= 0.0
        || eps >= 0.25 || !(1..=10000).contains(&steps) || !(0..=6).contains(&mode)
        { return -1; }
    #[cfg(feature = "cuda")] {
        return batch_propose(ctx, width, targets, h, eps, steps, mode, x, u, milliseconds);
    }
    #[cfg(not(feature = "cuda"))] { -2 }
}

/// # Safety
/// Same live-buffer contract as sp_propose; targets index signed matrix slots.
#[no_mangle]
pub unsafe extern "C" fn sp_propose_slots(ctx: *mut c_void, width: i32, targets: *const i32,
    h: f64, eps: f64, steps: i32, mode: i32, x: *mut f64, u: *mut f64,
    milliseconds: *mut f64) -> i32 {
    if ctx.is_null() || targets.is_null() || x.is_null() || u.is_null()
        || milliseconds.is_null() || ![1, 8, 32, 64].contains(&width)
        || !h.is_finite() || h <= 0.0 || !eps.is_finite() || eps <= 0.0
        || eps >= 0.25 || !(1..=10000).contains(&steps) || !(0..=6).contains(&mode)
        { return -1; }
    #[cfg(feature = "cuda")] {
        return batch_propose_slots(ctx, width, targets, h, eps, steps, mode, x, u, milliseconds);
    }
    #[cfg(not(feature = "cuda"))] { -2 }
}

/// # Safety
/// The non-null handle is live and has no pending call. It is consumed once.
#[no_mangle]
pub unsafe extern "C" fn sp_destroy(ctx: *mut c_void) -> i32 {
    if ctx.is_null() { return 0; }
    #[cfg(feature = "cuda")] { return batch_destroy(ctx); }
    #[cfg(not(feature = "cuda"))] { -2 }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test] fn rejects_shape_and_overflow() {
        assert!(admitted_shape(10, 20, 32));
        assert!(!admitted_shape(10, 19, 32));
        assert!(!admitted_shape(10, 20, 3));
        assert!(!admitted_shape(i32::MAX, i32::MAX-1, 64));
        assert!(!admitted_shape(40_000_000, 2, 1));
    }
    #[test] fn rejects_invalid_pointer_before_cuda() {
        unsafe { assert_eq!(sp_create(1, 2, 0, std::ptr::null(), std::ptr::null_mut()), -1); }
    }
}
