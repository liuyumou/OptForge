# GPUP-8 receipt-link recovery

Status: **incomplete**. Sixteen explicit corrected trial views bind the
existing independent verification receipts. Every original trial retains its null
link; the original sources, failure reports and full charges remain unchanged.
The strict original verifier reader consumes the corrected views. No passed test,
profile or retained numerical verification is rerun.

The [machine report](data/tensor-warp32/receipt-recovery-result-v1.json) uses the
unchanged scientific forecast, certification and multiplicity-adjusted latency
calculations. Profile gate: true.
Forecast working families: true.
Gain forecast passes: false. Certified
timings: 0/60. Certified timing families:
false. Adjusted certified total-latency gain:
false.

Recorded stop: forecast — unchanged gain forecast refused.

This recovery charges 0.000000000 GPU seconds. Combined
warp32 GPU consumption is 369.700946478 / 1640. GPUP-8 is
1232.909411024 / 3000; campaign is
22592.495266813 / 25202.574545061. The ledger has
17412 events, SHA-256 `9913d391634bdb0f74012be909be377e5a693d00b76e6882abcf336796ac863e`, preserving
the exact 17412-event prefix and every older prefix. Phase caps remain 330/320/990.

Only unused CPU allocations are used, under the unchanged 53640 ceiling.
Final CPU accounting is **45902.541829170 / 53640**, including
843.323873964 CPU seconds for this recovery, entirely from existing funds.
Reporting retains 315.762945624 CPU seconds; the 6400-second timing allocation remains
unused. All 168 documentation pages/internal links, source/preservation and diff
checks pass; every workload and guardian cleanup is empty. The [final accounting](data/tensor-warp32/receipt-final-cpu-accounting-v1.json)
retains all prior charges and unused funds. GPUP-9 remains
gated. No automatic retry, host/container/supervisor change, bootstrap rerun,
publication or merge occurs.

The unchanged thresholds and all six forecasts are retained below. These are
admission forecasts, not measured timing speedups.

| Model | Configuration | Forecast seconds | Limit seconds |
| --- | --- | ---: | ---: |
| small dense | fp16-tensor | 0.705380423 | 0.415902600 |
| small dense | int8-tensor | 0.642764297 | 0.415902600 |
| small dense | bf16-tensor | 0.722332868 | 0.415902600 |
| large dense | bf16-tensor | 9.177217471 | 5.697919800 |
| large dense | int8-tensor | 8.990098918 | 5.697919800 |
| large dense | fp16-tensor | 8.977063370 | 5.697919800 |
