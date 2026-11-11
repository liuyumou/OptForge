"""CPU-only attribution of the integration service's measured cold overhead."""
import time
import lp_fp4_recovery_contract as policy
from lp_fp4_integrate_common import BASE,put,ref
from lp_fp4_integrate_run import BINARY
from lp_fp4_integrate_model import model,prepare,observation

def main():
 rows=[]
 for repetition in range(3):
  for label,operation in [('policy_schema',lambda:policy.digest(policy.policy())),('binary_hash',lambda:ref(BINARY)),('model',lambda:model('dense-rich-65')),('prepare',lambda:prepare(model('dense-rich-65')[1],4,8))]:
   start=time.monotonic_ns();operation();rows.append(dict(phase=label,repetition=repetition,wall_ns=time.monotonic_ns()-start))
 put(BASE/'host-profile-v1.json',dict(rows=rows));print(rows)
if __name__=='__main__':main()
