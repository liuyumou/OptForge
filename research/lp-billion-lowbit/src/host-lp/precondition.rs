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

use optimizer_core::PreconditionerSettings;

use crate::problem::LinearProgram;
use crate::reduce::tree_sum;

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
        let _component_scope = optimizer_core::lp_cost::scope("preconditioning");
        let rows = program.row_count();
        let columns = program.column_count();
        let mut row = vec![1.0f64; rows];
        let mut column = vec![1.0f64; columns];

        let ruiz_cost = optimizer_core::lp_cost::scope("ruiz_scaling");
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

        drop(ruiz_cost);
        if settings.pock_chambolle_alpha > 0.0 {
            let _cost = optimizer_core::lp_cost::scope("pock_chambolle_scaling");
            let alpha = settings.pock_chambolle_alpha;
            // These are sums, so they go through the fixed reduction rather than
            // being accumulated in whatever order the entries arrive.
            // Both orientations are in the original term order. Compute totals
            // with the old diagonals before updating either diagonal; scratch is
            // bounded by one line per worker instead of two full term graphs.
            let totals = |transpose: bool| {
                let matrix = if transpose { program.column_major() } else { program.row_major() };
                std::thread::scope(|scope| {
                    let handles: Vec<_> = (0..4).map(|worker| {
                        let row = &row;
                        let column = &column;
                        scope.spawn(move || {
                            let mut terms = Vec::new();
                            (matrix.lines() * worker / 4..matrix.lines() * (worker + 1) / 4)
                                .map(|major| {
                                    terms.clear();
                                    let (indices, values) = matrix.line(major);
                                    terms.extend(indices.iter().zip(values).map(|(&minor, &value)| {
                                        let (r, c) = if transpose { (minor as usize, major) } else { (major, minor as usize) };
                                        let scaled = (row[r] * value * column[c]).abs();
                                        scaled.powf(if transpose { alpha } else { 2.0 - alpha })
                                    }));
                                    compact_sum(&terms)
                                }).collect::<Vec<_>>()
                        })
                    }).collect();
                    handles.into_iter().flat_map(|h| h.join().expect("precondition worker")).collect::<Vec<_>>()
                })
            };
            let row_totals = totals(false);
            let column_totals = totals(true);
            for (index, &total) in row_totals.iter().enumerate() {
                if total > 0.0 {
                    row[index] /= total.sqrt();
                }
            }
            for (index, &total) in column_totals.iter().enumerate() {
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

    #[cfg(feature = "precision-research")]
    pub(crate) fn explicit(
        row: Vec<f64>,
        column: Vec<f64>,
        settings: PreconditionerSettings,
    ) -> Self {
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

fn segment<const N: usize>(v: &[f64]) -> f64 {
    let mut buffer = [0.; N];
    if N < crate::reduce::SEGMENT {
        for (a, &b) in buffer.iter_mut().zip(v) {
            *a = b + 0.;
        }
    } else {
        buffer[..v.len()].copy_from_slice(v);
    }
    let mut stride = N / 2;
    while stride > 0 {
        for i in 0..stride {
            buffer[i] += buffer[i + stride];
        }
        stride /= 2;
    }
    buffer[0]
}

/// Keep the same 1024-leaf partition and butterfly. For a short segment, all
/// omitted upper levels only add +0.0 to each live leaf. Execute that once
/// (including -0.0 normalization), then the exact remaining tree. Nonfinite
/// inputs take the original implementation, including its NaN behavior.
pub fn compact_sum(values: &[f64]) -> f64 {
    if values.is_empty() {
        return 0.;
    }
    if values.iter().any(|x| !x.is_finite()) {
        return tree_sum(values);
    }
    let segment = |v: &[f64]| match v.len().next_power_of_two() {
        1 => segment::<1>(v),
        2 => segment::<2>(v),
        4 => segment::<4>(v),
        8 => segment::<8>(v),
        16 => segment::<16>(v),
        32 => segment::<32>(v),
        64 => segment::<64>(v),
        128 => segment::<128>(v),
        256 => segment::<256>(v),
        512 => segment::<512>(v),
        _ => segment::<1024>(v),
    };
    if values.len() <= crate::reduce::SEGMENT {
        return segment(values);
    }
    let level: Vec<_> = values.chunks(crate::reduce::SEGMENT).map(segment).collect();
    compact_sum(&level)
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
