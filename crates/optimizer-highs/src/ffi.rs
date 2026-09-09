//! Private declarations for the pinned HiGHS 1.11.0 C API.
//!
//! Only the entry points the adapter needs are declared. Raw handles never
//! cross this module's boundary: `super::Highs` owns them and destroys them
//! exactly once. `HighsInt` is 32-bit because ADR-0003 pins `HIGHSINT64=OFF`.

#![allow(non_snake_case)]

use std::ffi::{c_char, c_double, c_int, c_void};

/// Native integer width under the pinned `HIGHSINT64=OFF` build.
pub(crate) type HighsInt = c_int;

// A width mismatch would silently corrupt every index we pass, so fail the
// build instead of trusting the configuration.
const _: () = assert!(size_of::<HighsInt>() == 4);

// Status codes returned by C API calls.
pub(crate) const K_HIGHS_STATUS_ERROR: HighsInt = -1;
pub(crate) const K_HIGHS_STATUS_OK: HighsInt = 0;
pub(crate) const K_HIGHS_STATUS_WARNING: HighsInt = 1;

// Variable types.
pub(crate) const K_HIGHS_VAR_TYPE_CONTINUOUS: HighsInt = 0;
pub(crate) const K_HIGHS_VAR_TYPE_INTEGER: HighsInt = 1;

// Objective sense.
pub(crate) const K_HIGHS_OBJ_SENSE_MINIMIZE: HighsInt = 1;
pub(crate) const K_HIGHS_OBJ_SENSE_MAXIMIZE: HighsInt = -1;

// Matrix orientation for the sparse row layout we pass.
pub(crate) const K_HIGHS_MATRIX_FORMAT_ROWWISE: HighsInt = 2;

// Model statuses. Every one of these is mapped explicitly by the adapter.
pub(crate) const K_HIGHS_MODEL_STATUS_NOTSET: HighsInt = 0;
pub(crate) const K_HIGHS_MODEL_STATUS_LOAD_ERROR: HighsInt = 1;
pub(crate) const K_HIGHS_MODEL_STATUS_MODEL_ERROR: HighsInt = 2;
pub(crate) const K_HIGHS_MODEL_STATUS_PRESOLVE_ERROR: HighsInt = 3;
pub(crate) const K_HIGHS_MODEL_STATUS_SOLVE_ERROR: HighsInt = 4;
pub(crate) const K_HIGHS_MODEL_STATUS_POSTSOLVE_ERROR: HighsInt = 5;
pub(crate) const K_HIGHS_MODEL_STATUS_MODEL_EMPTY: HighsInt = 6;
pub(crate) const K_HIGHS_MODEL_STATUS_OPTIMAL: HighsInt = 7;
pub(crate) const K_HIGHS_MODEL_STATUS_INFEASIBLE: HighsInt = 8;
pub(crate) const K_HIGHS_MODEL_STATUS_UNBOUNDED_OR_INFEASIBLE: HighsInt = 9;
pub(crate) const K_HIGHS_MODEL_STATUS_UNBOUNDED: HighsInt = 10;
pub(crate) const K_HIGHS_MODEL_STATUS_OBJECTIVE_BOUND: HighsInt = 11;
pub(crate) const K_HIGHS_MODEL_STATUS_OBJECTIVE_TARGET: HighsInt = 12;
pub(crate) const K_HIGHS_MODEL_STATUS_TIME_LIMIT: HighsInt = 13;
pub(crate) const K_HIGHS_MODEL_STATUS_ITERATION_LIMIT: HighsInt = 14;
pub(crate) const K_HIGHS_MODEL_STATUS_UNKNOWN: HighsInt = 15;
pub(crate) const K_HIGHS_MODEL_STATUS_SOLUTION_LIMIT: HighsInt = 16;
pub(crate) const K_HIGHS_MODEL_STATUS_INTERRUPT: HighsInt = 17;

// Basis statuses.
pub(crate) const K_HIGHS_BASIS_STATUS_LOWER: HighsInt = 0;
pub(crate) const K_HIGHS_BASIS_STATUS_BASIC: HighsInt = 1;
pub(crate) const K_HIGHS_BASIS_STATUS_UPPER: HighsInt = 2;
pub(crate) const K_HIGHS_BASIS_STATUS_ZERO: HighsInt = 3;
pub(crate) const K_HIGHS_BASIS_STATUS_NONBASIC: HighsInt = 4;

// Interrupt callback types used for cooperative cancellation.
pub(crate) const K_HIGHS_CALLBACK_SIMPLEX_INTERRUPT: HighsInt = 1;
pub(crate) const K_HIGHS_CALLBACK_IPM_INTERRUPT: HighsInt = 2;
pub(crate) const K_HIGHS_CALLBACK_MIP_INTERRUPT: HighsInt = 6;

