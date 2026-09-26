//! Host-side certification of a dual bound, under SPEC-0011 requirements 11 to 13
//! and ADR-0010.
//!
//! This is the procedure the whole contract rests on, and ADR-0010 says so: the
//! engine can obtain a dual bound from a method that proves nothing, and the
//! entire safety of that rests here.
//!
//! The tempting alternative is to declare a bound once the device's residuals
//! fall below a tolerance. That is wrong for a reason that has nothing to do with
//! tolerances: the residuals are computed by the same device, in the same kernels,
//! from the same iterates, as the bound they would be vouching for. A device that
//! is wrong is wrong in both. SPEC-0008 requirement 8 refused this shape of
//! argument once already, by keeping the makespan recurrence independent of
//! everything that proposes a schedule.
//!
//! So nothing here reads a residual, a norm or an objective the device computed.
//! The only device-produced numbers this module touches are the `m` dual
//! multipliers, and they enter inequalities that hold for *every* real number.
//!
//! # Why the result is a bound for an arbitrary untrusted `y`
//!
//! Write the program as `min cᵀx + d` subject to `ρ ≤ A x ≤ σ` and `l ≤ x ≤ u`.
//! Take any vector `ŷ` and define the reduced costs `z = c − Aᵀŷ` from the
//! model's own coefficients. Then for every `x`, identically, because `z` was
//! *defined* that way rather than reported:
//!
//! ```text
//! cᵀx = (z + Aᵀŷ)ᵀx = zᵀx + ŷᵀ(A x)
//! ```
//!
//! Now bound each term using nothing but primal feasibility. If `ŷᵢ > 0` then
//! `ŷᵢ(Ax)ᵢ ≥ ŷᵢρᵢ`, because `(Ax)ᵢ ≥ ρᵢ` and the multiplier is positive; if
//! `ŷᵢ < 0` then `ŷᵢ(Ax)ᵢ ≥ ŷᵢσᵢ`, because `(Ax)ᵢ ≤ σᵢ` and a negative multiplier
//! reverses the inequality. The same argument applies to `zⱼxⱼ` against `lⱼ` and
//! `uⱼ`. Summing gives `cᵀx + d ≥ L` for every feasible `x`, so `L` is a lower
//! bound on the optimum.
//!
//! No step in that argument mentions where `ŷ` came from, and no step assumes it
//! is near optimal. A bad guess makes the bounded terms small, so `L` is weak; it
//! cannot make `L` invalid. That is requirement 13, and it is why the procedure is
//! a certification rather than an optimality test.
//!
//! # Where it cannot produce a bound
//!
//! The row side always admits a repair: if `ŷᵢ` has the sign whose bound is
//! infinite, setting it to zero costs the term but breaks no identity, because
//! `z` is recomputed from the repaired `ŷ`.
//!
//! The column side admits none. `zⱼ` is *determined* by `ŷ`, so adjusting one
//! reduced cost on its own would falsify `z = c − Aᵀŷ` and the number would stop
//! being a bound. When `zⱼ > 0` and `lⱼ = −∞`, the infimum of `zⱼxⱼ` really is
//! `−∞` and no finite number bounds it. The honest answer there is no bound,
//! naming the variable that blocked it. Substituting a large finite number would
//! fabricate one, and is the single most dangerous shortcut available in this
//! module.

use optimizer_core::Model;

use crate::outward::{self, Enclosure};
use crate::problem::LinearProgram;

/// Why no bound could be produced.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum NoBound {
    /// A variable contribution cannot be bounded finitely: its reduced-cost
    /// enclosure includes a sign whose variable bound is infinite.
    /// Names the original variable ID; this does not prove the LP is unbounded.
    UnboundedVariable {
        /// The original variable ID that blocked the bound.
        variable_id: u32,
    },
    /// An input multiplier was not finite. A domain check on the input, not a
    /// judgement about whether the device computed well.
    NonfiniteMultiplier {
        /// Row index of the offending multiplier.
        row: usize,
    },
    /// The arithmetic produced a nonfinite intermediate, so no finite bound can
    /// be reported.
    NonfiniteArithmetic,
}

