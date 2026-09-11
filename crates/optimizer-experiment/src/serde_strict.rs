//! Shared strict-JSON deserialization helpers.
//!
//! Serde's derived implementations accept a positional sequence wherever a
//! struct is expected. Every public input document in this crate requires a JSON
//! object instead, so shapes cannot drift between records and arrays.

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

// Serde's struct derive accepts positional sequences. Require a map before
// delegating field validation, preserving duplicate/unknown-field rejection.
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
