//! Taillard instance generation under SPEC-0008 requirements 22 to 24.
//!
//! The generator is Taillard's own, from "Benchmarks for basic scheduling
//! problems", European Journal of Operational Research 64 (1993) 278-285. The
//! procedures and the per-instance seeds are transcribed from that paper in
//! OR-Library's `flowshop2.txt`, contributed by Mattfeld and Vaessens.
//!
//! Generating rather than downloading is ADR-0007's decision. It keeps the
//! acceptance gate independent of a third-party host, and it lets a manifest
//! record how an instance arose rather than only what its bytes hash to.
//! Requirement 23 is what keeps that honest: the generated matrix is asserted
//! against a committed copy of the paper's published verification instance.
//!
//! This is deliberately not a general-purpose random number generator. It is one
//! specific published algorithm, reproduced exactly, and a "better" generator here
//! would be a wrong answer.

use optimizer_core::{ErrorKind, ValidationError};

use crate::instance::{
    FlowShopDocument, FlowShopInstance, MAX_JOBS, MAX_MACHINES, SCHEDULE_SCHEMA_VERSION,
};

/// Name recorded in a benchmark manifest's generator block.
pub const GENERATOR_NAME: &str = "taillard-1993-flow-shop";

/// Taillard's Lehmer generator, seeded per instance.
///
/// The constants are the "minimal standard" multiplicative congruential
/// parameters with Schrage's decomposition, so every intermediate product fits in
/// a signed 32-bit integer. They are reproduced exactly rather than modernized:
/// changing them would change every generated instance.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Lehmer {
    seed: i64,
}

impl Lehmer {
    const M: i64 = 2_147_483_647;
    const A: i64 = 16_807;
    const B: i64 = 127_773;
    const C: i64 = 2_836;

    /// Start from a published time seed.
    pub fn new(seed: u32) -> Self {
        Self {
            seed: i64::from(seed),
        }
    }

    /// Next value uniformly in `low..=high`, advancing the seed in place.
    ///
    /// The paper updates its seed by reference, which is why this takes `&mut
    /// self`: a copy-and-return generator would repeat the same draw.
    pub fn next_in(&mut self, low: u32, high: u32) -> u32 {
        let k = self.seed / Self::B;
        self.seed = Self::A * (self.seed % Self::B) - k * Self::C;
        if self.seed < 0 {
            self.seed += Self::M;
        }
        // The paper computes `low + trunc(value_0_1 * (high - low + 1))` in 64-bit
        // floating point. The span of a supported instance is small enough that
        // this is exact, and it is written the paper's way rather than as integer
        // arithmetic so the transcription is checkable against the source.
        let value_0_1 = self.seed as f64 / Self::M as f64;
        let span = f64::from(high - low + 1);
        low + (value_0_1 * span) as u32
    }
}

/// Generate the processing times of one Taillard flow-shop instance.
///
/// Machines are the outer loop and jobs the inner one, matching the paper's
/// `generate_flow_shop`. Transposing this loop order produces a different
/// instance from the same seed, which is why requirement 23 exists.
///
/// # Errors
///
/// Returns an unsupported failure when the requested shape exceeds the document
/// limits, and whatever [`FlowShopInstance::new`] returns otherwise.
pub fn taillard_instance(
    instance_id: impl Into<String>,
    seed: u32,
    jobs: u32,
    machines: u32,
) -> Result<FlowShopInstance, ValidationError> {
    if jobs == 0 || machines == 0 {
        return Err(ValidationError::new(
            ErrorKind::Structural,
            "jobs and machines must be positive",
        ));
    }
    if jobs > MAX_JOBS || machines > MAX_MACHINES {
        return Err(ValidationError::new(
            ErrorKind::Unsupported,
            format!(
                "requested {jobs} jobs and {machines} machines, above the supported {MAX_JOBS} and {MAX_MACHINES}"
            ),
        ));
    }
    let mut generator = Lehmer::new(seed);
    let mut processing_times = Vec::with_capacity(machines as usize);
    for _ in 0..machines {
        let mut row = Vec::with_capacity(jobs as usize);
        for _ in 0..jobs {
            row.push(generator.next_in(1, 99));
        }
        processing_times.push(row);
    }
    FlowShopInstance::new(FlowShopDocument {
        schema_version: SCHEDULE_SCHEMA_VERSION,
        instance_id: instance_id.into(),
        jobs,
        machines,
        processing_times,
    })
}

/// One published Taillard instance: its name, seed and dimensions.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct PublishedInstance {
    /// Instance name as the paper and OR-Library label it.
    pub id: &'static str,
    /// Published time seed.
    pub seed: u32,
    /// Job count.
    pub jobs: u32,
    /// Machine count.
    pub machines: u32,
}

