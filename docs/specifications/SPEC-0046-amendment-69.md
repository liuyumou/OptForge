# SPEC-0046 amendment 69: preserve old-total assertion failure

Operational CPU v27 passes all 75 supervisor tests, then fails the resource test
whose total assertions still read 320000 CPU / 35000 GPU seconds. Preserve its
original output, source snapshot, empty cleanup and full 720 CPU-second charge.
The actual caps match the explicit amendment-67 approval; update the assertions
to 370000 / 44000, leaving all physical and supervision checks unchanged.

Fresh CPU v28 precedes the still-unattempted GPU v22. New additive cleanup plans
bind those identities. No scientific measurement or failed reservation repeats.
The approved allocation, phase caps, strict certificates and idle guards remain
unchanged. Remove duplicate discovery of an imported historical test class while
retaining that class in its original test module.
