//! Bounded original-model transport. Compact CSR changes no model arithmetic.
use crate::{
    Result,
    operator::{MAX_DIMENSION, MAX_NONZEROS},
};
use optimizer_core::{
    Bound, Constraint, Domain, LinearTerm, Model, ModelDocument, Objective, ObjectiveSense,
    Variable,
};
use sha2::{Digest, Sha256};
use std::{
    fs::File,
    io::{BufReader, Read},
    path::Path,
};

pub const MAGIC: &[u8; 8] = b"LPCSRA01";
struct Hashed<R> {
    inner: R,
    hash: Sha256,
}
impl<R: Read> Read for Hashed<R> {
    fn read(&mut self, out: &mut [u8]) -> std::io::Result<usize> {
        let n = self.inner.read(out)?;
        self.hash.update(&out[..n]);
        Ok(n)
    }
}
fn bytes<const N: usize>(r: &mut impl Read) -> Result<[u8; N]> {
    let mut b = [0; N];
    r.read_exact(&mut b)?;
    Ok(b)
}
fn u64le(r: &mut impl Read) -> Result<u64> {
    Ok(u64::from_le_bytes(bytes(r)?))
}
fn u32le(r: &mut impl Read) -> Result<u32> {
    Ok(u32::from_le_bytes(bytes(r)?))
}
fn f64le(r: &mut impl Read) -> Result<f64> {
    Ok(f64::from_le_bytes(bytes(r)?))
}
fn bound(x: f64, lower: bool) -> Result<Bound> {
    if x.is_finite() {
        Ok(Bound::Finite { value: x })
    } else if lower && x == f64::NEG_INFINITY {
        Ok(Bound::NegativeInfinity)
    } else if !lower && x == f64::INFINITY {
        Ok(Bound::PositiveInfinity)
    } else {
        Err("compact bound domain".into())
    }
}

/// Header: magic, n/m/nnz/sense (u64), offset (f64), ID byte length and
/// objective term count (u64). All numbers are little endian. Arrays follow:
/// column IDs, row IDs (u32); column lower/upper, row lower/upper (f64);
/// row offsets (u64); matrix column positions (u32), coefficients (f64);
/// objective column positions (u32), coefficients (f64).
pub fn load(path: &Path) -> Result<(Model, String)> {
    let mut file = File::open(path)?;
    let mut magic = [0; 8];
    let nread = file.read(&mut magic)?;
    if nread != 8 || &magic != MAGIC {
        let mut data = Vec::new();
        File::open(path)?
            .take((384 << 20) + 1)
            .read_to_end(&mut data)?;
        if data.len() > 384 << 20 {
            return Err("model byte limit".into());
        }
        return Ok((
            Model::from_json(&data)?,
            format!("{:x}", Sha256::digest(&data)),
        ));
    }
    let file = File::open(path)?;
    let length = file.metadata()?.len();
    let mut r = BufReader::with_capacity(
        1 << 20,
        Hashed {
            inner: file,
            hash: Sha256::new(),
        },
    );
    if &bytes::<8>(&mut r)? != MAGIC {
        return Err("compact magic changed".into());
    }
    let n = usize::try_from(u64le(&mut r)?)?;
    let m = usize::try_from(u64le(&mut r)?)?;
    let z = usize::try_from(u64le(&mut r)?)?;
    let sense = match u64le(&mut r)? {
        0 => ObjectiveSense::Minimize,
        1 => ObjectiveSense::Maximize,
        _ => return Err("compact objective sense".into()),
    };
    let offset = f64le(&mut r)?;
    let idlen = usize::try_from(u64le(&mut r)?)?;
    let q = usize::try_from(u64le(&mut r)?)?;
    if n > MAX_DIMENSION
        || m > MAX_DIMENSION
        || z > MAX_NONZEROS
        || q > n
        || !(1..=1024).contains(&idlen)
    {
        return Err("compact resource domain".into());
    }
    let expected =
        64u64 + idlen as u64 + 20 * (n + m) as u64 + 8 * (m + 1) as u64 + 12 * (z + q) as u64;
    if length != expected {
        return Err("compact byte length".into());
    }
    let mut id = vec![0; idlen];
    r.read_exact(&mut id)?;
    let model_id = String::from_utf8(id)?;
    let column_ids = (0..n).map(|_| u32le(&mut r)).collect::<Result<Vec<_>>>()?;
    let row_ids = (0..m).map(|_| u32le(&mut r)).collect::<Result<Vec<_>>>()?;
    if column_ids.windows(2).any(|w| w[0] >= w[1]) || row_ids.windows(2).any(|w| w[0] >= w[1]) {
        return Err("compact IDs not canonical".into());
    }
    let lower = (0..n)
        .map(|_| bound(f64le(&mut r)?, true))
        .collect::<Result<Vec<_>>>()?;
    let upper = (0..n)
        .map(|_| bound(f64le(&mut r)?, false))
        .collect::<Result<Vec<_>>>()?;
    let variables = column_ids
        .iter()
        .zip(lower)
        .zip(upper)
        .map(|((&id, lower), upper)| Variable {
            id,
            domain: Domain::Continuous,
            lower,
            upper,
        })
        .collect();
    let lower = (0..m)
        .map(|_| bound(f64le(&mut r)?, true))
        .collect::<Result<Vec<_>>>()?;
    let upper = (0..m)
        .map(|_| bound(f64le(&mut r)?, false))
        .collect::<Result<Vec<_>>>()?;
    let pointers = (0..=m).map(|_| u64le(&mut r)).collect::<Result<Vec<_>>>()?;
    if pointers[0] != 0 || pointers[m] != z as u64 || pointers.windows(2).any(|w| w[0] > w[1]) {
        return Err("compact CSR offsets".into());
    }
    let indices = (0..z).map(|_| u32le(&mut r)).collect::<Result<Vec<_>>>()?;
    let mut constraints = Vec::with_capacity(m);
    for (i, ((id, lower), upper)) in row_ids.into_iter().zip(lower).zip(upper).enumerate() {
        let positions = &indices[pointers[i] as usize..pointers[i + 1] as usize];
        if positions.windows(2).any(|w| w[0] >= w[1]) {
            return Err("compact row positions not canonical".into());
        }
        let terms = positions
            .iter()
            .map(|&j| {
                let variable_id = *column_ids
                    .get(j as usize)
                    .ok_or("compact column position")?;
                Ok(LinearTerm {
                    variable_id,
                    coefficient: f64le(&mut r)?,
                })
            })
            .collect::<Result<Vec<_>>>()?;
        constraints.push(Constraint {
            id,
            lower,
            upper,
            terms,
        });
    }
    drop(indices);
    let indices = (0..q).map(|_| u32le(&mut r)).collect::<Result<Vec<_>>>()?;
    if indices.windows(2).any(|w| w[0] >= w[1]) {
        return Err("compact objective positions not canonical".into());
    }
    let terms = indices
        .into_iter()
        .map(|j| {
            let variable_id = *column_ids
                .get(j as usize)
                .ok_or("compact objective position")?;
            Ok(LinearTerm {
                variable_id,
                coefficient: f64le(&mut r)?,
            })
        })
        .collect::<Result<Vec<_>>>()?;
    if r.read(&mut [0; 1])? != 0 {
        return Err("compact trailing bytes".into());
    }
    let hash = format!("{:x}", r.into_inner().hash.finalize());
    let model = Model::new(ModelDocument {
        schema_version: 1,
        model_id,
        variables,
        constraints,
        objective: Objective {
            sense,
            offset,
            terms,
        },
    })?;
    Ok((model, hash))
}
