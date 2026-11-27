//! Bounded overlap inside one assessment boundary; no speculative solver steps.
use std::time::Instant;

#[derive(Default)]
pub(crate) struct Timing {
    pub proof_ns: u128,
    pub witness_ns: u128,
    pub wall_ns: u128,
}

/// Both tasks finish before returning, including on errors. Prefer proof errors,
/// matching the serial proof-then-output order. There is exactly one pending proof.
pub(crate) fn run<P: Send, W, E: Send>(
    proof: impl FnOnce() -> Result<P, E> + Send,
    witness: impl FnOnce() -> Result<W, E>,
) -> Result<(P, W, Timing), E> {
    let start = Instant::now();
    std::thread::scope(|scope| {
        let job = scope.spawn(|| {
            let start = Instant::now();
            let result = proof();
            (result, start.elapsed().as_nanos())
        });
        let begin = Instant::now();
        let output = witness();
        let witness_ns = begin.elapsed().as_nanos();
        let (proof, proof_ns) = match job.join() {
            Ok(result) => result,
            Err(error) => std::panic::resume_unwind(error),
        };
        Ok((
            proof?,
            output?,
            Timing {
                proof_ns,
                witness_ns,
                wall_ns: start.elapsed().as_nanos(),
            },
        ))
    })
}
#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::{
        atomic::{AtomicBool, Ordering},
        mpsc,
    };
    #[test]
    fn independent_work_overlaps_and_returns_the_same_snapshot() {
        let (a, b) = mpsc::sync_channel(0);
        let (c, d) = mpsc::sync_channel(0);
        let snapshot = vec![1.0f64, -0.0, 3.0];
        let proof_snapshot = &snapshot;
        let (proof, witness, _) = run(
            move || {
                a.send(()).unwrap();
                d.recv().unwrap();
                Ok::<_, String>(
                    proof_snapshot
                        .iter()
                        .map(|x| x.to_bits())
                        .collect::<Vec<_>>(),
                )
            },
            || {
                b.recv().unwrap();
                c.send(()).unwrap();
                Ok(snapshot.iter().map(|x| x.to_bits()).collect::<Vec<_>>())
            },
        )
        .unwrap();
        assert_eq!(proof, witness);
    }
    #[test]
    fn output_failure_still_joins_the_proof_worker() {
        let finished = AtomicBool::new(false);
        let result = run(
            || {
                finished.store(true, Ordering::SeqCst);
                Ok::<_, &str>(())
            },
            || Err::<(), _>("output"),
        );
        assert!(matches!(result, Err("output")));
        assert!(finished.load(Ordering::SeqCst));
    }
    #[test]
    fn proof_failure_has_serial_error_priority() {
        assert!(matches!(
            run(|| Err::<(), _>("proof"), || Err::<(), _>("output")),
            Err("proof")
        ));
    }
}