impl std::fmt::Display for NoBound {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::UnboundedVariable { variable_id } => write!(
                formatter,
                "no certified bound: variable {variable_id} has an infinite bound on the side \
                 its reduced-cost enclosure needs, so no finite contribution is certified"
            ),
            Self::NonfiniteMultiplier { row } => write!(
                formatter,
                "no certified bound: the multiplier for row {row} is not finite"
            ),
            Self::NonfiniteArithmetic => write!(
                formatter,
                "no certified bound: the certification arithmetic overflowed"
            ),
        }
    }
}

/// A bound the host proved, together with what it took to prove it.
#[derive(Clone, Debug, PartialEq)]
pub struct Certificate {
    /// The certified bound, in the caller's own objective direction.
    ///
    /// A lower bound for a minimization and an upper bound for a maximization,
    /// which is the same statement expressed in the caller's terms.
    pub bound: f64,
    /// The nearest-rounded weak-duality value, for diagnosis only.
    pub unadjusted: f64,
    /// An outward upper bound on the adjustment from `unadjusted` to `bound`.
    /// The authoritative bound is computed directly, not by subtracting this
    /// diagnostic with round-to-nearest arithmetic.
    pub allowance: f64,
    /// How many multipliers the repair had to zero.
    ///
    /// Not a failure. A high count means the guess pointed at rows whose bound is
    /// infinite on that side, so the bound will be weak.
    pub repaired: usize,
}

/// Certify a dual bound from an untrusted multiplier vector.
///
/// `y` is indexed by constraint position in the canonical program, which is the
/// model's constraints sorted by ID. It is untrusted in the strongest sense: no
/// property of it is assumed, and every value of it produces either a valid bound
/// or an explicit refusal.
///
/// # Errors
///
/// Returns [`NoBound`] when this enclosure cannot establish a finite bound.
/// In particular, sign uncertainty on an infinite variable side can prevent
/// certification even when a tighter calculation would succeed.
pub fn certify(program: &LinearProgram, y: &[f64]) -> Result<Certificate, NoBound> {
    let _component_scope = optimizer_core::lp_cost::scope("dual_certification");
    assert_eq!(
        y.len(),
        program.row_count(),
        "a multiplier vector must have one entry per constraint"
    );

    for (row, value) in y.iter().enumerate() {
        if !value.is_finite() {
            return Err(NoBound::NonfiniteMultiplier { row });
        }
    }

    // Step 1: repair. If a multiplier has the sign whose row bound is infinite,
    // its term would be unbounded below, so it is zeroed. This is a projection
    // onto the multipliers the rows admit; it breaks no identity because the
    // reduced costs below are computed from the repaired vector.
    let mut repaired_y = y.to_vec();
    let mut repaired = 0usize;
    for (row, value) in repaired_y.iter_mut().enumerate() {
        let range = program.rows()[row];
        let unusable = (*value > 0.0 && !range.lower.is_finite())
            || (*value < 0.0 && !range.upper.is_finite());
        if unusable {
            *value = 0.0;
            repaired += 1;
        }
    }

    // Enclose every term from the original data. A zero rounded reduced cost
    // still carries the full interval through the variable's two bound sides.
    let mut terms = Vec::with_capacity(program.row_count() + program.column_count() + 1);
    for (row, value) in repaired_y.iter().enumerate() {
        terms.push(endpoint(*value, program.rows()[row], None)?);
    }
    for column in 0..program.column_count() {
        let (rows, coefficients) = program.column_major().line(column);
        let products = rows
            .iter()
            .zip(coefficients)
            .map(|(row, coefficient)| {
                Enclosure::product(*coefficient, repaired_y[*row as usize])
                    .ok_or(NoBound::NonfiniteArithmetic)
            })
            .collect::<Result<Vec<_>, _>>()?;
        let transposed = outward::sum(&products).ok_or(NoBound::NonfiniteArithmetic)?;
        let reduced = Enclosure::point(program.objective()[column])
            .and_then(|cost| cost.subtract(transposed))
            .ok_or(NoBound::NonfiniteArithmetic)?;
        let range = program.columns()[column];
        let id = Some(program.variable_ids()[column]);
        let low = endpoint(reduced.lower, range, id)?;
        let high = endpoint(reduced.upper, range, id)?;
        let rounded = endpoint(reduced.rounded, range, id)?.rounded;
        // phi(z) = inf_x z*x is concave. Its minimum over the enclosure is
        // attained at an endpoint; the only possible interior maximum is z=0.
        let upper = if reduced.lower <= 0.0 && reduced.upper >= 0.0 {
            low.upper.max(high.upper).max(0.0)
        } else {
            low.upper.max(high.upper)
        };
        terms.push(
            Enclosure::new(low.lower.min(high.lower), upper, rounded)
                .ok_or(NoBound::NonfiniteArithmetic)?,
        );
    }
    terms.push(Enclosure::point(program.offset()).ok_or(NoBound::NonfiniteArithmetic)?);
    let total = outward::sum(&terms).ok_or(NoBound::NonfiniteArithmetic)?;
    let allowance = Enclosure::point(total.rounded)
        .and_then(|raw| raw.subtract(Enclosure::point(total.lower)?))
        .ok_or(NoBound::NonfiniteArithmetic)?
        .upper
        .max(0.0);
    Ok(Certificate {
        bound: program.to_original_objective(total.lower),
        unadjusted: program.to_original_objective(total.rounded),
        allowance,
        repaired,
    })
}

