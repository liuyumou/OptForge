"""Strict versioned session boundary; historical response schemas are unchanged."""
from functools import lru_cache
import jsonschema
from lp_gpup9_common import ROOT, load, require


@lru_cache
def validator():
    return jsonschema.Draft202012Validator(load(ROOT/'schemas/lp-gpup9-session-v1.schema.json'))


def validate_session(row):
    validator().validate(row)
    require(len(row['records'])==row['count'],'session request count')
    require(row['endpoint']!='cold' or row['count']==1,'cold count differs')
    for record in row['records']:
        for field in ['model','result']:
            item=record[field]
            path=(ROOT/item['path']).resolve()
            require(path.is_relative_to(ROOT/'artifacts/gpup9-v1') and '..' not in item['path'].split('/'),'session reference escapes allocation')
    require(row['complete_session_ns']>=row['setup_ns']+row['teardown_ns']+sum(r['complete_ns'] for r in row['records']),'overlapping session costs')
