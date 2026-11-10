"""Compiled validation of the exact two flat baseline array schemas.

No numeric conversion changes. The original semantic/finite checks still run.
No arbitrary schema dialect is accepted by this optional adapter.
"""
from functools import lru_cache
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'artifacts/gpup-external-baseline-v4/python-fast'))
import fastjsonschema
from jsonschema import ValidationError
from validate_artifacts import read_json_bytes, validator as original_validator


@lru_cache(maxsize=None)
def validator(name):
    if name not in ('lp-baseline-model-v1.schema.json','lp-baseline-endpoint-v1.schema.json'):
        return original_validator(name)
    schema=read_json_bytes((ROOT/'schemas'/name).read_bytes())
    # These frozen schemas use only keywords with unchanged Draft-7 semantics.
    forbidden={'$ref','$dynamicRef','prefixItems','unevaluatedProperties','unevaluatedItems',
               'dependentRequired','dependentSchemas','default','format','contains'}
    def check(value):
        if isinstance(value,dict):
            if forbidden.intersection(value): raise ValueError('unsupported compiled schema keyword')
            for child in value.values(): check(child)
        elif isinstance(value,list):
            for child in value: check(child)
    check(schema)
    compiled=fastjsonschema.compile(schema,use_default=False)
    class Validator:
        def validate(self,document):
            # fastjsonschema compares numeric const with Python ==; JSON Schema
            # distinguishes boolean true from numeric one. Both frozen schemas
            # have exactly this one numeric const, at schema_version.
            if isinstance(document,dict) and type(document.get('schema_version')) is bool:
                raise ValidationError('schema_version boolean differs from numeric const')
            try: compiled(document)
            except fastjsonschema.JsonSchemaException as error:
                raise ValidationError(str(error)) from error
    return Validator()


def install():
    import lp_baseline_contract
    lp_baseline_contract.validator=validator