/// Enclose phi(z) for one exact endpoint. Zero needs neither infinite side.
fn endpoint(z: f64, range: crate::Range, variable: Option<u32>) -> Result<Enclosure, NoBound> {
    if z == 0.0 {
        return Ok(Enclosure::ZERO);
    }
    let bound = if z > 0.0 { range.lower } else { range.upper };
    if !bound.is_finite() {
        return Err(match variable {
            Some(variable_id) => NoBound::UnboundedVariable { variable_id },
            None => NoBound::NonfiniteArithmetic,
        });
    }
    Enclosure::product(z, bound).ok_or(NoBound::NonfiniteArithmetic)
}

/// Conservative gap assessment in absolute objective units, shared by both LP backends.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct GapAssessment {
    /// Nonnegative outward upper bound on the sense-directed objective gap.
    pub upper: f64,
    /// Whether the whole gap enclosure fits the caller's existing tolerance policy.
    /// The caller must additionally require original-model candidate feasibility.
    pub closed: bool,
}

/// Assess the gap using an outward objective enclosure, including its offset.
///
/// `primal` is in original model units and canonical variable order. `bound` must
/// already have been certified for this program and is in the original sense;
/// this function does not certify a supplied bound or establish primal feasibility.
/// Returns `None` for wrong vector length, invalid tolerances, or any arithmetic
/// that cannot be enclosed finitely. The model's nearest-rounded reported objective
/// is deliberately not an input to a mathematical termination decision.
#[must_use]
pub fn assess_gap(
    program: &LinearProgram,
    primal: &[f64],
    bound: f64,
    tolerances: optimizer_core::Tolerances,
) -> Option<GapAssessment> {
    let _component_scope = optimizer_core::lp_cost::scope("gap_assessment");
    if primal.len() != program.column_count() || tolerances.validate().is_err() {
        return None;
    }
    let mut terms = program
        .objective()
        .iter()
        .zip(primal)
        .map(|(cost, value)| Enclosure::product(*cost, *value))
        .collect::<Option<Vec<_>>>()?;
    terms.push(Enclosure::point(program.offset())?);
    let objective = outward::sum(&terms)?;
    // Sign conversion is an involution: it also maps a reported bound back to min.
    let bound = program.to_original_objective(bound);
    let gap = objective.subtract(Enclosure::point(bound)?)?;
    // A lower bound on the requested scale for EVERY objective in the interval.
    // Using its maximum magnitude would increase the tolerance without evidence.
    let magnitude = if objective.lower <= 0.0 && objective.upper >= 0.0 {
        0.0
    } else {
        objective.lower.abs().min(objective.upper.abs())
    };
    let scale = magnitude.max(bound.abs());
    let allowance = Enclosure::product(tolerances.relative, scale)?
        .add(Enclosure::point(tolerances.absolute)?)?;
    Some(GapAssessment {
        upper: gap.upper.max(0.0),
        closed: gap.lower >= -tolerances.absolute && gap.upper <= allowance.lower,
    })
}

/// Certify directly from an original model.
///
/// # Errors
///
/// Returns the conversion failure for a discrete model, or [`NoBound`] as
/// [`certify`] does.
pub fn certify_model(
    model: &Model,
    y: &[f64],
) -> Result<Result<Certificate, NoBound>, optimizer_core::ValidationError> {
    let program = LinearProgram::new(model)?;
    Ok(certify(&program, y))
}

