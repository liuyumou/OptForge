// Retained unique-key reader body, copied without changing the historical crate.
use optimizer_core::{ErrorKind, ValidationError};
fn invalid(message: String) -> ValidationError {
    ValidationError::new(ErrorKind::Document, message)
}
pub(crate) fn unique_json(bytes: &[u8]) -> Result<(), ValidationError> {
    struct Unique;
    impl<'de> serde::Deserialize<'de> for Unique {
        fn deserialize<D: serde::Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
            struct Visitor;
            impl<'de> serde::de::Visitor<'de> for Visitor {
                type Value = Unique;
                fn expecting(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
                    f.write_str("finite JSON with unique keys")
                }
                fn visit_bool<E: serde::de::Error>(self, _: bool) -> Result<Unique, E> {
                    Ok(Unique)
                }
                fn visit_i64<E: serde::de::Error>(self, _: i64) -> Result<Unique, E> {
                    Ok(Unique)
                }
                fn visit_u64<E: serde::de::Error>(self, _: u64) -> Result<Unique, E> {
                    Ok(Unique)
                }
                fn visit_f64<E: serde::de::Error>(self, v: f64) -> Result<Unique, E> {
                    if v.is_finite() {
                        Ok(Unique)
                    } else {
                        Err(E::custom("nonfinite JSON"))
                    }
                }
                fn visit_str<E: serde::de::Error>(self, _: &str) -> Result<Unique, E> {
                    Ok(Unique)
                }
                fn visit_unit<E: serde::de::Error>(self) -> Result<Unique, E> {
                    Ok(Unique)
                }
                fn visit_seq<A: serde::de::SeqAccess<'de>>(
                    self,
                    mut seq: A,
                ) -> Result<Unique, A::Error> {
                    while seq.next_element::<Unique>()?.is_some() {}
                    Ok(Unique)
                }
                fn visit_map<A: serde::de::MapAccess<'de>>(
                    self,
                    mut map: A,
                ) -> Result<Unique, A::Error> {
                    let mut seen = std::collections::BTreeSet::new();
                    while let Some(key) = map.next_key::<String>()? {
                        if !seen.insert(key) {
                            return Err(serde::de::Error::custom("duplicate JSON key"));
                        }
                        map.next_value::<Unique>()?;
                    }
                    Ok(Unique)
                }
            }
            deserializer.deserialize_any(Visitor)
        }
    }
    let _: Unique = serde_json::from_slice(bytes).map_err(|e| invalid(e.to_string()))?;
    Ok(())
}
