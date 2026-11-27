//! Immutable, bounded chunks of original arrays and untrusted endpoint bits.
use crate::Result;
use optimizer_core::{Model, ObjectiveSense};
use optimizer_lp::{LinearProgram, Range};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::{
    collections::BTreeMap,
    fs::{self, OpenOptions},
    io::Write,
    path::{Path, PathBuf},
    time::Instant,
};

pub const CHUNK: usize = 32 << 20;
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Object {
    pub sha256: String,
    pub bytes: usize,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Array {
    pub dtype: String,
    pub count: usize,
    pub chunks: Vec<Object>,
}
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Manifest {
    pub schema_version: u32,
    pub model_id: String,
    pub rows: usize,
    pub columns: usize,
    pub nonzeros: usize,
    pub sense: ObjectiveSense,
    pub offset: f64,
    pub arrays: BTreeMap<String, Array>,
}
pub struct Store {
    root: PathBuf,
    read_workers: usize,
}
pub trait Scalar: Copy + Default + Send + Sync {
    const WIDTH: usize;
    const DTYPE: &'static str;
    fn decode(bytes: &[u8]) -> Self;
    fn append(self, bytes: &mut Vec<u8>);
}
macro_rules! scalar {
    ($ty:ty, $size:expr, $dtype:expr) => {
        impl Scalar for $ty {
            const WIDTH: usize = $size;
            const DTYPE: &'static str = $dtype;
            fn decode(b: &[u8]) -> Self {
                Self::from_le_bytes(b.try_into().expect("scalar width"))
            }
            fn append(self, b: &mut Vec<u8>) {
                b.extend_from_slice(&self.to_le_bytes());
            }
        }
    };
}
scalar!(u32, 4, "u32le");
scalar!(u64, 8, "u64le");
scalar!(f64, 8, "f64le");
impl Store {
    pub fn new(root: &Path) -> Result<Self> {
        fs::create_dir_all(root.join("objects"))?;
        Ok(Self {
            root: root.canonicalize()?,
            read_workers: 1,
        })
    }
    /// Bounded verified decoding only; no digest or metadata cache.
    pub fn with_read_workers(mut self, workers: usize) -> Self {
        assert!((1..=4).contains(&workers));
        self.read_workers = workers;
        self
    }
    fn path(&self, o: &Object) -> Result<PathBuf> {
        if o.sha256.len() != 64
            || !o
                .sha256
                .bytes()
                .all(|b| b.is_ascii_hexdigit() && !b.is_ascii_uppercase())
            || o.bytes == 0
            || o.bytes > CHUNK
        {
            return Err("object domain".into());
        }
        let p = self.root.join("objects").join(format!("{}.bin", o.sha256));
        if p.exists() && !p.canonicalize()?.starts_with(&self.root) {
            return Err("object root escape".into());
        }
        Ok(p)
    }
    pub fn bytes(&self, o: &Object) -> Result<Vec<u8>> {
        let p = self.path(o)?;
        if p.metadata()?.len() != o.bytes as u64 {
            return Err("object length".into());
        }
        let b = fs::read(p)?;
        if format!("{:x}", Sha256::digest(&b)) != o.sha256 {
            return Err("object digest".into());
        }
        Ok(b)
    }
    pub fn put(&self, bytes: &[u8]) -> Result<Object> {
        let o = Object {
            sha256: format!("{:x}", Sha256::digest(bytes)),
            bytes: bytes.len(),
        };
        let p = self.path(&o)?;
        if p.exists() {
            self.bytes(&o)?;
        } else {
            let mut f = OpenOptions::new().create_new(true).write(true).open(p)?;
            f.write_all(bytes)?;
            f.sync_all()?;
        }
        Ok(o)
    }
    pub fn write<T: Scalar>(&self, values: &[T]) -> Result<Array> {
        let mut chunks = Vec::new();
        let mut bytes = Vec::with_capacity(CHUNK.min(values.len().saturating_mul(T::WIDTH)));
        for part in values.chunks(CHUNK / T::WIDTH) {
            bytes.clear();
            for &v in part {
                v.append(&mut bytes);
            }
            chunks.push(self.put(&bytes)?);
        }
        Ok(Array {
            dtype: T::DTYPE.into(),
            count: values.len(),
            chunks,
        })
    }
    pub fn read<T: Scalar>(&self, a: &Array, count: usize) -> Result<Vec<T>> {
        if a.dtype != T::DTYPE
            || a.count != count
            || count > 1_000_000_001
            || a.chunks
                .iter()
                .try_fold(0usize, |n, c| n.checked_add(c.bytes))
                != count.checked_mul(T::WIDTH)
            || a.chunks.iter().any(|c| c.bytes % T::WIDTH != 0)
        {
            return Err("array shape/type".into());
        }
        if self.read_workers > 1 && a.chunks.len() > 1 && count * T::WIDTH >= 2 << 20 {
            let mut result = Vec::new();
            result.try_reserve_exact(count)?;
            result.resize(count, T::default());
            let width = self.read_workers.min(a.chunks.len());
            let mut remaining = result.as_mut_slice();
            let mut jobs = Vec::with_capacity(width);
            for worker in 0..width {
                let chunks = &a.chunks
                    [a.chunks.len() * worker / width..a.chunks.len() * (worker + 1) / width];
                let elements = chunks.iter().map(|c| c.bytes / T::WIDTH).sum();
                let (output, tail) = remaining.split_at_mut(elements);
                remaining = tail;
                jobs.push((chunks, output));
            }
            let results = std::thread::scope(|scope| {
                jobs.into_iter()
                    .map(|(chunks, mut output)| {
                        scope.spawn(move || -> std::result::Result<(), String> {
                            for chunk in chunks {
                                // One raw chunk per worker, decoded directly into its final slice.
                                let bytes = self.bytes(chunk).map_err(|e| e.to_string())?;
                                let (part, tail) = output.split_at_mut(chunk.bytes / T::WIDTH);
                                output = tail;
                                for (slot, value) in
                                    part.iter_mut().zip(bytes.chunks_exact(T::WIDTH))
                                {
                                    *slot = T::decode(value);
                                }
                            }
                            Ok(())
                        })
                    })
                    .collect::<Vec<_>>()
                    .into_iter()
                    .map(|job| job.join().expect("verified chunk reader"))
                    .collect::<Vec<_>>()
            });
            // Join every reader, then preserve the first chunk-order refusal.
            for result in results {
                result?;
            }
            return Ok(result);
        }
        let mut result = Vec::new();
        result.try_reserve_exact(count)?;
        for c in &a.chunks {
            result.extend(self.bytes(c)?.chunks_exact(T::WIDTH).map(T::decode));
        }
        Ok(result)
    }
    pub fn endpoint(&self, x: &[f64], y: &[f64]) -> Result<serde_json::Value> {
        Ok(serde_json::json!({"primal":self.write(x)?, "dual":self.write(y)?}))
    }
}
pub struct Original {
    pub program: LinearProgram,
    pub row_ids: Vec<u32>,
    pub model_id: String,
    pub objective_indices: Vec<u32>,
    pub objective_values: Vec<f64>,
    pub offset: f64,
    pub sha256: String,
}
#[derive(Default, Debug, Serialize)]
pub struct InputProfile {
    pub manifest_ns: u128,
    pub metadata_arrays_ns: u128,
    pub csr_arrays_ns: u128,
    pub objective_arrays_ns: u128,
    pub construction_ns: u128,
    pub total_ns: u128,
}
impl Original {
    pub fn load(path: &Path, store: &Store) -> Result<Self> {
        Self::load_profiled(path, store, false).map(|(original, _)| original)
    }
    pub fn load_profiled(
        path: &Path,
        store: &Store,
        parallel_transpose: bool,
    ) -> Result<(Self, InputProfile)> {
        let started = Instant::now();
        let mut profile = InputProfile::default();
        if path.metadata()?.len() > 16 << 20 {
            return Err("manifest size".into());
        }
        let bytes = fs::read(path)?;
        let a: Manifest = serde_json::from_slice(&bytes)?;
        let (m, n, z) = (a.rows, a.columns, a.nonzeros);
        if a.schema_version != 1
            || m > 250_000_000
            || n > 250_000_000
            || z > 1_000_000_000
            || !a.offset.is_finite()
            || a.arrays.len() != 11
        {
            return Err("original manifest domain".into());
        }
        let sha256 = format!("{:x}", Sha256::digest(&bytes));
        profile.manifest_ns = started.elapsed().as_nanos();
        let stage = Instant::now();
        let field = |name: &str| a.arrays.get(name).ok_or_else(|| format!("missing {name}"));
        let variable_ids = store.read(field("column_ids")?, n)?;
        let row_ids: Vec<u32> = store.read(field("row_ids")?, m)?;
        if row_ids.windows(2).any(|w| w[0] >= w[1]) {
            return Err("row identities".into());
        }
        let ranges = |lo: &str, hi: &str, count| -> Result<Vec<Range>> {
            let lower: Vec<f64> = store.read(field(lo)?, count)?;
            let upper: Vec<f64> = store.read(field(hi)?, count)?;
            Ok(lower
                .into_iter()
                .zip(upper)
                .map(|(lower, upper)| Range { lower, upper })
                .collect())
        };
        let columns = ranges("column_lower", "column_upper", n)?;
        let rows = ranges("row_lower", "row_upper", m)?;
        profile.metadata_arrays_ns = stage.elapsed().as_nanos();
        let stage = Instant::now();
        let offsets: Vec<u64> = store.read(field("offsets")?, m + 1)?;
        let offsets = offsets
            .into_iter()
            .map(usize::try_from)
            .collect::<std::result::Result<Vec<_>, _>>()?;
        let indices = store.read(field("indices")?, z)?;
        let values = store.read(field("values")?, z)?;
        profile.csr_arrays_ns = stage.elapsed().as_nanos();
        let stage = Instant::now();
        let objective_n = field("objective_indices")?.count;
        if objective_n > n {
            return Err("objective size".into());
        }
        let objective_indices = store.read(field("objective_indices")?, objective_n)?;
        let objective_values = store.read(field("objective_values")?, objective_n)?;
        profile.objective_arrays_ns = stage.elapsed().as_nanos();
        let stage = Instant::now();
        let constructor = if parallel_transpose {
            LinearProgram::from_csr_parallel
        } else {
            LinearProgram::from_csr
        };
        let program = constructor(
            variable_ids,
            columns,
            rows,
            offsets,
            indices,
            values,
            &objective_indices,
            &objective_values,
            a.sense,
            a.offset,
        )?;
        profile.construction_ns = stage.elapsed().as_nanos();
        profile.total_ns = started.elapsed().as_nanos();
        Ok((
            Self {
                program,
                row_ids,
                model_id: a.model_id,
                objective_indices,
                objective_values,
                offset: a.offset,
                sha256,
            },
            profile,
        ))
    }
    pub fn convert(model: &Model, store: &Store) -> Result<Manifest> {
        let p = LinearProgram::new(model)?;
        let d = model.document();
        let mut arrays = BTreeMap::new();
        arrays.insert("column_ids".into(), store.write(p.variable_ids())?);
        arrays.insert(
            "row_ids".into(),
            store.write(&d.constraints.iter().map(|r| r.id).collect::<Vec<_>>())?,
        );
        for (name, ranges) in [("column", p.columns()), ("row", p.rows())] {
            arrays.insert(
                format!("{name}_lower"),
                store.write(&ranges.iter().map(|r| r.lower).collect::<Vec<_>>())?,
            );
            arrays.insert(
                format!("{name}_upper"),
                store.write(&ranges.iter().map(|r| r.upper).collect::<Vec<_>>())?,
            );
        }
        arrays.insert(
            "offsets".into(),
            store.write(
                &(0..=p.row_count())
                    .map(|i| p.row_major().offset(i) as u64)
                    .collect::<Vec<_>>(),
            )?,
        );
        arrays.insert(
            "indices".into(),
            store.write(
                &p.row_major()
                    .entries()
                    .map(|(_, j, _)| j)
                    .collect::<Vec<_>>(),
            )?,
        );
        arrays.insert(
            "values".into(),
            store.write(
                &p.row_major()
                    .entries()
                    .map(|(_, _, v)| v)
                    .collect::<Vec<_>>(),
            )?,
        );
        arrays.insert(
            "objective_indices".into(),
            store.write(
                &d.objective
                    .terms
                    .iter()
                    .map(|t| {
                        p.variable_ids()
                            .binary_search(&t.variable_id)
                            .expect("original ID") as u32
                    })
                    .collect::<Vec<_>>(),
            )?,
        );
        arrays.insert(
            "objective_values".into(),
            store.write(
                &d.objective
                    .terms
                    .iter()
                    .map(|t| t.coefficient)
                    .collect::<Vec<_>>(),
            )?,
        );
        Ok(Manifest {
            schema_version: 1,
            model_id: d.model_id.clone(),
            rows: p.row_count(),
            columns: p.column_count(),
            nonzeros: p.nonzeros(),
            sense: d.objective.sense,
            offset: d.objective.offset,
            arrays,
        })
    }
}
