"""Bounded shared-memory phase diagnostics; no per-sample file writes."""
from collections import defaultdict
import mmap
import os
import struct
import time

CAPACITY=262144
RECORD=struct.Struct('<QQQQQQ')
HEADER=struct.Struct('<Q')
PHASES={1:'scan',2:'pidfd_wait',3:'sample_start_gap'}


class Trace:
    def __init__(self):
        self.memory=mmap.mmap(-1,HEADER.size+CAPACITY*RECORD.size)

    def span(self,phase,start,end,cpu_start,cpu_end):
        sequence=HEADER.unpack_from(self.memory)[0]
        RECORD.pack_into(self.memory,HEADER.size+(sequence%CAPACITY)*RECORD.size,
                         sequence,phase,start,end,cpu_start,cpu_end)
        HEADER.pack_into(self.memory,0,sequence+1)

    def summarize(self):
        count=HEADER.unpack_from(self.memory)[0];groups=defaultdict(list)
        for seq in range(max(0,count-CAPACITY),count):
            row=RECORD.unpack_from(self.memory,HEADER.size+(seq%CAPACITY)*RECORD.size)
            if row[0]!=seq:raise RuntimeError('incomplete phase trace record')
            _,phase,start,end,cpu_start,cpu_end=row
            if phase not in PHASES or end<start or cpu_end<cpu_start:
                raise RuntimeError('invalid phase trace record')
            groups[PHASES[phase]].append(dict(sequence=seq,start_ns=start,end_ns=end,
                wall_ns=end-start,cpu_ns=cpu_end-cpu_start))
        result={}
        for phase,rows in groups.items():
            ordered=sorted(rows,key=lambda r:r['wall_ns']);n=len(rows)
            result[phase]=dict(count=n,median_wall_ns=ordered[(n-1)//2]['wall_ns'],
                p99_wall_ns=ordered[min(n-1,int(n*.99))]['wall_ns'],max_wall_ns=ordered[-1]['wall_ns'],
                total_wall_ns=sum(r['wall_ns'] for r in rows),total_cpu_ns=sum(r['cpu_ns'] for r in rows),
                over_100ms=sum(r['wall_ns']>100_000_000 for r in rows),
                largest=ordered[-32:],over_100ms_records=[r for r in rows if r['wall_ns']>100_000_000][:4096])
        return dict(total_records=count,captured_records=min(count,CAPACITY),truncated=count>CAPACITY,
                    phases=result,limitations='Overlapping phase clocks are not additive. Process CPU time does not attribute off-CPU delay to a specific cause. Diagnostic instrumentation may perturb timing.')


def install(supervisor,prefix):
    trace=Trace();original_run=supervisor.run;original_coordinator=supervisor.coordinator
    original_snapshot=supervisor.snapshot;original_select=supervisor.select.select;original_send=supervisor.send
    delay=int(os.environ.get('MIXED2_CONFIRM2_SCAN_DELAY_MS','0'))
    if not 0<=delay<=1500:raise ValueError('diagnostic scan delay')

    def coordinator(*args,**kwargs):
        owner=os.getpid();previous=None

        def snapshot(root,cpus,additional=()):
            if os.getpid()!=owner or not additional:return original_snapshot(root,cpus,additional)
            start=time.monotonic_ns();cpu=time.process_time_ns()
            try:
                if delay:time.sleep(delay/1000)
                return original_snapshot(root,cpus,additional)
            finally:trace.span(1,start,time.monotonic_ns(),cpu,time.process_time_ns())

        def select(read,write,error,timeout=None):
            if os.getpid()!=owner or timeout!=.005:return original_select(read,write,error,timeout)
            start=time.monotonic_ns();cpu=time.process_time_ns()
            try:return original_select(read,write,error,timeout)
            finally:trace.span(2,start,time.monotonic_ns(),cpu,time.process_time_ns())

        def send(channel,value):
            nonlocal previous
            if os.getpid()==owner and value.get('event')=='heartbeat':
                now=value['timestamp_ns'];cpu=time.process_time_ns()
                if previous:trace.span(3,previous[0],now,previous[1],cpu)
                previous=(now,cpu)
            return original_send(channel,value)

        supervisor.snapshot=snapshot;supervisor.select.select=select;supervisor.send=send
        return original_coordinator(*args,**kwargs)

    def run(request):
        try:return original_run(request)
        finally:
            result=trace.summarize();result['injected_scan_delay_ms']=delay
            supervisor.atomic_json(str(prefix)+'.phases.json',result)
            trace.memory.close()

    supervisor.coordinator=coordinator;supervisor.run=run
