//! Diagonal preconditioning, under SPEC-0011 requirement 9.
//!
//! A first-order method's convergence depends strongly on how well the constraint
//! matrix is scaled, so a preconditioner is not an optimization here: it is part
//! of what the method is. That is exactly why requirement 9 makes it recorded
//! state. It changes the iterates, so it changes the result, so a record that did
//! not name it would not describe the solve it came from.
//!
//! Two passes, in this order. Ruiz equilibration repeatedly divides each row and
//! column by the square root of its largest magnitude, which drives every row and
//! column maximum toward one. Then one Pock-Chambolle pass balances the remaining
//! scale between the primal and dual steps.
//!
//! Only the Ruiz pass is order-independent for free: a maximum of magnitudes does
//! not depend on the order it was taken in, whereas the Pock-Chambolle pass sums
//! absolute values and therefore goes through the fixed reduction in
//! [`crate::reduce`]. Mixing the two rules would have made the preconditioner's
//! reproducibility depend on which pass happened to dominate.

use serde::{Deserialize, Serialize};

use crate::problem::LinearProgram;
use crate::reduce::tree_sum;

/// How the preconditioner was configured, recorded with every solve.
#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PreconditionerSettings {
    /// Number of Ruiz equilibration passes. Fixed, never convergence-driven: a
    /// pass count that stopped on a measured criterion would vary with rounding
    /// and take the iterates with it.
    pub ruiz_passes: u32,
    /// Pock-Chambolle exponent. `1.0` is the balanced choice; `0.0` disables the
    /// pass.
    pub pock_chambolle_alpha: f64,
}

impl PreconditionerSettings {
    /// Whether these settings are usable.
    ///
    /// # Errors
    ///
    /// Returns a document failure for a nonfinite or out-of-range exponent, or a
    /// pass count large enough to be a mistake rather than a choice.
    pub fn validate(&self) -> Result<(), optimizer_core::ValidationError> {
        use optimizer_core::{ErrorKind, ValidationError};
        if self.ruiz_passes > 100 {
            return Err(ValidationError::new(
                ErrorKind::Document,
                format!("ruiz_passes {} exceeds 100", self.ruiz_passes),
            ));
        }
        if !self.pock_chambolle_alpha.is_finite()
            || self.pock_chambolle_alpha < 0.0
            || self.pock_chambolle_alpha > 2.0
        {
            return Err(ValidationError::new(
                ErrorKind::Document,
                format!(
                    "pock_chambolle_alpha {} must be finite in [0, 2]",
                    self.pock_chambolle_alpha
                ),
            ));
        }
        Ok(())
    }
}

/// The diagonal scaling applied to a program.
///
/// `row[i]` and `column[j]` are the multipliers, so the scaled matrix is
/// `diag(row) A diag(column)`. Both are strictly positive, which keeps the
/// unscaling exact in the sense that it divides by a number that cannot be zero.
#[derive(Clone, Debug, PartialEq)]
pub struct Preconditioner {
    row: Vec<f64>,
    column: Vec<f64>,
    settings: PreconditionerSettings,
}

impl Preconditioner {
    /// Compute the scaling for one program.
    #[must_use]
    pub fn new(program: &LinearProgram, settings: PreconditionerSettings) -> Self {
        let rows = program.row_count();
        let columns = program.column_count();
        let mut row = vec![1.0f64; rows];
        let mut column = vec![1.0f64; columns];

        for _ in 0..settings.ruiz_passes {
            let mut row_max = vec![0.0f64; rows];
            let mut column_max = vec![0.0f64; columns];
            for (r, c, value) in program.row_major().entries() {
                let scaled = (row[r] * value * column[c as usize]).abs();
                row_max[r] = row_max[r].max(scaled);
                column_max[c as usize] = column_max[c as usize].max(scaled);
            }
            // An empty row or column has maximum zero and is left alone. Scaling
            // it by anything would be dividing by nothing.
            for (index, maximum) in row_max.iter().enumerate() {
                if *maximum > 0.0 {
                    row[index] /= maximum.sqrt();
                }
            }
            for (index, maximum) in column_max.iter().enumerate() {
                if *maximum > 0.0 {
                    column[index] /= maximum.sqrt();
                }
            }
        }

        if settings.pock_chambolle_alpha > 0.0 {
            let alpha = settings.pock_chambolle_alpha;
            // These are sums, so they go through the fixed reduction rather than
            // being accumulated in whatever order the entries arrive.
            let mut row_terms: Vec<Vec<f64>> = vec![Vec::new(); rows];
            let mut column_terms: Vec<Vec<f64>> = vec![Vec::new(); columns];
            for (r, c, value) in program.row_major().entries() {
                let scaled = (row[r] * value * column[c as usize]).abs();
                row_terms[r].push(scaled.powf(2.0 - alpha));
                column_terms[c as usize].push(scaled.powf(alpha));
            }
            for (index, terms) in row_terms.iter().enumerate() {
                let total = tree_sum(terms);
                if total > 0.0 {
                    row[index] /= total.sqrt();
                }
            }
            for (index, terms) in column_terms.iter().enumerate() {
                let total = tree_sum(terms);
                if total > 0.0 {
                    column[index] /= total.sqrt();
                }
            }
        }

        Self {
            row,
            column,
            settings,
        }
    }

    /// Row multipliers.
    #[must_use]
    pub fn row(&self) -> &[f64] {
        &self.row
    }

