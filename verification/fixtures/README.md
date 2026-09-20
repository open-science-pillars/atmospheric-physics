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

## `receipt-skills-fixture.json`

What the three receipt skills (`sweep`, `receipt-figures`, `methods`)
produce on the ASDC executors' synthetic fixtures at seed 7, read by
`receipt_skills.py`.

**Provenance.** Measured, not quoted: the file is written by
`uv run verification/receipt_skills.py --measure` from what the three
skills produce, and every value in it arrives through a receipt. Each
sweep cell is a field of a receipt the bundle's attester passed, copied
by the receipt field path the sweep manifest records beside its column;
each figure digest is the sha256 of an array the renderer drew from
such a receipt; each methods entry is the set of receipt fields a
paragraph was filled from, with the reference ids the concept's own
frontmatter carries. Recorded 2026-09-20 against the `asdc` bundle's
`cloud_radiative_effect.py` and `energy_budget.py`, whose digests the
file names; the fixtures regenerate deterministically from the seed
with no numeric library in the path, so the values do not drift with a
release of anything.

**What it is not.** It is not a receipt, not a copy of a provider
fixture, and not a number this capability owns. The run identifier of a
fixture run is bound to the runtime name and is deliberately not
recorded, and neither is any bit-exact digest of a derived float. A
window mean is not bit-reproducible across interpreters: CPython 3.12
changed float `sum()` to compensated summation, so the same executor on
the same fixture writes means whose last bits differ under 3.11 and
under 3.12, while the fixture itself hashes the same under both (its
generator is a stdlib hash stream). The cells here are therefore
compared with a relative tolerance of 1e-9, and each figure's drawn
arrays are checked against the receipt they were drawn from inside the
same run rather than against a recorded digest.

**When it changes.** When an executor's digest changes, which the
golden reports by name, and then the provider bundle's change is the
thing to read first; or when a skill deliberately changes which receipt
field a column, a figure or a sentence reads. Re-measure with
`--measure` and say in the pull request what moved and why. A value
edited here to make the golden pass is the golden lying.
