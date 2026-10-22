//! ADR-0041 operator-only diagnostics. These records can never certify an LP.
#![allow(missing_docs)]
use crate::{lp_quant_resident::Request, serde_strict::deserialize_required_object, sha256};
use optimizer_core::{ErrorKind, Model, ValidationError};
use optimizer_lp::{
    Engine, LinearProgram,
    quant_resident::{Counts, Layout, Operator, Promotion},
};
use serde::{Deserialize, Serialize};
use std::{collections::BTreeMap, time::Instant};
fn invalid(e: impl ToString) -> ValidationError {
    ValidationError::new(ErrorKind::Document, e.to_string())
}
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Mode {
    Fused,
    Product,
    Guard,
}
impl Mode {
    fn code(self) -> u32 {
        match self {
            Self::Fused => 0,
            Self::Guard => 1,
            Self::Product => 2,
        }
    }
}
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct MicroRequest {
    pub request: Request,
    pub vectors_sha256: String,
    pub mode: Mode,
    pub products: u32,
}
deserialize_required_object!(MicroRequest {
    request: Request,
    vectors_sha256: String,
    mode: Mode,
    products: u32
});
impl MicroRequest {
    pub fn from_json(b: &[u8]) -> Result<Self, ValidationError> {
        crate::lp::unique_json(b)?;
        let r: Self = serde_json::from_slice(b).map_err(invalid)?;
        r.validate()?;
        Ok(r)
    }
    fn validate(&self) -> Result<(), ValidationError> {
        self.request.validate()?;
        if self.products != 16
            || self.request.layout != Layout::Segmented
            || !self.request.diagnostic
            || self.vectors_sha256.len() != 64
        {
            return Err(invalid("resident micro identity"));
        }
        Ok(())
    }
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct NamedVector {
    pub name: String,
    pub transpose: bool,
    pub values: Vec<f64>,
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Vectors {
    pub schema_version: u32,
    pub model_sha256: String,
    pub vectors: Vec<NamedVector>,
}
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct Row {
    pub name: String,
    pub transpose: bool,
    pub products: u32,
    pub elapsed_ns: u64,
    pub output_sha256: Option<String>,
    pub bounds_sha256: Option<String>,
    pub flags_sha256: Option<String>,
    pub counts: Counts,
}
deserialize_required_object!(Row{name:String,transpose:bool,products:u32,elapsed_ns:u64,output_sha256:Option<String>,bounds_sha256:Option<String>,flags_sha256:Option<String>,counts:Counts});
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct Evidence {
    pub schema_version: u32,
    pub identity: String,
    pub request: MicroRequest,
    pub executed_device: String,
    pub rows: Vec<Row>,
    pub elapsed_ns: u64,
    pub counters: BTreeMap<String, u64>,
    pub payload_sha256: String,
}
deserialize_required_object!(Evidence{schema_version:u32,identity:String,request:MicroRequest,executed_device:String,rows:Vec<Row>,elapsed_ns:u64,counters:BTreeMap<String,u64>,payload_sha256:String});
fn floats(v: &[f64]) -> String {
    sha256::hex(
        &v.iter()
            .flat_map(|v| v.to_bits().to_le_bytes())
            .collect::<Vec<_>>(),
    )
}
fn flags(v: &[u32]) -> String {
    sha256::hex(&v.iter().flat_map(|v| v.to_le_bytes()).collect::<Vec<_>>())
}
fn payload(e: &Evidence) -> Result<String, ValidationError> {
    Ok(sha256::hex(
        &serde_json::to_vec(&(
            e.schema_version,
            &e.identity,
            &e.request,
            &e.executed_device,
            &e.rows,
            e.elapsed_ns,
            &e.counters,
        ))
        .map_err(invalid)?,
    ))
}
fn prepare(b: &[u8], v: &[u8], r: &MicroRequest) -> Result<(Model, Vectors), ValidationError> {
    r.validate()?;
    crate::lp::unique_json(v)?;
    let vectors: Vectors = serde_json::from_slice(v).map_err(invalid)?;
    if sha256::hex(b) != r.request.model_sha256
        || sha256::hex(v) != r.vectors_sha256
        || vectors.schema_version != 1
        || vectors.model_sha256 != r.request.model_sha256
        || vectors.vectors.len() != 4
    {
        return Err(invalid("resident micro inputs"));
    }
    let model = Model::from_json(b)?;
    for (row, expected) in vectors.vectors.iter().zip([
        "synthetic-primal",
        "synthetic-dual",
        "recorded-primal",
        "recorded-dual",
    ]) {
        if row.name != expected
            || row.transpose != expected.ends_with("dual")
            || row.values.len()
                != if row.transpose {
                    model.document().constraints.len()
                } else {
                    model.document().variables.len()
                }
            || row.values.iter().any(|v| !v.is_finite())
        {
            return Err(invalid("resident micro vector shape"));
        }
    }
    Ok((model, vectors))
}
impl Evidence {
    pub fn from_json(b: &[u8]) -> Result<Self, ValidationError> {
        crate::lp::unique_json(b)?;
        serde_json::from_slice(b).map_err(invalid)
    }
    pub fn verify(&self, b: &[u8], v: &[u8], r: &MicroRequest) -> Result<(), ValidationError> {
        let (model, vectors) = prepare(b, v, r)?;
        if self.schema_version != 1
            || self.identity != "lp-quant-resident-micro-v1"
            || &self.request != r
            || self.executed_device != r.request.device
            || self.payload_sha256 != payload(self)?
            || self.rows.len() != 4
        {
            return Err(invalid("resident micro evidence identity"));
        }
        let p = LinearProgram::new(&model)?;
        let e = Engine::new(&p, r.request.method);
        let op =
            Operator::new(&e, r.request.settings.clone(), Layout::Segmented).map_err(invalid)?;
        let g = op.generation(Promotion::new(&op)).map_err(invalid)?;
        let size = op.rows.max(op.columns).max(1) as u64;
        let lines = (op.rows + op.columns).max(1) as u64;
        let mask = op.tiles.len().max(1) as u64;
        let peak = optimizer_lp_cuda::quant_resident::buffer_bytes(&op).map_err(invalid)?;
        let expected_launches =
            4 * (2 + if r.mode == Mode::Product { 2 } else { 3 } * u64::from(r.products));
        let expected_upload = peak
            + mask * 4
            + 3 * lines * 8
            + 4 * size * 8
            + if r.mode == Mode::Product { 4 * 24 } else { 0 };
        let expected_readback = 4 * (88 + 12 * lines + 8 * size);
        if self.counters
            != BTreeMap::from([
                ("launches".into(), expected_launches),
                ("upload_bytes".into(), expected_upload),
                ("readback_bytes".into(), expected_readback),
                ("device_peak_bytes".into(), peak),
            ])
        {
            return Err(invalid("resident micro resource counters"));
        }
        for (row, v) in self.rows.iter().zip(&vectors.vectors) {
            let actual = op.product(&g, v.transpose, &v.values).map_err(invalid)?;
            let mut counts = Counts::default();
            let mut part = actual.counts.clone();
            if r.mode == Mode::Guard {
                part.guard_products = part.low + part.high;
            }
            if r.mode == Mode::Product {
                part.coarse_pass = 0;
                part.detailed_pass = 0;
                part.detailed_fail = 0;
            }
            for _ in 0..r.products {
                counts.add(&part);
            }
            if row.name != v.name
                || row.transpose != v.transpose
                || row.products != r.products
                || row.counts != counts
                || row.elapsed_ns > self.elapsed_ns
                || row.output_sha256
                    != if r.mode == Mode::Guard {
                        None
                    } else {
                        Some(floats(&actual.output))
                    }
                || row.bounds_sha256
                    != if r.mode == Mode::Product {
                        None
                    } else {
                        Some(floats(&actual.bounds))
                    }
                || row.flags_sha256
                    != if r.mode == Mode::Product {
                        None
                    } else {
                        Some(flags(&actual.flags))
                    }
            {
                return Err(invalid("resident micro independent product/bound witness"));
            }
        }
        Ok(())
    }
}
pub fn execute(b: &[u8], v: &[u8], r: MicroRequest) -> Result<Evidence, ValidationError> {
    let start = Instant::now();
    let (model, vectors) = prepare(b, v, &r)?;
    if std::env::var("AI_OPTIMIZER_GPU_LEASE").ok().as_deref() != Some("inherited")
        || std::env::var("CUDA_VISIBLE_DEVICES").ok().as_deref() != Some(r.request.device.as_str())
        || sha256::hex(&std::fs::read(std::env::current_exe().map_err(invalid)?).map_err(invalid)?)
            != r.request.executable_sha256
    {
        return Err(invalid("resident micro selected lease/executable"));
    }
    let image =
        std::fs::read(optimizer_lp_cuda::quant_resident::code_object_path()).map_err(invalid)?;
    if sha256::hex(&image) != r.request.code_object_sha256 {
        return Err(invalid("resident micro image identity"));
    }
    let p = LinearProgram::new(&model)?;
    let e = Engine::new(&p, r.request.method);
    let op = Operator::new(&e, r.request.settings.clone(), Layout::Segmented).map_err(invalid)?;
    let g = op.generation(Promotion::new(&op)).map_err(invalid)?;
    let context =
        std::rc::Rc::new(optimizer_cuda_sys::Context::create(&r.request.device).map_err(invalid)?);
    if context.device().uuid != r.request.device {
        return Err(invalid("resident micro executed device"));
    }
    let module = context.load_module(&image).map_err(invalid)?;
    let mut oracle = optimizer_lp_cuda::quant_resident::Oracle::new(
        context,
        &op,
        &module,
        r.request.device_buffer_bytes,
        &e,
    )
    .map_err(invalid)?;
    let mut rows = vec![];
    for v in vectors.vectors {
        let (actual, elapsed_ns) = oracle
            .diagnostic_batch(&g, v.transpose, &v.values, r.products, r.mode.code())
            .map_err(invalid)?;
        rows.push(Row {
            name: v.name,
            transpose: v.transpose,
            products: r.products,
            elapsed_ns,
            output_sha256: if r.mode == Mode::Guard {
                None
            } else {
                Some(floats(&actual.output))
            },
            bounds_sha256: if r.mode == Mode::Product {
                None
            } else {
                Some(floats(&actual.bounds))
            },
            flags_sha256: if r.mode == Mode::Product {
                None
            } else {
                Some(flags(&actual.flags))
            },
            counts: actual.counts,
        });
    }
    let mut counters = BTreeMap::new();
    counters.insert("launches".into(), oracle.counters.launches);
    counters.insert("upload_bytes".into(), oracle.counters.upload_bytes);
    counters.insert("readback_bytes".into(), oracle.counters.readback_bytes);
    counters.insert("device_peak_bytes".into(), oracle.counters.peak_bytes);
    let mut result = Evidence {
        schema_version: 1,
        identity: "lp-quant-resident-micro-v1".into(),
        executed_device: r.request.device.clone(),
        request: r,
        rows,
        elapsed_ns: start.elapsed().as_nanos() as u64,
        counters,
        payload_sha256: String::new(),
    };
    result.payload_sha256 = payload(&result)?;
    Ok(result)
}