    /// Column multipliers.
    #[must_use]
    pub fn column(&self) -> &[f64] {
        &self.column
    }

    /// The settings that produced this scaling.
    #[must_use]
    pub fn settings(&self) -> PreconditionerSettings {
        self.settings
    }

    /// A stable digest of the diagonals, for the record.
    ///
    /// The record carries a digest rather than the two vectors themselves: they
    /// are `rows + columns` doubles and would dwarf every other field, and a
    /// reader who wants them can recompute them from the recorded settings and
    /// the model, which is what makes the digest sufficient. It is a check that
    /// the recomputation matches, not a substitute for the numbers.
    #[must_use]
    pub fn digest(&self) -> String {
        // FNV-1a over the raw bit patterns. Not cryptographic and not required to
        // be: this detects a changed scaling, it does not defend against a chosen
        // one.
        let mut hash: u64 = 0xcbf2_9ce4_8422_2325;
        for value in self.row.iter().chain(&self.column) {
            for byte in value.to_bits().to_le_bytes() {
                hash ^= u64::from(byte);
                hash = hash.wrapping_mul(0x0000_0100_0000_01b3);
            }
        }
        format!("{hash:016x}")
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use optimizer_core::{
        Bound, Constraint, Domain, LinearTerm, Model, ModelDocument, Objective, ObjectiveSense,
        SCHEMA_VERSION, Variable,
    };

    fn settings() -> PreconditionerSettings {
        PreconditionerSettings {
            ruiz_passes: 10,
            pock_chambolle_alpha: 1.0,
        }
    }

    fn badly_scaled() -> LinearProgram {
        let model = Model::new(ModelDocument {
            schema_version: SCHEMA_VERSION,
            model_id: "badly-scaled".to_string(),
            variables: (0..3)
                .map(|id| Variable {
                    id,
                    domain: Domain::Continuous,
                    lower: Bound::Finite { value: 0.0 },
                    upper: Bound::Finite { value: 1.0 },
                })
                .collect(),
            constraints: vec![
                Constraint {
                    id: 0,
                    lower: Bound::NegativeInfinity,
                    upper: Bound::Finite { value: 1.0e6 },
                    terms: vec![
                        LinearTerm {
                            variable_id: 0,
                            coefficient: 1.0e6,
                        },
                        LinearTerm {
                            variable_id: 1,
                            coefficient: 1.0e-3,
                        },
                    ],
                },
                Constraint {
                    id: 1,
                    lower: Bound::NegativeInfinity,
                    upper: Bound::Finite { value: 1.0 },
                    terms: vec![LinearTerm {
                        variable_id: 2,
                        coefficient: 1.0,
                    }],
                },
            ],
            objective: Objective {
                sense: ObjectiveSense::Minimize,
                offset: 0.0,
                terms: vec![LinearTerm {
                    variable_id: 0,
                    coefficient: 1.0,
                }],
            },
        })
        .expect("valid");
        LinearProgram::new(&model).expect("continuous")
    }

    /// Requirement 9's premise: the preconditioner is a pure function of the
    /// program and its recorded parameters, so recording those parameters is
    /// enough to reproduce it.
    #[test]
    fn the_preconditioner_is_a_pure_function_of_its_recorded_parameters() {
        let program = badly_scaled();
        let first = Preconditioner::new(&program, settings());
        let second = Preconditioner::new(&program, settings());
        assert_eq!(first, second);
        assert_eq!(first.digest(), second.digest());
    }

    #[test]
    fn different_settings_produce_a_different_digest() {
        let program = badly_scaled();
        let balanced = Preconditioner::new(&program, settings());
        let none = Preconditioner::new(
            &program,
            PreconditionerSettings {
                ruiz_passes: 0,
                pock_chambolle_alpha: 0.0,
            },
        );
        assert_ne!(balanced.digest(), none.digest());
        // With no passes at all the scaling is the identity, which is what makes
        // the comparison above meaningful rather than a comparison of two
        // arbitrary numbers.
        assert!(none.row().iter().all(|value| *value == 1.0));
        assert!(none.column().iter().all(|value| *value == 1.0));
    }

    /// The pass has to do something, or every later claim about it is empty.
    #[test]
    fn equilibration_reduces_the_spread_of_entry_magnitudes() {
        let program = badly_scaled();
        let scaled = Preconditioner::new(&program, settings());
        let spread = |scale: Option<&Preconditioner>| {
            let magnitudes: Vec<f64> = program
                .row_major()
                .entries()
                .map(|(r, c, value)| match scale {
                    Some(p) => (p.row()[r] * value * p.column()[c as usize]).abs(),
                    None => value.abs(),
                })
                .filter(|value| *value > 0.0)
                .collect();
            let max = magnitudes.iter().copied().fold(f64::MIN, f64::max);
            let min = magnitudes.iter().copied().fold(f64::MAX, f64::min);
            max / min
        };
        assert!(
            spread(Some(&scaled)) < spread(None) / 1.0e6,
            "equilibration must materially reduce the magnitude spread"
        );
    }

    #[test]
    fn settings_outside_the_accepted_range_are_refused() {
        assert!(
            PreconditionerSettings {
                ruiz_passes: 101,
                pock_chambolle_alpha: 1.0,
            }
            .validate()
            .is_err()
        );
        assert!(
            PreconditionerSettings {
                ruiz_passes: 10,
                pock_chambolle_alpha: f64::NAN,
            }
            .validate()
            .is_err()
        );
        assert!(settings().validate().is_ok());
    }
}
