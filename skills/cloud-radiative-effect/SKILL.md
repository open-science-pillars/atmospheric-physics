---
name: cloud-radiative-effect
description: "Run the attested cloud radiative effect of the ASDC bundle, the CERES EBAF all-sky flux minus the clear-sky flux of a clear-sky convention the user chooses deliberately, through the provider bundle's sanctioned executor, and attest the receipt before quoting any number from it. Keywords: cloud radiative effect, CRE, cloud forcing, clear-sky, cloud-free area, total region, convention, shortwave, longwave, net, CERES, EBAF, radiation budget, region, latitude band."
---

# cloud-radiative-effect

Run instructions for the attested computation
`knowledge/asdc/computations/cloud-radiative-effect.md` in the provider
bundle: over one stated window and one stated region, the shortwave,
longwave and net effect of clouds on the top-of-atmosphere radiation
budget as the difference between the all-sky and the clear-sky fluxes
of the energy balanced product, each with an uncertainty and the stamp
it came from, the residual of the decomposition of the net effect, the
verdict `decomposition_closes`, the same three terms under the other
clear-sky convention beside them, and the distance from the published
global mean where the run is of its region, convention and period.

This capability computes nothing. The contract (the parameters, the
receipt fields, the refusal codes, the attester criterion) is the
concept and the executor's own usage text; this skill is the procedure
an agent follows to run it, and every number it reports is owned by
that signed concept. Read the concept before the first run, and the
bundle's recipe `knowledge/asdc/recipes/cloud-radiative-effect.md` for
how to read what comes back.

## Where the executor is

The provider bundle arrives with the `nasa-daac-knowledge` dependency.
Its root is the `installPath` of that entry in
`claude plugin list --json`, which is the installer's own record of
what is installed; a checkout named by `NASA_DAAC_KNOWLEDGE` is the one
override, for a workspace that holds the repository beside this one.
`$ASDC` below stands for `<that root>/knowledge/asdc`:

- concept: `$ASDC/computations/cloud-radiative-effect.md`
- executor: `$ASDC/references/computations/cloud_radiative_effect.py`
- attester: `$ASDC/references/attesters/cloud_radiative_effect_check.py`
- the committed data root: `$ASDC/references/retrieval/cloud-radiative-effect-root`
- the loaders that built it: `$ASDC/references/loaders/cre_ceres_fluxes.py`
  and `cre_data_root.py`

Never edit the executor or the attester. The attester hashes the
executor on disk, so an edited computation invalidates every earlier
receipt by construction.

## The parameters this skill binds

The concept declares three parameters, and this skill binds all three
on every run:

- `window` (string, required), bound as `--window YYYY-MM:YYYY-MM`: an
  inclusive month range inside the flux record, at least 24 months of
  which carry a value.
- `region` (string, required), bound as `--region NAME`: one of
  `global`, `tropics`, `northern-extratropics`,
  `southern-extratropics`, `northern-midlatitudes`,
  `southern-midlatitudes`, `arctic`, `antarctic`. Each is a band of
  whole one degree zones. A region that would need a surface type or
  sea ice mask (`ocean`, `land`, `sea-ice`) is refused, because the
  fields read carry no such field.
- `clear_sky` (string, required), bound as `--clear-sky CONVENTION`:
  `total-region` or `cloud-free-area`, the two conventions the energy
  balanced product's variables carry. The next section is how this
  value is settled, and it is never settled by this skill.

The rest of the command line is execution plumbing, not science:
`--runtime NAME` names the runtime that ran it (from Claude Code pass
`--runtime claude-code`, with `--runtime-version V` where the runtime
states one); `--fixture [--seed N]` or `--data-root DIR` selects the
input; `--receipt PATH` says where the receipt is written;
`--capability-root DIR` names the package tree a run is evidence for.
The run identifier is bound to the runtime name.

## The clear-sky convention is the user's choice, made out loud

The product carries two fields that are both called clear-sky. A cloud
radiative effect inherits the convention of whichever one is
subtracted, and nothing in a difference of two flux variables records
which that was. So before any run:

1. State the two conventions in the words of
   `knowledge/asdc/conventions/ceres-clear-sky-conventions.md`, which
   owns what each one is, and
   `knowledge/asdc/gotchas/ebaf-clear-sky-definitions.md`, which owns
   the edition history and the published size of the adjustment between
   them. Cite both by bundle path and restate neither's numbers as your
   own.
2. Say what turns on the choice for this particular request: a
   comparison with a published figure, with another study, or with the
   product's own cloud radiative effect variables each implies a
   convention, and the convention of the target is the convention to
   bind.
3. Ask the user to choose, and bind what they say. Do not default,
   do not pick the one the last run used, and do not pick the one that
   makes a comparison land closer. Where the user has no preference,
   say which convention the thing they are comparing against carries
   and let them confirm that one.

Every receipt carries a `convention_contrast` block: the same three
terms over the same window and region under the other convention, with
the difference. Report that block on every run, next to the bound
convention's terms and never instead of them. The contrast is the size
of the incomparability between the two, not a conversion; no
conversion between them is computed, because the documentation
publishes no per-cell conversion. The sign of the difference is not
the same everywhere, so a regional effect cannot be moved between
conventions by a single global number.

## Behavior, in order