#[cfg(test)]
mod tests {
    use super::*;
    use optimizer_core::{
        Bound, Constraint, Domain, LinearTerm, Model, ModelDocument, Objective, ObjectiveSense,
        SCHEMA_VERSION, Variable,
    };

    fn finite(value: f64) -> Bound {
        Bound::Finite { value }
    }

    /// A two-variable program with every bound finite.
    ///
    /// `min c·x + offset` subject to `row_lower ≤ x0 + 2 x1 ≤ row_upper`,
    /// `0 ≤ xj ≤ 1`.
    fn program(
        sense: ObjectiveSense,
        cost: [f64; 2],
        offset: f64,
        row: (Bound, Bound),
        upper: [Bound; 2],
    ) -> LinearProgram {
        let model = Model::new(ModelDocument {
            schema_version: SCHEMA_VERSION,
            model_id: "certify".to_string(),
            variables: vec![
                Variable {
                    id: 0,
                    domain: Domain::Continuous,
                    lower: finite(0.0),
                    upper: upper[0],
                },
                Variable {
                    id: 1,
                    domain: Domain::Continuous,
                    lower: finite(0.0),
                    upper: upper[1],
                },
            ],
            constraints: vec![Constraint {
                id: 0,
                lower: row.0,
                upper: row.1,
                terms: vec![
                    LinearTerm {
                        variable_id: 0,
                        coefficient: 1.0,
                    },
                    LinearTerm {
                        variable_id: 1,
                        coefficient: 2.0,
                    },
                ],
            }],
            objective: Objective {
                sense,
                offset,
                terms: vec![
                    LinearTerm {
                        variable_id: 0,
                        coefficient: cost[0],
                    },
                    LinearTerm {
                        variable_id: 1,
                        coefficient: cost[1],
                    },
                ],
            },
        })
        .expect("valid");
        LinearProgram::new(&model).expect("continuous")
    }

    fn boxed(sense: ObjectiveSense, cost: [f64; 2], offset: f64) -> LinearProgram {
        program(
            sense,
            cost,
            offset,
            (Bound::NegativeInfinity, finite(1.5)),
            [finite(1.0), finite(1.0)],
        )
    }

    /// Every feasible point of a two-variable program on a fine grid.
    ///
    /// Independent of the certification by construction: it evaluates the
    /// original objective directly and knows nothing about duals. Weak duality
    /// says the bound is below the objective at *every* feasible point, so this
    /// tests the claim itself rather than a consequence of it, and it needs no
    /// optimum and no second solver to do it.
    fn feasible_objectives(program: &LinearProgram) -> Vec<f64> {
        let steps = 60;
        let mut objectives = Vec::new();
        let axis = |index: usize| -> Vec<f64> {
            let range = program.columns()[index];
            let lower = range.lower;
            let upper = if range.upper.is_finite() {
                range.upper
            } else {
                lower + 10.0
            };
            (0..=steps)
                .map(|step| lower + (upper - lower) * f64::from(step) / f64::from(steps))
                .collect()
        };
        for x0 in axis(0) {
            for x1 in axis(1) {
                let activity = x0 + 2.0 * x1;
                let row = program.rows()[0];
                if activity < row.lower - 1e-12 || activity > row.upper + 1e-12 {
                    continue;
                }
                let internal =
                    program.objective()[0] * x0 + program.objective()[1] * x1 + program.offset();
                objectives.push(program.to_original_objective(internal));
            }
        }
        assert!(
            !objectives.is_empty(),
            "the grid must contain feasible points or the test asserts nothing"
        );
        objectives
    }

    fn assert_valid(program: &LinearProgram, y: &[f64], label: &str) {
        let certificate = certify(program, y).expect("a boxed program always certifies");
        for objective in feasible_objectives(program) {
            match program.sense() {
                ObjectiveSense::Minimize => assert!(
                    certificate.bound <= objective,
                    "{label}: bound {} exceeded a feasible objective {objective}",
                    certificate.bound
                ),
                ObjectiveSense::Maximize => assert!(
                    certificate.bound >= objective,
                    "{label}: bound {} fell below a feasible objective {objective}",
                    certificate.bound
                ),
            }
        }
    }

