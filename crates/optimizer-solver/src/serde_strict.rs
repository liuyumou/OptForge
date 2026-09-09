//! Strict-JSON deserialization helpers for this crate's public documents.
//!
//! Serde's derived implementations accept a positional sequence wherever a
//! struct is expected. Every public input document here requires a JSON object
//! instead, matching the rule optimizer-core applies to model and solve
//! documents so shapes cannot drift between records and arrays.

use serde::Deserialize;

/// Require a JSON object before delegating to `T`'s field validation.
pub(crate) fn object<'de, D: serde::Deserializer<'de>, T: Deserialize<'de>>(
    deserializer: D,
) -> Result<T, D::Error> {
    struct ObjectVisitor<T>(std::marker::PhantomData<T>);

    impl<'de, T: Deserialize<'de>> serde::de::Visitor<'de> for ObjectVisitor<T> {
        type Value = T;

        fn expecting(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
            formatter.write_str("an object")
        }

        fn visit_map<A: serde::de::MapAccess<'de>>(self, map: A) -> Result<T, A::Error> {
            T::deserialize(serde::de::value::MapAccessDeserializer::new(map))
        }
    }

    deserializer.deserialize_map(ObjectVisitor(std::marker::PhantomData))
}

// Require a map before delegating field validation, preserving unknown and
// duplicate field rejection.
macro_rules! deserialize_object {
    ($name:ident { $($field:ident: $ty:ty),+ $(,)? }) => {
        impl<'de> serde::Deserialize<'de> for $name {
            fn deserialize<D: serde::Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
                #[derive(serde::Deserialize)]
                #[serde(deny_unknown_fields)]
                struct Fields {
                    $($field: $ty),+
                }

                let fields: Fields = $crate::serde_strict::object(deserializer)?;
                Ok(Self { $($field: fields.$field),+ })
            }
        }
    };
}

pub(crate) use deserialize_object;
