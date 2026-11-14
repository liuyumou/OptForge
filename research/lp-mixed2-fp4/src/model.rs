use crate::Result;
use crate::identity::hex;
use optimizer_core::Model;
use optimizer_lp::LinearProgram;
use serde::Serialize;

pub const MAX: usize = 2048;
pub fn pair(x: f64) -> [f32; 2] {
    let h = x as f32;
    [h, (x - f64::from(h)) as f32]
}
pub fn decode(c: u32) -> f64 {
    let value = [0., 0.5, 1., 1.5, 2., 3., 4., 6.][(c & 7) as usize];
    if c & 8 == 0 { value } else { -value }
}
pub fn encode(values: &[f64], k: usize) -> Result<(Vec<u32>, Vec<i32>, Vec<f64>)> {
    if !values.len().is_multiple_of(32)
        || ![2, 4].contains(&k)
        || values.iter().any(|v| !v.is_finite())
    {
        return Err("encoding domain".into());
    }
    let mut residual = values.to_vec();
    let mut words = vec![0; k * values.len() / 8];
    let mut exponents = Vec::new();
    for plane in 0..k {
        let maximum = residual.iter().map(|x| x.abs()).fold(0., f64::max);
        if maximum > 6. * 2_f64.powi(48) {
            return Err("encoding scale overflow".into());
        }
        let mut e = if maximum == 0. {
            -48
        } else {
            (maximum.log2().floor() as i32 - 2).max(-48)
        };
        if maximum > 6. * 2_f64.powi(e) {
            e += 1;
        }
        exponents.push(e);
        let scale = 2_f64.powi(e);
        for (i, r) in residual.iter_mut().enumerate() {
            let x = r.abs() / scale;
            let mut code = 0_u32;
            for (next, mid) in [(2, 0.5), (3, 1.25), (4, 1.75), (5, 2.5), (6, 3.5), (7, 5.)] {
                if x > mid || (x == mid && next != 2 && next % 2 == 0) {
                    code = next;
                }
            }
            if *r < 0. && code != 0 {
                code |= 8;
            }
            words[plane * values.len() / 8 + i / 8] |= code << ((i % 8) * 4);
            *r -= decode(code) * scale;
        }
    }
    Ok((words, exponents, residual))
}

