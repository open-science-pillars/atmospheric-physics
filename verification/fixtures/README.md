# Fixtures

What the goldens at the top of `verification/` read. Everything here is
committed, offline and deterministic: a golden touches no live service,
needs no credential and carries no secret.

## `wrapped_computations.json`

The expected values of this capability's two wrapping chains, read by
`wrapped_computations.py`.

**Provenance.** Every number in it is quoted from the Reference run
section of the concept it names, in the nasa-daac-knowledge `asdc`
bundle: `knowledge/asdc/computations/energy-budget.md` (signed stable,
verified 2026-09-16) and
`knowledge/asdc/computations/cloud-radiative-effect.md` (signed stable,
verified 2026-09-19). Both are fixture runs at seed 7, which the
executors regenerate deterministically from a hash-based Gaussian
stream with no numeric library in the path, so the values do not drift
with a release of anything. Recorded 2026-09-19.

**What it is not.** It is not a copy of a provider fixture and not a
receipt. The provider's fixtures are generated at run time and are
never committed anywhere; the executors, the attesters and the
committed data roots stay in the provider bundle and arrive with the
dependency. This capability owns none of these numbers, and the file
exists so that a chain which stops reproducing its signed concept fails
the gate.

**When it changes.** Only when the concept it quotes changes its
reference run, and then the concept is the thing to read first. A value
edited here to make a golden pass is the golden lying.