    /// Requirement 13, the central claim: valid for an arbitrary dual vector.
    ///
    /// The multipliers include a sign-flipped one, an absurdly scaled one and
    /// zero, none of which is near optimal. If validity depended on the guess
    /// being good, one of these would break it.
    #[test]
    fn a_certified_bound_is_valid_for_an_arbitrary_dual_vector() {
        for (label, y) in [
            ("zero", 0.0),
            ("small positive", 0.25),
            ("negative", -3.0),
            ("optimal-ish", -1.0),
            ("absurd", -1.0e18),
            ("absurd positive", 1.0e18),
        ] {
            for sense in [ObjectiveSense::Minimize, ObjectiveSense::Maximize] {
                let program = boxed(sense, [-1.0, -3.0], 2.5);
                assert_valid(&program, &[y], label);
            }
        }
    }

    /// Requirement 13 again, in the form the specification's acceptance section
    /// names: a deliberately early-stopped iterate still certifies.
    #[test]
    fn a_bound_from_a_deliberately_early_stopped_iterate_is_still_valid() {
        let program = boxed(ObjectiveSense::Minimize, [-1.0, -3.0], 0.0);
        // An "iterate" one step from its starting point, nowhere near optimal.
        assert_valid(&program, &[-0.01], "barely started");
        let early = certify(&program, &[-0.01]).unwrap();
        let better = certify(&program, &[-1.5]).unwrap();
        assert!(
            early.bound < better.bound,
            "a worse guess must give a weaker bound, not an invalid one"
        );
    }

    /// The rounding allowance is not decoration, and this is the instrument that
    /// proves it.
    ///
    /// The argument in the module header is exact in the reals, so a violation is
    /// pure `f64` rounding and appears only where the margin is zero: at the
    /// optimal dual, where complementary slackness makes every bounded term tight.
    /// Away from it the slack is of order the reduced costs and rounding at 1e-16
    /// cannot reach across. These coefficients were found by searching that
    /// regime, with `y` set to the multiplier that zeroes the first variable's
    /// reduced cost.
    ///
    /// Without the outward adjustment the reported bound would exceed the true optimum by
    /// about 6.6e-14 -- a bound stronger than the truth, which is the one failure
    /// mode this module exists to prevent. Returning the raw value as the bound
    /// fails this test; the allowance field itself is only diagnostic.
    #[test]
    fn the_outward_adjustment_is_shown_to_matter() {
        let a = [0.206_433_577_151_847_46_f64, 9.355_369_574_607_812];
        let cost = [8.345_320_531_948_929_f64, 7.939_554_807_831_865];
        let rhs = 9.398_501_687_559_822_f64;

        let model = Model::new(ModelDocument {
            schema_version: SCHEMA_VERSION,
            model_id: "rounding".to_string(),
            variables: vec![
                Variable {
                    id: 0,
                    domain: Domain::Continuous,
                    lower: finite(0.0),
                    upper: finite(1.0),
                },
                Variable {
                    id: 1,
                    domain: Domain::Continuous,
                    lower: finite(0.0),
                    upper: finite(1.0),
                },
            ],
            constraints: vec![Constraint {
                id: 0,
                lower: finite(rhs),
                upper: finite(rhs),
                terms: vec![
                    LinearTerm {
                        variable_id: 0,
                        coefficient: a[0],
                    },
                    LinearTerm {
                        variable_id: 1,
                        coefficient: a[1],
                    },
                ],
            }],
            objective: Objective {
                sense: ObjectiveSense::Minimize,
                offset: 0.0,
                terms: vec![
                    LinearTerm {
                        variable_id: 0,
                        coefficient: cost[0],
                    },
                    LinearTerm {
                        variable_id: 1,
                        coefficient: cost[1],
                    },
                ],
            },
        })
        .expect("valid");
        let program = LinearProgram::new(&model).expect("continuous");

        // The feasible set is a segment, so its optimum is at an endpoint. Both
        // endpoints are computed here directly rather than sampled, because the
        // effect being demonstrated is smaller than any grid would resolve.
        let mut optimum = f64::INFINITY;
        for x0 in [0.0_f64, 1.0] {
            let x1 = (rhs - a[0] * x0) / a[1];
            if (0.0..=1.0).contains(&x1) {
                optimum = optimum.min(cost[0] * x0 + cost[1] * x1);
            }
        }
        for x1 in [0.0_f64, 1.0] {
            let x0 = (rhs - a[1] * x1) / a[0];
            if (0.0..=1.0).contains(&x0) {
                optimum = optimum.min(cost[0] * x0 + cost[1] * x1);
            }
        }
        assert!(optimum.is_finite(), "the instance must be feasible");

        let y = cost[0] / a[0];
        let certificate = certify(&program, &[y]).expect("certifies");

        assert!(
            certificate.unadjusted > optimum,
            "this instance exists because the raw sum exceeds the optimum; \
             if it stops doing so the test no longer demonstrates anything"
        );
        assert!(
            certificate.bound <= optimum,
            "the adjusted bound must be a valid bound: {} vs {optimum}",
            certificate.bound
        );
    }