/// Callback output data. Only the leading fields are read, so the struct is
/// declared opaque and accessed through the C API's own accessors.
#[repr(C)]
pub(crate) struct HighsCallbackDataOut {
    _opaque: [u8; 0],
}

/// Callback input data. `user_interrupt` is the documented cancellation channel.
///
/// The layout mirrors `HighsCallbackStruct.h` for the pinned 1.11.0 release.
#[repr(C)]
pub(crate) struct HighsCallbackDataIn {
    pub(crate) user_solution_callback_origin: HighsInt,
    pub(crate) user_interrupt: c_int,
    pub(crate) user_solution: *mut c_double,
    pub(crate) cbdata: *mut c_void,
    pub(crate) user_has_solution: c_int,
    pub(crate) user_solution_size: HighsInt,
}

pub(crate) type HighsCCallbackType = unsafe extern "C" fn(
    callback_type: c_int,
    message: *const c_char,
    data_out: *const HighsCallbackDataOut,
    data_in: *mut HighsCallbackDataIn,
    user_callback_data: *mut c_void,
);

#[cfg(highs_native)]
unsafe extern "C" {
    pub(crate) fn Highs_version() -> *const c_char;
    pub(crate) fn Highs_create() -> *mut c_void;
    pub(crate) fn Highs_destroy(highs: *mut c_void);
    pub(crate) fn Highs_getInfinity(highs: *const c_void) -> c_double;

    pub(crate) fn Highs_setBoolOptionValue(
        highs: *mut c_void,
        option: *const c_char,
        value: c_int,
    ) -> HighsInt;
    pub(crate) fn Highs_setIntOptionValue(
        highs: *mut c_void,
        option: *const c_char,
        value: HighsInt,
    ) -> HighsInt;
    pub(crate) fn Highs_setDoubleOptionValue(
        highs: *mut c_void,
        option: *const c_char,
        value: c_double,
    ) -> HighsInt;
    pub(crate) fn Highs_setStringOptionValue(
        highs: *mut c_void,
        option: *const c_char,
        value: *const c_char,
    ) -> HighsInt;

    #[allow(clippy::too_many_arguments)]
    pub(crate) fn Highs_passLp(
        highs: *mut c_void,
        num_col: HighsInt,
        num_row: HighsInt,
        num_nz: HighsInt,
        a_format: HighsInt,
        sense: HighsInt,
        offset: c_double,
        col_cost: *const c_double,
        col_lower: *const c_double,
        col_upper: *const c_double,
        row_lower: *const c_double,
        row_upper: *const c_double,
        a_start: *const HighsInt,
        a_index: *const HighsInt,
        a_value: *const c_double,
    ) -> HighsInt;

    #[allow(clippy::too_many_arguments)]
    pub(crate) fn Highs_passMip(
        highs: *mut c_void,
        num_col: HighsInt,
        num_row: HighsInt,
        num_nz: HighsInt,
        a_format: HighsInt,
        sense: HighsInt,
        offset: c_double,
        col_cost: *const c_double,
        col_lower: *const c_double,
        col_upper: *const c_double,
        row_lower: *const c_double,
        row_upper: *const c_double,
        a_start: *const HighsInt,
        a_index: *const HighsInt,
        a_value: *const c_double,
        integrality: *const HighsInt,
    ) -> HighsInt;

    pub(crate) fn Highs_run(highs: *mut c_void) -> HighsInt;
    pub(crate) fn Highs_getModelStatus(highs: *const c_void) -> HighsInt;
    pub(crate) fn Highs_getSolution(
        highs: *const c_void,
        col_value: *mut c_double,
        col_dual: *mut c_double,
        row_value: *mut c_double,
        row_dual: *mut c_double,
    ) -> HighsInt;
    pub(crate) fn Highs_getBasis(
        highs: *const c_void,
        col_status: *mut HighsInt,
        row_status: *mut HighsInt,
    ) -> HighsInt;
    pub(crate) fn Highs_setBasis(
        highs: *mut c_void,
        col_status: *const HighsInt,
        row_status: *const HighsInt,
    ) -> HighsInt;
    pub(crate) fn Highs_setSolution(
        highs: *mut c_void,
        col_value: *const c_double,
        row_value: *const c_double,
        col_dual: *const c_double,
        row_dual: *const c_double,
    ) -> HighsInt;

    pub(crate) fn Highs_getIntInfoValue(
        highs: *const c_void,
        info: *const c_char,
        value: *mut c_int,
    ) -> HighsInt;
    pub(crate) fn Highs_getDoubleInfoValue(
        highs: *const c_void,
        info: *const c_char,
        value: *mut c_double,
    ) -> HighsInt;

    pub(crate) fn Highs_setCallback(
        highs: *mut c_void,
        user_callback: Option<HighsCCallbackType>,
        user_callback_data: *mut c_void,
    ) -> HighsInt;
    pub(crate) fn Highs_startCallback(highs: *mut c_void, callback_type: HighsInt) -> HighsInt;
}
