"""CPU integration admission before the held-out freeze."""
import subprocess
import sys
from lp_sp_pricing_budget import ROOT

if __name__=='__main__':
    for name,identity in [('lp_sp_pricing_auxiliary_build.py','auxiliary-native-build-v3'),
                          ('lp_sp_pricing_auxiliary_admit.py','auxiliary-sanitizers-v2')]:
        subprocess.run([sys.executable,'-B',str(ROOT/'tools'/name),identity],check=True)
    subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests/integration','-p','test_lp_sp_pricing.py'],check=True)
    subprocess.run([sys.executable,'-B',str(ROOT/'tools/lp_sp_pricing_baseline_seal.py'),'baseline-seal-v1'],check=True)
