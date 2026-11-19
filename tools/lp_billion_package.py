"""Integrity replay from a relocated hardlinked root, without duplicating large data."""
import argparse
import os
import shutil
from lp_billion_common import BASE,load,put,ref,require
from lp_billion_portable import build,replay


def package(identity,resource):
    build(identity,[resource])
    out=BASE/'portable'/identity;manifest=out/'manifest.json'
    view=BASE/'portable-view';view.mkdir(exist_ok=False)
    for item in load(manifest)['entries']:
        source=BASE/item['path'];target=view/item['path']
        require(target.resolve().is_relative_to(view),'relocated path containment')
        target.parent.mkdir(parents=True,exist_ok=True)
        os.link(source,target)
    shutil.copyfile(manifest,view/'manifest.json')
    replay(view,view/'manifest.json',out/'relocated-replay.json')
    shutil.rmtree(view)
    put(out/'result.json',dict(status='passed',catalog=ref(manifest),
        relocated_replay=ref(out/'relocated-replay.json'),
        content_verified_during_catalog_and_relocated_replay=True,
        temporary_view_removed=not view.exists(),
        scope='Integrity replay; original scalar numerical checking is recorded separately.'))
    print(load(out/'relocated-replay.json'),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--resource',required=True)
    a=p.parse_args();package(a.id,a.resource)