pub struct Data {
    pub original: LinearProgram,
    pub hash: String,
    pub p: usize,
    pub a: Vec<f64>,
    pub cb: Vec<f64>,
    pub initial: Vec<f64>,
    pub row_scale: Vec<f64>,
    pub shift: u32,
    pub dense: bool,
    pub unbounded_direction: Option<usize>,
}
#[derive(Serialize)]
pub struct Packed {
    pub codes: Vec<u32>,
    pub exponents: Vec<i32>,
    pub native: Vec<f64>,
    /// Per direction: original row L1, coefficient error L1, component L1.
    pub norms: Vec<f64>,
}
fn up_add(a: f64, b: f64) -> f64 {
    (a + b).next_up()
}
#[derive(Serialize, Clone, Debug)]
pub struct Observation {
    pub rho: f64,
    pub row: f64,
    pub column: f64,
    pub primal_fixed: f64,
    pub dual_fixed: f64,
    pub scale: f64,
}
impl Data {
    pub fn new(bytes: &[u8], equilibrate: bool) -> Result<Self> {
        let model = Model::from_json(bytes)?;
        let original = LinearProgram::new(&model)?;
        let (n, m) = (original.column_count(), original.row_count());
        if n == 0 || m == 0 || n.max(m) > MAX {
            return Err("bounded model dimensions".into());
        }
        let p = n.max(m).div_ceil(32) * 32;
        let mut row_scale = vec![1.; m];
        for (i, scale) in row_scale.iter_mut().enumerate() {
            let maximum = original
                .row_major()
                .line(i)
                .1
                .iter()
                .map(|v| v.abs())
                .fold(0., f64::max);
            if equilibrate && maximum > 0. {
                let exponent = -(maximum.log2().round() as i32);
                if !(-32..=32).contains(&exponent) {
                    return Err("row scaling domain".into());
                }
                *scale = 2_f64.powi(exponent);
            }
        }
        let mut a = vec![0.; p * p];
        for (i, j, v) in original.row_major().entries() {
            let scaled = v * row_scale[i];
            if !scaled.is_finite() || (v != 0. && scaled == 0.) {
                return Err("row scaling coefficient overflow/underflow".into());
            }
            a[i * p + j as usize] = scaled;
        }
        let mut cb = vec![0.; 5 * p + 5];
        cb[..n].copy_from_slice(original.objective());
        for (i, b) in original.columns().iter().enumerate() {
            cb[p + i] = b.lower;
            cb[2 * p + i] = b.upper;
        }
        for (i, b) in original.rows().iter().enumerate() {
            for (slot, bound) in [(3 * p + i, b.lower), (4 * p + i, b.upper)] {
                let scaled = bound * row_scale[i];
                if bound.is_finite() && (!scaled.is_finite() || (bound != 0. && scaled == 0.)) {
                    return Err("row scaling bound overflow/underflow".into());
                }
                cb[slot] = scaled;
            }
        }
        if cb[..5 * p]
            .iter()
            .filter(|x| x.is_finite())
            .any(|x| !(*x as f32).is_finite())
        {
            return Err("FP32-pair coefficient domain".into());
        }
        let nr = (0..p)
            .map(|i| a[i * p..(i + 1) * p].iter().map(|v| v.abs()).sum::<f64>())
            .fold(0., f64::max);
        let nc = (0..p)
            .map(|j| (0..p).map(|i| a[i * p + j].abs()).sum::<f64>())
            .fold(0., f64::max);
        let shift = (((nr * nc / 0.75).sqrt()).log2().ceil() as u32).max(1);
        if shift > 24 || a.iter().any(|v| !v.is_finite()) || cb.iter().any(|v| v.is_nan()) {
            return Err("scaled operator domain".into());
        }
        cb[5 * p] = nr;
        cb[5 * p + 1] = nc;
        cb[5 * p + 2] = cb[..5 * p]
            .iter()
            .filter(|v| v.is_finite())
            .map(|&v| {
                let q = pair(v);
                (v - f64::from(q[0]) - f64::from(q[1])).abs()
            })
            .fold(0., f64::max);
        cb[5 * p + 4] = original.nonzeros() as f64;
        let dense = original.nonzeros() as f64 / (n * m) as f64 > 0.2;
        let mut initial = vec![0.; 5 * p];
        for i in 0..n {
            initial[i] = ((i % 3) as f64 - 1.)
                .mul_add(0.125, 0.)
                .clamp(cb[p + i], cb[2 * p + i]);
            initial[2 * p + i] = initial[i];
            initial[3 * p + i] = initial[i];
        }
        for i in 0..m {
            initial[p + i] = ((i % 7) as f64 - 3.) / 64. / row_scale[i];
            initial[4 * p + i] = initial[p + i];
        }
        let unbounded_direction = (0..n).find(|&j| {
            original.column_major().line(j).1.is_empty()
                && ((original.objective()[j] > 0.
                    && original.columns()[j].lower == f64::NEG_INFINITY)
                    || (original.objective()[j] < 0.
                        && original.columns()[j].upper == f64::INFINITY))
        });
        Ok(Self {
            original,
            hash: hex(bytes),
            p,
            a,
            cb,
            initial,
            row_scale,
            shift,
            dense,
            unbounded_direction,
        })
    }
    pub fn pack(&self, k: usize) -> Result<Packed> {
        if ![0, 2, 4].contains(&k) {
            return Err("component count".into());
        }
        let p = self.p;
        let blocks = p / 32;
        let mut codes = Vec::new();
        let mut exponents = Vec::new();
        let mut norms = vec![0.; 6 * p];
        if k != 0 {
            for r in 0..blocks {
                for c in 0..blocks {
                    let tile: Vec<_> = (0..1024)
                        .map(|i| self.a[(32 * r + i / 32) * p + 32 * c + i % 32])
                        .collect();
                    let (words, scales, _) = encode(&tile, k)?;
                    for (i, &a) in tile.iter().enumerate() {
                        let (mut lo, mut hi, mut magnitude) = (0., 0., 0.);
                        for h in 0..k {
                            let v = decode((words[h * 128 + i / 8] >> (4 * (i % 8))) & 15)
                                * 2_f64.powi(scales[h]);
                            lo = (lo + v).next_down();
                            hi = (hi + v).next_up();
                            magnitude = up_add(magnitude, v.abs());
                        }
                        let error = (a - lo).abs().max((hi - a).abs()).next_up();
                        for (direction, row) in [(0, 32 * r + i / 32), (1, 32 * c + i % 32)] {
                            let z = direction * 3 * p + row;
                            norms[z] = up_add(norms[z], a.abs());
                            norms[z + p] = up_add(norms[z + p], error);
                            norms[z + 2 * p] = up_add(norms[z + 2 * p], magnitude);
                        }
                    }
                    codes.extend(words);
                    exponents.extend(scales);
                }
            }
        } else {
            codes.push(0);
            exponents.push(0);
        }
        if norms.iter().any(|x| !x.is_finite()) {
            return Err("nonfinite guard norm".into());
        }
        let mut native = Vec::with_capacity(2 * p * p);
        for transpose in [false, true] {
            for j in 0..p {
                for i in 0..p {
                    native.push(self.a[if transpose { j * p + i } else { i * p + j }]);
                }
            }
        }
        Ok(Packed {
            codes,
            exponents,
            native,
            norms,
        })
    }
    pub fn endpoint(&self, raw: &[f64], transport: &str) -> crate::checker::Endpoint {
        crate::checker::Endpoint {
            model_sha256: self.hash.clone(),
            primal: raw[..self.original.column_count()].to_vec(),
            dual: (0..self.original.row_count())
                .map(|i| raw[self.p + i] * self.row_scale[i])
                .collect(),
            transport: transport.into(),
        }
    }
    fn audit_products(&self, x: &[f64], y: &[f64]) -> (Vec<f64>, Vec<f64>) {
        if self.original.nonzeros() < 262144 {
            return self.audit_products_serial(x, y);
        }
        std::thread::scope(|scope| {
            let workers: Vec<_> = (0..4)
                .map(|worker| {
                    scope.spawn(move || {
                        let mut ax = Vec::new();
                        let mut reduced = Vec::new();
                        for i in self.original.row_count() * worker / 4
                            ..self.original.row_count() * (worker + 1) / 4
                        {
                            let (indices, values) = self.original.row_major().line(i);
                            let mut sum = 0.;
                            for (&j, &a) in indices.iter().zip(values) {
                                sum += a * x[j as usize];
                            }
                            ax.push(sum);
                        }
                        for j in self.original.column_count() * worker / 4
                            ..self.original.column_count() * (worker + 1) / 4
                        {
                            let (indices, values) = self.original.column_major().line(j);
                            let mut sum = self.original.objective()[j];
                            for (&i, &a) in indices.iter().zip(values) {
                                sum -= a * y[i as usize];
                            }
                            reduced.push(sum);
                        }
                        (ax, reduced)
                    })
                })
                .collect();
            let mut ax = Vec::with_capacity(y.len());
            let mut reduced = Vec::with_capacity(x.len());
            for worker in workers {
                let (a, r) = worker.join().expect("original audit worker panicked");
                ax.extend(a);
                reduced.extend(r);
            }
            (ax, reduced)
        })
    }
    fn audit_products_serial(&self, x: &[f64], y: &[f64]) -> (Vec<f64>, Vec<f64>) {
        let mut ax = vec![0.; y.len()];
        let mut reduced = self.original.objective().to_vec();
        for (i, j, a) in self.original.row_major().entries() {
            ax[i] += a * x[j as usize];
            reduced[j as usize] -= a * y[i];
        }
        (ax, reduced)
    }
    pub fn observe(&self, raw: &[f64]) -> Result<Observation> {
        if raw.len() != 5 * self.p || raw.iter().any(|v| !v.is_finite()) {
            return Err("nonfinite audit".into());
        }
        let e = self.endpoint(raw, "completed");
        let (x, y) = (&e.primal, &e.dual);
        let (ax, reduced) = self.audit_products(x, y);
        let sx = x
            .iter()
            .chain(&reduced)
            .map(|v| v.abs())
            .chain(
                self.original
                    .columns()
                    .iter()
                    .flat_map(|b| [b.lower, b.upper])
                    .filter(|v| v.is_finite())
                    .map(f64::abs),
            )
            .fold(1., f64::max);
        let sy = y
            .iter()
            .chain(&ax)
            .map(|v| v.abs())
            .chain(
                self.original
                    .rows()
                    .iter()
                    .flat_map(|b| [b.lower, b.upper])
                    .filter(|v| v.is_finite())
                    .map(f64::abs),
            )
            .fold(1., f64::max);
        let column = self
            .original
            .columns()
            .iter()
            .enumerate()
            .map(|(i, b)| (x[i] - x[i].clamp(b.lower, b.upper)).abs() / sx)
            .fold(0., f64::max);
        let primal_fixed = self
            .original
            .columns()
            .iter()
            .enumerate()
            .map(|(i, b)| (x[i] - (x[i] - reduced[i]).clamp(b.lower, b.upper)).abs() / sx)
            .fold(0., f64::max);
        let row = self
            .original
            .rows()
            .iter()
            .enumerate()
            .map(|(i, b)| (ax[i] - ax[i].clamp(b.lower, b.upper)).abs() / sy)
            .fold(0., f64::max);
        let dual_fixed = self
            .original
            .rows()
            .iter()
            .enumerate()
            .map(|(i, b)| (ax[i] + (y[i] - ax[i]).clamp(-b.upper, -b.lower)).abs() / sy)
            .fold(0., f64::max);
        let scale = raw[..self.p]
            .iter()
            .map(|v| v.abs())
            .fold(1., f64::max)
            .min(
                raw[self.p..2 * self.p]
                    .iter()
                    .map(|v| v.abs())
                    .fold(1., f64::max),
            );
        Ok(Observation {
            rho: row.max(column).max(primal_fixed).max(dual_fixed),
            row,
            column,
            primal_fixed,
            dual_fixed,
            scale,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn original_audit_parallel_order_is_exact() {
        use serde_json::json;
        let n = 512;
        let finite = |x: f64| json!({"kind":"finite","value":x});
        let model = json!({"schema_version":1,"model_id":"audit-order",
            "variables":(0..n).map(|j|json!({"id":j,"domain":"continuous","lower":finite(-1.),"upper":finite(1.)})).collect::<Vec<_>>(),
            "constraints":(0..n).map(|i|json!({"id":i,"lower":finite(-1.),"upper":finite(1.),"terms":(0..n).map(|j|json!({"variable_id":j,"coefficient":((13*i+7*j)%37) as f64/37.-0.4})).collect::<Vec<_>>()})).collect::<Vec<_>>(),
            "objective":{"sense":"minimize","offset":0.,"terms":[]}});
        let data = Data::new(&serde_json::to_vec(&model).unwrap(), false).unwrap();
        for scale in [0., -0., 1., 1e-280, 1e280] {
            let x: Vec<_> = (0..n)
                .map(|i| scale * ((13 * i % 37) as f64 / 37. - 0.5))
                .collect();
            let y: Vec<_> = (0..n)
                .map(|i| scale * ((7 * i % 29) as f64 / 29. - 0.5))
                .collect();
            let (a, b) = data.audit_products(&x, &y);
            let (c, d) = data.audit_products_serial(&x, &y);
            assert!(crate::same_bits(&a, &c) && crate::same_bits(&b, &d));
        }
    }
    #[test]
    fn tie_even_and_negative_zero() {
        let mut v = vec![0.; 32];
        v[0] = 6.;
        v[1] = 0.25;
        v[2] = 0.75;
        v[3] = -0.25;
        let (w, e, r) = encode(&v, 2).unwrap();
        assert_eq!(e[0], 0);
        assert_eq!(w[0] & 0xffff, 0x0207);
        assert_eq!(r[0], 0.);
    }
    #[test]
    fn exact_residual_identity() {
        let v: Vec<_> = (0..1024)
            .map(|i| ((13 * i + 7) % 37) as f64 / 37. - 0.5)
            .collect();
        for k in [2, 4] {
            let (w, e, r) = encode(&v, k).unwrap();
            for i in 0..1024 {
                let decoded = (0..k)
                    .map(|j| decode((w[j * 128 + i / 8] >> ((i % 8) * 4)) & 15) * 2_f64.powi(e[j]))
                    .sum::<f64>();
                assert_eq!(v[i], decoded + r[i]);
            }
        }
    }
    #[test]
    fn encoding_rejects_nonfinite_and_overflow() {
        assert!(encode(&[f64::NAN; 32], 4).is_err());
        assert!(encode(&[1e100; 32], 4).is_err());
        assert!(encode(&[1.; 32], 8).is_err());
    }
}