/// The 20-job, 5-machine class, `ta001` through `ta010`.
///
/// This is the frozen development subset. It is the paper's smallest published
/// class, which keeps the committed documents small enough for Git while still
/// being far beyond what exhaustive enumeration can check. Enlarging this list, or
/// changing any seed in it, is a split change and requires a new decision record
/// and experiment record under requirement 24.
pub const DEVELOPMENT_SUBSET: [PublishedInstance; 10] = [
    PublishedInstance {
        id: "ta001",
        seed: 873_654_221,
        jobs: 20,
        machines: 5,
    },
    PublishedInstance {
        id: "ta002",
        seed: 379_008_056,
        jobs: 20,
        machines: 5,
    },
    PublishedInstance {
        id: "ta003",
        seed: 1_866_992_158,
        jobs: 20,
        machines: 5,
    },
    PublishedInstance {
        id: "ta004",
        seed: 216_771_124,
        jobs: 20,
        machines: 5,
    },
    PublishedInstance {
        id: "ta005",
        seed: 495_070_989,
        jobs: 20,
        machines: 5,
    },
    PublishedInstance {
        id: "ta006",
        seed: 402_959_317,
        jobs: 20,
        machines: 5,
    },
    PublishedInstance {
        id: "ta007",
        seed: 1_369_363_414,
        jobs: 20,
        machines: 5,
    },
    PublishedInstance {
        id: "ta008",
        seed: 2_021_925_980,
        jobs: 20,
        machines: 5,
    },
    PublishedInstance {
        id: "ta009",
        seed: 573_109_518,
        jobs: 20,
        machines: 5,
    },
    PublishedInstance {
        id: "ta010",
        seed: 88_325_120,
        jobs: 20,
        machines: 5,
    },
];

impl PublishedInstance {
    /// Generate this instance from its published seed.
    ///
    /// # Errors
    ///
    /// Returns whatever [`taillard_instance`] returns.
    pub fn generate(&self) -> Result<FlowShopInstance, ValidationError> {
        taillard_instance(self.id, self.seed, self.jobs, self.machines)
    }
}

/// One instance from each published shape, `ta001` through `ta111`.
///
/// This is the scale subset. It exists to locate a crossover, which is a question
/// about how cost grows with instance shape, so it takes the first instance of each
/// of the paper's twelve classes rather than ten instances of one class. A sweep
/// needs range; it does not need a sample, and taking ten per class would commit
/// twelve times the bytes to answer the same question less clearly.
///
/// It deliberately overlaps [`DEVELOPMENT_SUBSET`] at `ta001`. That instance is the
/// small end of the sweep and the one where a device is expected to lose, which is
/// the measurement's own falsification check under SPEC-0010 requirement 22; leaving
/// it out would remove the row most able to show a measurement is wrong.
///
/// Seeds are transcribed from the same published table as the development subset,
/// and the paper reuses some seeds across shapes: `ta051` and `ta071` share one.
/// A seed is therefore unique only together with its shape, and anything asserting
/// uniqueness must say so, or it will fail on the source's own data.
///
/// This list is a split. Changing it, or any seed in it, requires a new decision
/// record and experiment record under requirement 24, exactly as the development
/// subset does.
pub const SCALE_SUBSET: [PublishedInstance; 12] = [
    PublishedInstance {
        id: "ta001",
        seed: 873_654_221,
        jobs: 20,
        machines: 5,
    },
    PublishedInstance {
        id: "ta011",
        seed: 587_595_453,
        jobs: 20,
        machines: 10,
    },
    PublishedInstance {
        id: "ta021",
        seed: 479_340_445,
        jobs: 20,
        machines: 20,
    },
    PublishedInstance {
        id: "ta031",
        seed: 1_328_042_058,
        jobs: 50,
        machines: 5,
    },
    PublishedInstance {
        id: "ta041",
        seed: 1_958_948_863,
        jobs: 50,
        machines: 10,
    },
    PublishedInstance {
        id: "ta051",
        seed: 1_539_989_115,
        jobs: 50,
        machines: 20,
    },
    PublishedInstance {
        id: "ta061",
        seed: 896_678_084,
        jobs: 100,
        machines: 5,
    },
    PublishedInstance {
        id: "ta071",
        seed: 1_539_989_115,
        jobs: 100,
        machines: 10,
    },
    PublishedInstance {
        id: "ta081",
        seed: 450_926_852,
        jobs: 100,
        machines: 20,
    },
    PublishedInstance {
        id: "ta091",
        seed: 471_503_978,
        jobs: 200,
        machines: 10,
    },
    PublishedInstance {
        id: "ta101",
        seed: 2_013_025_619,
        jobs: 200,
        machines: 20,
    },
    PublishedInstance {
        id: "ta111",
        seed: 1_368_624_604,
        jobs: 500,
        machines: 20,
    },
];
