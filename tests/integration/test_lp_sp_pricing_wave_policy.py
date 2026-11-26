"""A busy initialization must neither block useful CPU work nor hide failure."""
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'research/lp-sp-pricing/python'))
from sp_pricing.gpu_wave import WaveBackend
from sp_pricing.gpu_wave_policy import OpportunisticWaveBackend


class OpportunisticInitialization(unittest.TestCase):
    def test_busy_future_returns_no_labels_without_waiting_or_packing(self):
        backend=OpportunisticWaveBackend();backend.future=Mock();backend.future.done.return_value=False
        labels,proofs,meta=backend(object())
        self.assertEqual(labels,{});self.assertEqual(proofs,[])
        self.assertEqual(meta['reason'],'initialization_in_progress');backend.future.result.assert_not_called()

    def test_ready_future_uses_the_admitted_wave_backend(self):
        backend=OpportunisticWaveBackend();backend.future=Mock();backend.future.done.return_value=True
        with patch.object(WaveBackend,'__call__',return_value=({1:-1},[],dict(gpu_labels=1))) as implementation:
            labels,proofs,meta=backend(object(),steps=256)
            self.assertEqual(labels,{1:-1});self.assertEqual(meta['startup_policy'],'cpu_while_initializing')
            implementation.assert_called_once()

    def test_ready_failure_is_not_hidden_by_cpu_fallback(self):
        backend=OpportunisticWaveBackend();backend.future=Mock();backend.future.done.return_value=True
        with patch.object(WaveBackend,'__call__',side_effect=RuntimeError('CUDA setup failure')):
            with self.assertRaisesRegex(RuntimeError,'CUDA setup failure'):backend(object())

    def test_teardown_waits_for_and_releases_an_unused_session(self):
        backend=OpportunisticWaveBackend();backend.future=Mock();backend.pool=Mock()
        engine=backend.future.result.return_value
        backend.__exit__(None,None,None)
        backend.future.result.assert_called_once();engine.close.assert_called_once()
        backend.pool.shutdown.assert_called_once_with(wait=True)


if __name__=='__main__':unittest.main()
