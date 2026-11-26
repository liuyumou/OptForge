"""Opt-in precomputed GPU projection with the unchanged exact postprocessor."""
import argparse
from pathlib import Path
from unittest.mock import patch
from lp_sp_pricing_budget import ROOT
from lp_sp_pricing_factor_run import run
from sp_pricing import factor_projection

LIBRARY=ROOT/'research/lp-sp-pricing/target/release/libsp_factor_transform.so'


def transformed(model,output,seconds=60,rho_multiplier=1,representation='transform'):
    if rho_multiplier not in (1,4,16,64):raise ValueError('prespecified rho multiplier')
    if representation not in ('factor','transform'):raise ValueError('projection representation')
    selected_library=LIBRARY if representation=='transform' else factor_projection.LIBRARY
    original=factor_projection.projection
    original_gpu=factor_projection.GpuProjection
    class ScaledProjection(original_gpu):
        def __init__(self,a,b,c,rho):super().__init__(a,b,c,rho*rho_multiplier)
    def projection(a,b,c,*args,**kwargs):
        x,y,detail=original(a,b,c,*args,**kwargs)
        m,n=a.shape;detail.update(method='precomputed_factorized_projection' if representation=='transform' else 'scaled_factorized_projection',
            stored_matrix_entries=(2 if representation=='transform' else 1)*m*n+n*n,
            per_iteration_triangular_solves=0 if representation=='transform' else 2,representation=representation,
            rho=detail['rho']*rho_multiplier,rho_multiplier=rho_multiplier)
        return x,y,detail
    with patch.object(factor_projection,'LIBRARY',selected_library),patch.object(factor_projection,'projection',projection),patch.object(factor_projection,'GpuProjection',ScaledProjection):
        return run(model,output,seconds,True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('model',type=Path);p.add_argument('output',type=Path);p.add_argument('--seconds',type=float,default=60)
    p.add_argument('--rho-multiplier',type=int,choices=[1,4,16,64],default=1)
    p.add_argument('--representation',choices=['factor','transform'],default='transform')
    a=p.parse_args();raise SystemExit(int(transformed(a.model,a.output,a.seconds,a.rho_multiplier,a.representation)))
