"""Supplemental native RREF sanitizer coverage, without numerical source changes."""
import sys
import subprocess
from lp_sp_pricing_budget import ROOT,BASE,put,binding
from lp_sp_pricing_geometry_experiment import admission
from lp_sp_pricing_geometry_admit import sources
identity=sys.argv[1];gate=admission();out=BASE/identity;out.mkdir(exist_ok=False)
source=ROOT/'tests/native/sp_geometry_rref.cpp';binary=out/'sanitized'
command=['g++','-std=c++17','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',
 str(ROOT/'research/lp-sp-pricing/native/geometry_exact.cpp'),str(source),'/usr/lib/x86_64-linux-gnu/libgmp.so.10.4.1','-o',str(binary)]
subprocess.run(command,check=True)
with (out/'sanitizer.log').open('x') as stream:subprocess.run([str(binary)],stdout=stream,stderr=subprocess.STDOUT,check=True)
put(out/'result.json',dict(status='passed',admission=gate,numerical_sources=sources(),test=binding(source),
 cases=64,log=binding(out/'sanitizer.log'),source=binding(__file__)))
