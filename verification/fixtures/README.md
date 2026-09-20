# Fixtures

What the goldens at the top of `verification/` read. Everything here is
committed, offline and deterministic: a golden touches no live service,
needs no credential and carries no secret.

## `energy-budget-chain.json` and `cloud-radiative-effect-chain.json`

What the two chain goldens read: `energy_budget_chain.py` and
`cloud_radiative_effect_chain.py`, the chains the provider bundle's
check routine ran before the computations moved here.

**Provenance.** The `runs` and the `refusal` of each file are quoted
from the Reference run section of the concept the file names,
`knowledge/computations/energy-budget.md` and
`knowledge/computations/cloud-radiative-effect.md`, which this package
now owns and which were left at `status: draft` by the move of
2026-09-20 pending the maintainer's re-sign. The eight-region table of
`cloud-radiative-effect-chain.json` is measured, not quoted: each cell
is a term of a receipt the attester passed, read from a run on the
committed data root at the new paths on 2026-09-20, and the four cells
the concept states (global and antarctic, both conventions) are
asserted against the quoted runs as well.

**What it is not.** No number here is new. The four runs quoted
reproduced to the digit at the new paths, which is what the move owed,
and the table exists so that the sign reversal of the convention
difference over the polar bands is held by a check rather than by a
sentence.

**When it changes.** When the concept changes a reference run, and
then the concept is the thing to read first. A value edited here to
make a golden pass is the golden lying.

## `wrapped_computations.json`

The expected values of the fixture run of each of this capability's two
attested computations, read by `wrapped_computations.py`, which is also
the release qualification surface.

**Provenance.** Every number in it is quoted from the Reference run
section of the concept it names: `knowledge/computations/energy-budget.md`
and `knowledge/computations/cloud-radiative-effect.md`. Both are
fixture runs at seed 7, which the executors regenerate
deterministically from a hash-based Gaussian stream with no numeric
library in the path, so the values do not drift with a release of
anything. Recorded 2026-09-19, and re-read at the new paths on
2026-09-20 without a number moving.

**What it is not.** It is not a receipt and not a committed fixture:
the fixtures are generated at run time and are never committed
anywhere. The file exists so that a chain which stops reproducing its
concept fails the gate.

**When it changes.** Only when the concept it quotes changes its
reference run, and then the concept is the thing to read first. A value
edited here to make a golden pass is the golden lying.

## `receipt-skills-fixture.json`

What the three receipt skills (`sweep`, `receipt-figures`, `methods`)
produce on this package's executors' synthetic fixtures at seed 7, read
by `receipt_skills.py`.

**Provenance.** Measured, not quoted: the file is written by
`uv run verification/receipt_skills.py --measure` from what the three
skills produce, and every value in it arrives through a receipt. Each
sweep cell is a field of a receipt the bundle's attester passed, copied
by the receipt field path the sweep manifest records beside its column;
each figure digest is the sha256 of an array the renderer drew from
such a receipt; each methods entry is the set of receipt fields a
paragraph was filled from, with the reference ids the concept's own
frontmatter carries. Re-measured 2026-09-20 against this package's
`cloud_radiative_effect.py` and `energy_budget.py`, whose digests the
file names, after the move changed those digests; the fixtures
regenerate deterministically from the seed with no numeric library in
the path, so the values do not drift with a release of anything. The
re-measurement moved no cell by more than 3.2e-14 in absolute value,
which is the last-bit difference between the interpreter that recorded
the previous file and the one that recorded this one, not a change of
method: the moved executors were checked against the provider bundle's
own copies on one interpreter and produce bit-identical receipts.

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
