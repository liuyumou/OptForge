//! Bounded CPU contract only; original-model checking remains independent.
use serde::{Deserialize, Serialize};

/// CPU reference envelope; large declared sparse shapes must not trigger unbounded allocation.
pub const MAX_DIMENSION: usize = 65_536;
pub const MAX_NONZEROS: usize = 4_194_304;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Refusal {
    Shape,
    Nonfinite,
    RepresentationRange,
    ArithmeticRange,
    CounterOverflow,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Csr {
    pub rows: usize,
    pub cols: usize,
    pub offsets: Vec<usize>,
    pub columns: Vec<usize>,
    pub values: Vec<f64>,
}

#[derive(Debug)]
pub struct Prepared {
    original: Csr,
    stored: Vec<f32>,
    error: Vec<f64>,
}

#[derive(Debug, Serialize)]
pub struct Product {
    pub values: Vec<f64>,
    pub error_bounds: Vec<f64>,
    pub representation_bounds: Vec<f64>,
    pub rounding_bounds: Vec<f64>,
}

fn up(value: f64) -> Result<f64, Refusal> {
    if !value.is_finite() || value < 0.0 {
        return Err(Refusal::ArithmeticRange);
    }
    let result = value.next_up();
    if result.is_finite() {
        Ok(result)
    } else {
        Err(Refusal::ArithmeticRange)
    }
}
fn add(a: f64, b: f64) -> Result<f64, Refusal> {
    if a == 0.0 {
        return Ok(b);
    }
    if b == 0.0 {
        return Ok(a);
    }
    up(a + b)
}
fn multiply(a: f64, b: f64) -> Result<f64, Refusal> {
    if a == 0.0 || b == 0.0 {
        return Ok(0.0);
    }
    up(a * b)
}

impl Prepared {
    pub fn new(original: Csr) -> Result<Self, Refusal> {
        let Csr {
            rows,
            cols,
            offsets,
            columns,
            values,
        } = &original;
        if *rows == 0
            || *cols == 0
            || *rows > MAX_DIMENSION
            || *cols > MAX_DIMENSION
            || values.len() > MAX_NONZEROS
            || rows.checked_add(1) != Some(offsets.len())
            || columns.len() != values.len()
            || offsets.first() != Some(&0)
            || offsets.last() != Some(&values.len())
        {
            return Err(Refusal::Shape);
        }
        for range in offsets.windows(2) {
            if range[0] > range[1] || range[1] > values.len() {
                return Err(Refusal::Shape);
            }
            let indices = &columns[range[0]..range[1]];
            if indices.iter().any(|&c| c >= *cols) || indices.windows(2).any(|v| v[0] >= v[1]) {
                return Err(Refusal::Shape);
            }
        }
        let mut stored = Vec::with_capacity(values.len());
        let mut error = Vec::with_capacity(values.len());
        for &a in values {
            if !a.is_finite() {
                return Err(Refusal::Nonfinite);
            }
            let b = a as f32;
            if !b.is_finite() || (a != 0.0 && b == 0.0) {
                return Err(Refusal::RepresentationRange);
            }
            stored.push(b);
            let difference = (a - f64::from(b)).abs();
            error.push(if difference == 0.0 {
                0.0
            } else {
                up(difference)?
            });
        }
        Ok(Self {
            original,
            stored,
            error,
        })
    }

    /// Enclose error relative to an exact original-A dot, including FMA rounding.
    pub fn product(&self, x: &[f64], transpose: bool) -> Result<Product, Refusal> {
        let a = &self.original;
        let (input, output) = if transpose {
            (a.rows, a.cols)
        } else {
            (a.cols, a.rows)
        };
        if x.len() != input {
            return Err(Refusal::Shape);
        }
        if x.iter().any(|v| !v.is_finite()) {
            return Err(Refusal::Nonfinite);
        }
        let mut result = Product {
            values: vec![0.0; output],
            error_bounds: vec![0.0; output],
            representation_bounds: vec![0.0; output],
            rounding_bounds: vec![0.0; output],
        };
        let u = 2.0_f64.powi(-53);
        let factor = up(u / (1.0 - u))?;
        for row in 0..a.rows {
            for k in a.offsets[row]..a.offsets[row + 1] {
                let col = a.columns[k];
                let (destination, operand) = if transpose {
                    (col, x[row])
                } else {
                    (row, x[col])
                };
                let value = f64::from(self.stored[k]).mul_add(operand, result.values[destination]);
                if !value.is_finite() {
                    return Err(Refusal::ArithmeticRange);
                }
                let local = add(multiply(factor, value.abs())?, f64::from_bits(1))?;
                result.rounding_bounds[destination] =
                    add(result.rounding_bounds[destination], local)?;
                result.representation_bounds[destination] = add(
                    result.representation_bounds[destination],
                    multiply(self.error[k], operand.abs())?,
                )?;
                result.values[destination] = value;
            }
        }
        for i in 0..output {
            result.error_bounds[i] =
                add(result.representation_bounds[i], result.rounding_bounds[i])?;
        }
        Ok(result)
    }

    pub fn original(&self) -> &Csr {
        &self.original
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Mode {
    Mixed,
    Native,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Reason {
    Accepted,
    ErrorBudget,
    Stagnation,
    Cancelled,
    InvalidAudit,
    NoWork,
    NativeOnly,
}
#[derive(Debug, Clone, Copy)]
pub struct Audit {
    pub primal_before: f64,
    pub primal_after: f64,
    pub dual_before: f64,
    pub dual_after: f64,
    pub error_bound: f64,
    pub allowance: f64,
}
#[derive(Debug)]
pub struct WindowResult {
    pub checkpoint: Vec<u8>,
    pub reason: Reason,
}
#[derive(Debug)]
pub struct Controller {
    mode: Mode,
    physical: u64,
    logical: u64,
    useful_windows: u64,
}
impl Default for Controller {
    fn default() -> Self {
        Self {
            mode: Mode::Mixed,
            physical: 0,
            logical: 0,
            useful_windows: 0,
        }
    }
}
impl Controller {
    pub fn mode(&self) -> Mode {
        self.mode
    }
    pub fn physical(&self) -> u64 {
        self.physical
    }
    pub fn logical(&self) -> u64 {
        self.logical
    }
    pub fn useful_windows(&self) -> u64 {
        self.useful_windows
    }

    /// Caller must supply original-model residuals and a complete serialized checkpoint.
    /// This reference has no certificate-producing operation.
    pub fn finish(
        &mut self,
        checkpoint: Vec<u8>,
        candidate: Vec<u8>,
        attempted: u64,
        audit: Audit,
        cancelled: bool,
    ) -> Result<WindowResult, Refusal> {
        let physical = self
            .physical
            .checked_add(attempted)
            .ok_or(Refusal::CounterOverflow)?;
        if self.mode == Mode::Native {
            // Refusing publication must not erase work reported by the caller.
            self.physical = physical;
            return Ok(WindowResult {
                checkpoint,
                reason: Reason::NativeOnly,
            });
        }
        let fields = [
            audit.primal_before,
            audit.primal_after,
            audit.dual_before,
            audit.dual_after,
            audit.error_bound,
            audit.allowance,
        ];
        let reason = if cancelled {
            Reason::Cancelled
        } else if attempted == 0 {
            Reason::NoWork
        } else if fields.iter().any(|v| !v.is_finite() || *v < 0.0) {
            Reason::InvalidAudit
        } else if audit.error_bound > audit.allowance {
            Reason::ErrorBudget
        } else if !(audit.primal_before > 0.0
            && audit.dual_before > 0.0
            && audit.primal_after <= 0.99 * audit.primal_before
            && audit.dual_after <= 0.99 * audit.dual_before)
        {
            Reason::Stagnation
        } else {
            Reason::Accepted
        };
        if reason == Reason::Accepted {
            let logical = self
                .logical
                .checked_add(attempted)
                .ok_or(Refusal::CounterOverflow)?;
            let useful = self
                .useful_windows
                .checked_add(1)
                .ok_or(Refusal::CounterOverflow)?;
            self.logical = logical;
            self.useful_windows = useful;
        } else if reason != Reason::Cancelled {
            self.mode = Mode::Native;
        }
        self.physical = physical;
        Ok(WindowResult {
            checkpoint: if reason == Reason::Accepted {
                candidate
            } else {
                checkpoint
            },
            reason,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn csr(values: Vec<f64>) -> Csr {
        Csr {
            rows: 1,
            cols: values.len(),
            offsets: vec![0, values.len()],
            columns: (0..values.len()).collect(),
            values,
        }
    }
    fn audit() -> Audit {
        Audit {
            primal_before: 1.0,
            primal_after: 0.5,
            dual_before: 2.0,
            dual_after: 1.0,
            error_bound: 1e-8,
            allowance: 1e-7,
        }
    }
    #[test]
    fn range_and_nonfinite_refusals() {
        for value in [f64::MAX, f64::from_bits(1)] {
            assert_eq!(
                Prepared::new(csr(vec![value])).unwrap_err(),
                Refusal::RepresentationRange
            );
        }
        for value in [f64::NAN, f64::INFINITY] {
            assert_eq!(
                Prepared::new(csr(vec![value])).unwrap_err(),
                Refusal::Nonfinite
            );
        }
    }
    #[test]
    fn original_bits_and_subnormals_retained() {
        let p = Prepared::new(csr(vec![-0.0, f64::from(f32::from_bits(1)), 1.00000001])).unwrap();
        assert_eq!(p.original().values[0].to_bits(), (-0.0_f64).to_bits());
        assert_eq!(p.stored[0].to_bits(), (-0.0_f32).to_bits());
        assert!(p.product(&[1.0; 3], false).unwrap().error_bounds[0] > 0.0);
    }
    #[test]
    fn malformed_csr_refuses_without_panic() {
        let a = Csr {
            rows: 1,
            cols: usize::MAX,
            offsets: vec![0, 0],
            columns: vec![],
            values: vec![],
        };
        assert_eq!(Prepared::new(a).unwrap_err(), Refusal::Shape);
        let mut a = csr(vec![1.0, 2.0]);
        a.offsets = vec![3, 2];
        assert_eq!(Prepared::new(a).unwrap_err(), Refusal::Shape);
        let mut a = csr(vec![1.0, 2.0]);
        a.columns = vec![1, 1];
        assert_eq!(Prepared::new(a).unwrap_err(), Refusal::Shape);
    }
    #[test]
    fn vector_and_arithmetic_refusals() {
        let p = Prepared::new(csr(vec![2.0])).unwrap();
        assert_eq!(p.product(&[], false).unwrap_err(), Refusal::Shape);
        assert_eq!(
            p.product(&[f64::NAN], false).unwrap_err(),
            Refusal::Nonfinite
        );
        assert_eq!(
            p.product(&[f64::MAX], false).unwrap_err(),
            Refusal::ArithmeticRange
        );
    }
    #[test]
    fn empty_rows_and_transpose_share_coefficients() {
        let p = Prepared::new(Csr {
            rows: 2,
            cols: 2,
            offsets: vec![0, 0, 1],
            columns: vec![0],
            values: vec![0.1],
        })
        .unwrap();
        let forward = p.product(&[1.0, 0.0], false).unwrap();
        let transpose = p.product(&[0.0, 1.0], true).unwrap();
        assert_eq!(forward.values[1].to_bits(), transpose.values[0].to_bits());
        assert_eq!(forward.values[0], 0.0);
        assert_eq!(forward.error_bounds[0], 0.0);
    }
    #[test]
    fn accepted_nonzero_work_is_charged() {
        let mut c = Controller::default();
        let r = c
            .finish(vec![0, 128], vec![1, 0], 7, audit(), false)
            .unwrap();
        assert_eq!(r.reason, Reason::Accepted);
        assert_eq!(r.checkpoint, vec![1, 0]);
        assert_eq!((c.physical(), c.logical(), c.useful_windows()), (7, 7, 1));
    }
    #[test]
    fn error_failure_restores_bytes_and_sticky_promotes() {
        let mut c = Controller::default();
        let mut a = audit();
        a.error_bound = 1.0;
        let r = c.finish(vec![0, 128, 255], vec![1], 3, a, false).unwrap();
        assert_eq!(r.reason, Reason::ErrorBudget);
        assert_eq!(r.checkpoint, vec![0, 128, 255]);
        assert_eq!(c.mode(), Mode::Native);
        assert_eq!((c.physical(), c.logical()), (3, 0));
        assert_eq!(
            c.finish(vec![4], vec![5], 9, audit(), false)
                .unwrap()
                .reason,
            Reason::NativeOnly
        );
        assert_eq!(c.physical(), 12);
    }
    #[test]
    fn both_residuals_must_progress() {
        for primal in [true, false] {
            let mut c = Controller::default();
            let mut a = audit();
            if primal {
                a.primal_after = 1.0;
            } else {
                a.dual_after = 2.0;
            }
            assert_eq!(
                c.finish(vec![7], vec![8], 4, a, false).unwrap().reason,
                Reason::Stagnation
            );
            assert_eq!((c.physical(), c.logical()), (4, 0));
        }
    }
    #[test]
    fn cancellation_restores_and_charges() {
        let mut c = Controller::default();
        let r = c.finish(vec![0, 128], vec![1], 8, audit(), true).unwrap();
        assert_eq!(r.reason, Reason::Cancelled);
        assert_eq!(r.checkpoint, vec![0, 128]);
        assert_eq!(c.mode(), Mode::Mixed);
        assert_eq!((c.physical(), c.logical()), (8, 0));
    }
    #[test]
    fn zero_work_and_bad_audit_never_qualify() {
        let mut c = Controller::default();
        assert_eq!(
            c.finish(vec![], vec![1], 0, audit(), false).unwrap().reason,
            Reason::NoWork
        );
        for value in [-1.0, f64::INFINITY, f64::NAN] {
            let mut c = Controller::default();
            let mut a = audit();
            a.allowance = value;
            assert_eq!(
                c.finish(vec![], vec![1], 2, a, false).unwrap().reason,
                Reason::InvalidAudit
            );
        }
    }
    #[test]
    fn counter_overflow_is_atomic() {
        let mut c = Controller {
            physical: u64::MAX,
            ..Controller::default()
        };
        assert_eq!(
            c.finish(vec![], vec![1], 1, audit(), false).unwrap_err(),
            Refusal::CounterOverflow
        );
        assert_eq!(c.mode(), Mode::Mixed);
        assert_eq!(c.logical(), 0);
    }
}
