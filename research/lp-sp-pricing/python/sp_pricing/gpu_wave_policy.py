"""Do useful exact CPU work while the independently initialized GPU is busy."""
from .gpu_wave import WaveBackend


class OpportunisticWaveBackend(WaveBackend):
    def __call__(self,oracle,*args,**kwargs):
        if self.engine is None and self.future is not None and not self.future.done():
            # Empty proposals invoke the existing exact CPU oracle for this
            # query. No GPU label is guessed and no failed future is suppressed.
            return {},[],dict(backend='wave',startup_policy='cpu_while_initializing',
                reason='initialization_in_progress',gpu_labels=0,batches=[],preparation_ns=0)
        labels,proofs,metadata=super().__call__(oracle,*args,**kwargs)
        metadata['startup_policy']='cpu_while_initializing'
        return labels,proofs,metadata