    /// The row-side repair, which always exists.
    #[test]
    fn a_multiplier_whose_row_bound_is_infinite_is_zeroed_rather_than_refused() {
        // Row is `x0 + 2 x1 <= 1.5`, so its lower bound is infinite and a
        // positive multiplier has no finite term.
        let program = boxed(ObjectiveSense::Minimize, [-1.0, -3.0], 0.0);
        let certificate = certify(&program, &[5.0]).expect("the repair keeps this certifiable");
        assert_eq!(certificate.repaired, 1);
        // Zeroing the multiplier is the same as having been handed zero.
        let zeroed = certify(&program, &[0.0]).unwrap();
        assert_eq!(certificate.bound, zeroed.bound);
        assert_valid(&program, &[5.0], "repaired");
    }

    /// The column side, where no repair exists.
    ///
    /// A free variable's reduced cost must be exactly zero for a bound to exist,
    /// and a nonzero one leaves the contribution genuinely unbounded below. The
    /// refusal names the variable, and no finite number is invented.
    #[test]
    fn an_infinite_variable_bound_on_the_side_the_repair_needs_yields_no_bound() {
        let program = program(
            ObjectiveSense::Minimize,
            [-1.0, -3.0],
            0.0,
            (Bound::NegativeInfinity, finite(1.5)),
            [Bound::PositiveInfinity, finite(1.0)],
        );
        // With y = 0 the reduced cost of x0 is -1, which points at its upper
        // bound, and that bound is infinite.
        let error = certify(&program, &[0.0]).unwrap_err();
        assert_eq!(error, NoBound::UnboundedVariable { variable_id: 0 });
    }

    /// A multiplier that is not a number is an input domain failure, reported as
    /// such rather than propagated into a NaN bound.
    #[test]
    fn a_nonfinite_multiplier_is_refused_by_row() {
        let program = boxed(ObjectiveSense::Minimize, [-1.0, -3.0], 0.0);
        assert_eq!(
            certify(&program, &[f64::NAN]).unwrap_err(),
            NoBound::NonfiniteMultiplier { row: 0 }
        );
        assert_eq!(
            certify(&program, &[f64::INFINITY]).unwrap_err(),
            NoBound::NonfiniteMultiplier { row: 0 }
        );
    }

    /// The direction is reported in the caller's terms, and the test would fail
    /// if the sense were dropped rather than merely producing a weak number.
    #[test]
    fn a_maximization_bound_is_an_upper_bound() {
        let minimize = boxed(ObjectiveSense::Minimize, [-1.0, -3.0], 2.5);
        let maximize = boxed(ObjectiveSense::Maximize, [-1.0, -3.0], 2.5);
        let low = certify(&minimize, &[-1.0]).unwrap();
        let high = certify(&maximize, &[1.0]).unwrap();
        for objective in feasible_objectives(&minimize) {
            assert!(low.bound <= objective);
        }
        for objective in feasible_objectives(&maximize) {
            assert!(high.bound >= objective);
        }
    }

    /// Certification is a pure function of the program and the multipliers, so
    /// repeating it is bit for bit identical. Requirement 8's reproducibility
    /// covers the iteration; this covers the thing that turns an iterate into a
    /// claim.
    #[test]
    fn certification_is_bitwise_repeatable() {
        let program = boxed(ObjectiveSense::Minimize, [-1.0, -3.0], 2.5);
        let first = certify(&program, &[-0.75]).unwrap();
        let second = certify(&program, &[-0.75]).unwrap();
        assert_eq!(first.bound.to_bits(), second.bound.to_bits());
    }
}
