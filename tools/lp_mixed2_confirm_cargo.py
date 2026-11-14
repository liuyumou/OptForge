#!/usr/bin/env python3
import json,os,sys
cpus=json.loads(os.environ["LP_CPU_ALLOWED_CPUS"])
os.sched_setaffinity(0,set(cpus[:3]))
os.execv("/tmp/ai-optimizer-cargo/bin/cargo",["cargo",*sys.argv[1:]])
