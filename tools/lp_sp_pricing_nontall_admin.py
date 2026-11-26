"""CPU-only contract admission for the fresh non-tall harness."""
import unittest
from lp_sp_pricing_budget import ROOT,BASE,put,binding
from lp_sp_pricing_transform_admit import validate
from lp_sp_pricing_nontall_experiment import sources


if __name__=='__main__':
    gate=validate();out=BASE/'nontall-contracts-v1';out.mkdir(exist_ok=False)
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests/integration'),'test_lp_sp_pricing_nontall.py')
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful() or result.testsRun!=3 or result.skipped:raise RuntimeError('non-tall contracts failed')
    for name in ('lp_sp_pricing_nontall_budget.py','lp_sp_pricing_nontall_experiment.py','lp_sp_pricing_nontall_driver.py'):
        path=ROOT/'tools'/name;compile(path.read_text(),str(path),'exec')
    put(out/'result.json',dict(status='passed',tests=result.testsRun,numerical_admission=gate,sources=sources()))