1. **Parse and show back:** the window, the region, the convention the
   user chose and why, and whether the run is a rehearsal on the
   synthetic fixture or a real run on the committed data root. Consult
   the concept, the convention concept and the clear-sky gotcha, and
   cite all three by bundle path, the concept first, because it is the
   one that owns every number this run can report:
   `knowledge/asdc/computations/cloud-radiative-effect.md`,
   `knowledge/asdc/conventions/ceres-clear-sky-conventions.md` and
   `knowledge/asdc/gotchas/ebaf-clear-sky-definitions.md`.
2. **The fixture run** (the rehearsal, and the reference the concept
   records):

   ```bash
   uv run $ASDC/references/computations/cloud_radiative_effect.py \
     --fixture --seed 7 --window 2006-01:2020-12 \
     --region global --clear-sky total-region \
     --runtime claude-code --receipt /tmp/cre-receipt.json
   ```

   The fixture is regenerated deterministically from the seed (a
   hash-based Gaussian stream, no numeric library in the path), with a
   planted effect and a planted per-region convention offset; the
   attester regenerates it and compares every value. A fixture receipt
   says in its own caveats that it proves the chain and not the Earth,
   and a report of a fixture run says the same.
3. **The real run on the committed data root:**

   ```bash
   uv run $ASDC/references/computations/cloud_radiative_effect.py \
     --data-root $ASDC/references/retrieval/cloud-radiative-effect-root \
     --window 2005-07:2015-06 --region global --clear-sky cloud-free-area \
     --runtime claude-code --receipt /tmp/cre-record.json
   ```

   The root carries `RECORD.json` (the stamp, the manifest, the
   coverage table and the bookkeeping table), `cre-fluxes.csv`,
   `cre-fluxes-stamp.json` and `SOURCES.json`, and covers 2000-03
   through 2026-05 for the eight regions and both conventions. The
   executor checks every file against its manifest hash before it reads
   a number, and refuses a stamp missing any required statement.
4. **The refusal rule.** A refusal is never a number: the run writes a
   refusal receipt with `refused: true`, a reason code and the reason
   in words, and exits 3.

   ```bash
   uv run $ASDC/references/computations/cloud_radiative_effect.py \
     --fixture --window 2006-01:2020-12 --region global --clear-sky pristine \
     --runtime claude-code --receipt /tmp/refusal.json
   echo $?   # 3, and the receipt carries clear-sky-convention-not-carried
   ```

   The codes are `clear-sky-convention-not-carried` (`pristine`,
   `computed-cloud-removed` and `total-sky-no-aerosol` are SYN1deg
   quantities and this product has no such field),
   `region-not-resolvable`, `window-outside-record`, `too-few-months`
   and `interval-not-stated`. The first two are settled by the bound
   parameters alone and the attester reproduces them without the
   record. Report the refusal in the executor's own words; a refusal
   attests PASS only as a refusal, and the verdict line reads
   `PASS refusal`.
5. **Attest before quoting anything.** Every number quoted from a
   receipt comes after the attester has said PASS on that exact
   receipt:

   ```bash
   uv run $ASDC/references/attesters/cloud_radiative_effect_check.py \
     /tmp/cre-receipt.json [--data-root DIR] [--out /tmp/attestation.json]
   ```

   A data-root receipt is attested with `--data-root DIR` naming the
   tree: without it the data digests are taken on the executor's word
   and are not verified. The checks are `fields`, `code`, `release`,
   `runtime`, `data`, `convention`, `region`, `series`, `recompute`,
   `bookkeeping` and `plausible`; `--out` writes the attestation for a
   qualification record, and `--selftest` runs the tampers, the wrong
   release, all five refusals and the forged cases. Report the
   attester's verdict, not your own reading of the numbers.
6. **Report**, with each of these beside the number it qualifies: the
   three terms with their uncertainties and the sign rule each follows;
   the residual against the stated decomposition tolerance and the
   verdict; the combined uncertainty, stated as carried beside the
   verdict and not as its bar, because the three terms are three views
   of one month's fields; the bound convention, the variable suffix the
   receipt says it read, and the other convention's three terms with
   the difference; the region as its latitude band; the months used and
   missing; the run identifier and the runtime name; and the attester's
   verdict. Then the caveats the concept states:

   - **A cloud radiative effect is not a cloud feedback.** It is the
     difference clouds make to the flux in the atmosphere as it was,
     not the response of clouds to warming.
   - **The published distance is stated, not gated,** and only where
     the run is of the region, convention and period the published
     figure is of. It carries both the rounding of the published table
     and the change of edition since it, and is a measurement of
     neither. A run on the other convention over the same months states
     no distance, and the receipt records that refusal to compare.
   - **No trend is computed here.** A window crossing the satellite
     transitions carries the climatology adjustments the record is
     stitched with, which the bundle's dataset concept owns.
   - **The product's anchoring does not reach these terms,** because
     the one-time adjustment enters the all-sky and the clear-sky field
     of the same month and cancels in their difference. That is why
     this concept carries no anchoring block where the bundle's energy
     budget computation carries one.

## Must NOT

- Never quote a number from a receipt the attester has not passed, and
  never edit the sanctioned executor or attester.
- Never bind a clear-sky convention the user did not choose, and never
  report a term without naming the convention it is of.
- Never compare two runs on different conventions as though the
  difference were physical, and never convert between the conventions
  with a single offset; report the receipt's contrast block instead.
- Never present a refusal as a number, and never approximate a region
  the computation refuses or a convention the product does not carry.
- Never report the published distance for a run whose region,
  convention or period is not the published figure's.
- Never state a number this release owns. Every figure in a report
  comes from the receipt or from the concept, cited by bundle path.
- Never commit a receipt, an attestation or a generated fixture to this
  repository.
