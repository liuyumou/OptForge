//! Research Expansion64 scalar authority, separate from all FP64 solver paths.
#![allow(missing_docs)]
// These fallible, explicitly rounded primitives are not Rust infallible operators.
#![allow(clippy::should_implement_trait)]
use serde::{Deserialize, Serialize};

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Value {
    pub magnitude: u64,
    pub exponent: i32,
    pub negative: bool,
}
pub const ONE: Value = Value { magnitude: 1 << 63, exponent: -63, negative: false };
pub const ZERO: Value = Value { magnitude: 0, exponent: 0, negative: false };

#[derive(Clone, Copy, Default)]
struct Wide([u64; 5]);
impl Wide {
    fn aligned(mut n: u128, offset: i32) -> Self {
        let mut shift = offset;
        if shift < 0 {
            let distance = -shift;
            n = if distance >= 128 { u128::from(n != 0) } else {
                (n >> distance) | u128::from(n & ((1u128 << distance) - 1) != 0)
            };
            shift = 0;
        }
        let mut out = Self::default();
        let word = shift as usize / 64;
        let bits = shift as u32 % 64;
        for (i, v) in [n as u64, (n >> 64) as u64].into_iter().enumerate() {
            if word + i < 5 { out.0[word+i] |= v << bits; }
            if bits != 0 && word + i + 1 < 5 { out.0[word+i+1] |= v >> (64-bits); }
        }
        out
    }
    fn greater_equal(self, b: Self) -> bool {
        self.0.iter().rev().cmp(b.0.iter().rev()).is_ge()
    }
    fn add(&mut self, b: Self) {
        let mut carry = 0u128;
        for (a,b) in self.0.iter_mut().zip(b.0) {
            let n = u128::from(*a) + u128::from(b) + carry;
            *a = n as u64; carry = n >> 64;
        }
    }
    fn sub(&mut self, b: Self) {
        let mut borrow = false;
        for (a,b) in self.0.iter_mut().zip(b.0) {
            let (v, first) = a.overflowing_sub(b);
            let (v, second) = v.overflowing_sub(u64::from(borrow));
            *a = v; borrow = first || second;
        }
    }
    fn bit(self, position: i32) -> bool {
        (0..320).contains(&position) && (self.0[position as usize/64] >> (position%64)) & 1 != 0
    }
    fn below(self, position: i32) -> bool {
        self.0.iter().enumerate().any(|(i,&v)| {
            let count = position - 64*i as i32;
            let mask = if count >= 64 { u64::MAX } else if count <= 0 { 0 } else { (1u64 << count)-1 };
            v & mask != 0
        })
    }
    fn extract(self, offset: i32) -> u64 {
        if offset < 0 { return self.0[0].checked_shl((-offset) as u32).unwrap_or(0); }
        let word = offset as usize/64;
        let bits = offset as u32%64;
        let lo = self.0.get(word).copied().unwrap_or(0);
        let hi = self.0.get(word+1).copied().unwrap_or(0);
        (lo >> bits) | if bits == 0 { 0 } else { hi << (64-bits) }
    }
    fn round(self, base: i32, negative: bool, precision: i32) -> Result<Value, &'static str> {
        let top = self.0.iter().enumerate().rev().find(|(_,v)| **v != 0)
            .map(|(i,v)| 64*i as i32+63-v.leading_zeros() as i32);
        let Some(top) = top else { return Ok(Value { negative, ..ZERO }); };
        let mut unit = (base+top-(precision-1)).max(-1022-(precision-1));
        let shift = unit-base;
        let mut m = self.extract(shift);
        let mut carry = false;
        if self.bit(shift-1) && (self.below(shift-1) || m & 1 != 0) {
            (m, carry) = m.overflowing_add(1);
        }
        if carry || precision < 64 && m == 1u64 << precision {
            m = 1u64 << (precision-1); unit += 1;
        }
        if unit > 1023-(precision-1) { return Err("expanded_overflow"); }
        Ok(Value { magnitude: m, exponent: if m == 0 { 0 } else { unit }, negative })
    }
}

