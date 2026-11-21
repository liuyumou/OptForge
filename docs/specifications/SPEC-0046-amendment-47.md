# SPEC-0046 amendment 47: prospectively place the unattempted 512 M pair in development

The nine fresh 64 M capacity cells complete without an outer overrun. The 256 M
coupled CPU cell returns after about 205 seconds; the coupled GPU cell reaches
its owned-child deadline and retains the full 960 CPU / 240 GPU reservation,
missing response, empty cleanup and overrun=false. Preserve every attempted cell.
The remaining admission phase balance cannot reserve both planned 512 M cells.
Do not change prior charges or total/phase caps to hide that fact.

The two still-unattempted 512 M cells are numerical capacity-development
measurements. Prospectively reserve them in the existing development phase, each
with 600 process seconds, 128 GiB aggregate host, 80 GiB owned GPU, unchanged
120-second requested vendor solver allowance and a separate 300-second strict
final-check reservation. The larger process envelope follows the observed vendor
setup delays. Their complete 4800 CPU / 1200 GPU reserve fits unused development
capacity; the full billion freeze must additionally fit all remaining solve,
audit and storage reservations afterward. All 320000/35000 total and individual
phase caps remain unchanged. No new resource readmission is needed for an unchanged
supervisor, capacity guard or numerical image.

Pause only the exact outer continuation driver launched by this task, outside the
supervised process family, while its already-running 256 M children finish. Record
its command/PID/start identity and leave current scientific jobs untouched. Once
the 256 M completion receipt exists and no reservation is active, terminate that
owned idle outer driver and start the separately frozen 512 M development pair.
Never signal an unrelated process or change GPU configuration. This prevents the
old coordinator from attempting a known-unfunded admission-stage freeze.

Preserve the original 64 M, tail 64/256 M manifests, all failures, and every raw
response. The 512 M manifest binds this prospective classification, the unchanged
native adapter and capacity worker, and its new coordinator. A larger-scale result
never regrades an interrupted lower-scale cell. No attempted scientific cell repeats.