impl Value {
    pub fn validate(self) -> Result<Self, &'static str> {
        if self.magnitude == 0 && self.exponent == 0 || self.magnitude != 0 &&
            (-1085..=960).contains(&self.exponent) &&
            (self.exponent == -1085 || self.magnitude >= 1 << 63) { Ok(self) }
        else { Err("expanded_noncanonical") }
    }
    pub fn from_f64(v: f64) -> Result<Self, &'static str> {
        if !v.is_finite() { return Err("expanded_nonfinite"); }
        let bits = v.to_bits();
        let field = ((bits >> 52) & 2047) as i32;
        let mut m = bits & ((1 << 52)-1);
        let mut e = -1074;
        if field != 0 { m |= 1 << 52; e = field-1075; }
        if m == 0 { return Ok(Self { negative: bits >> 63 != 0, ..ZERO }); }
        let shift = (m.leading_zeros() as i32).min(e+1085);
        Ok(Self { magnitude: m << shift, exponent: e-shift, negative: bits >> 63 != 0 })
    }
    fn fp64_rounded(self) -> Result<Value, &'static str> {
        Wide::aligned(u128::from(self.magnitude),0).round(self.exponent,self.negative,53)
    }
    fn binary64(v: Value) -> f64 {
        let bits = if v.magnitude < 1 << 52 { v.magnitude } else {
            ((v.exponent+1075) as u64) << 52 | v.magnitude & ((1 << 52)-1)
        };
        f64::from_bits(bits | (u64::from(v.negative) << 63))
    }
    pub fn to_f64(self) -> Result<f64, &'static str> {
        let rounded = self.fp64_rounded()?;
        if self.magnitude != 0 && rounded.magnitude == 0 { return Err("boundary_nonzero_to_zero"); }
        Ok(Self::binary64(rounded))
    }
    /// FP64 only for a conservative guard scalar, never an authoritative iterate.
    pub fn abs_upper(self) -> Result<f64, &'static str> {
        if self.magnitude == 0 { return Ok(0.); }
        let x = Self::binary64(Self { negative: false, ..self.fp64_rounded()? });
        let bound = x.next_up();
        if bound.is_finite() { Ok(bound) } else { Err("expanded_bound_overflow") }
    }
    pub fn negate(self) -> Self { Self { negative: !self.negative, ..self } }
    pub fn fma(self, b: Self, c: Self) -> Result<Self, &'static str> {
        let product = u128::from(self.magnitude)*u128::from(b.magnitude);
        let pe = if product != 0 { self.exponent+b.exponent } else { c.exponent };
        let ce = if c.magnitude != 0 { c.exponent } else { pe };
        let base = pe.max(ce)-160;
        let mut left = Wide::aligned(product,pe-base);
        let mut right = Wide::aligned(u128::from(c.magnitude),ce-base);
        let sign = self.negative ^ b.negative;
        if sign == c.negative { left.add(right); left.round(base,sign,64) }
        else if left.greater_equal(right) {
            left.sub(right);
            left.round(base,if left.0.iter().all(|v| *v == 0) { false } else { sign },64)
        } else { right.sub(left); right.round(base,c.negative,64) }
    }
    pub fn add(self, b: Self) -> Result<Self, &'static str> { self.fma(ONE,b) }
    pub fn sub(self, b: Self) -> Result<Self, &'static str> { self.add(b.negate()) }
    pub fn mul(self, b: Self) -> Result<Self, &'static str> {
        let v = self.fma(b,Self { negative: self.negative ^ b.negative, ..ZERO })?;
        if self.magnitude != 0 && b.magnitude != 0 && v.magnitude == 0 {
            Err("expanded_product_underflow")
        } else { Ok(v) }
    }
    pub fn less(self, b: Self) -> bool {
        if self.magnitude == 0 && b.magnitude == 0 { return false; }
        if self.magnitude == 0 { return !b.negative; }
        if b.magnitude == 0 { return self.negative; }
        if self.negative != b.negative { return self.negative; }
        let order = (self.exponent,self.magnitude).cmp(&(b.exponent,b.magnitude));
        if self.negative { order.is_gt() } else { order.is_lt() }
    }
    pub fn project(self, lower: Option<Self>, upper: Option<Self>) -> Result<Self, &'static str> {
        if lower.zip(upper).is_some_and(|(l,u)| u.less(l)) { return Err("expanded_bound_order"); }
        let v = lower.filter(|l| self.less(*l)).unwrap_or(self);
        Ok(upper.filter(|u| u.less(v)).unwrap_or(v))
    }
    pub fn from_i128(n: i128, exponent: i32) -> Result<Self, &'static str> {
        Wide::aligned(n.unsigned_abs(),0).round(exponent,n < 0,64)
    }
    pub fn block_exponent(self) -> i32 {
        if self.magnitude == 0 { -1085 } else { self.exponent+64-self.magnitude.leading_zeros() as i32 }
    }
    /// A 64-bit UNSIGNED magnitude plus separate sign, with an exact E64 tail.
    pub fn pack(self, block_exponent: i32) -> Result<(u64,Self), &'static str> {
        if self.magnitude == 0 { return Ok((0,self)); }
        let shift = self.exponent-block_exponent+64;
        if shift >= 0 {
            if 64-self.magnitude.leading_zeros() as i32+shift > 64 { return Err("expanded_pack_range"); }
            Ok((self.magnitude.checked_shl(shift as u32).unwrap_or(0),Self { negative:self.negative, ..ZERO }))
        } else {
            let distance = -shift;
            let q = self.magnitude.checked_shr(distance as u32).unwrap_or(0);
            let tail = if distance >= 64 { self.magnitude } else { self.magnitude & ((1 << distance)-1) };
            Ok((q,Wide::aligned(u128::from(tail),0).round(self.exponent,self.negative,64)?))
        }
    }
}
