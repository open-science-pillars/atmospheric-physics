---
name: energy-budget-closure
description: "Run the attested energy budget closure of the ASDC bundle, the CERES EBAF net top-of-atmosphere flux against the Argo ocean heat content rate with the published deep ocean and non-ocean terms, through the provider bundle's sanctioned executor, and attest the receipt before quoting any number from it. Keywords: energy budget, Earth energy imbalance, EEI, budget closure, CERES, EBAF, net TOA flux, ocean heat content, Argo, heat inventory, anchoring, anomaly trend."
---

# energy-budget-closure

Run instructions for the attested computation
`knowledge/asdc/computations/energy-budget.md` in the provider bundle:
over one stated window of calendar months, four rate terms in watts per
square metre of the Earth's surface with the stamp each came from
(`toa_net`, `ohc_0_2000`, `deep_ocean`, `non_ocean`), the residual, the
combined uncertainty, the verdict `closed_within_uncertainty`, the same
four terms as energy over the window in zettajoules, and beside them
the EBAF net flux anomaly against the window's own mean with its linear
trend, in which the product's anchor cancels.

This capability computes nothing. The contract (the parameter, the
receipt fields, the refusal codes, the attester criterion) is the
concept and the executor's own usage text; this skill is the procedure
an agent follows to run it, and every number it reports is owned by
that signed concept. Read the concept before the first run, and read
the bundle's recipe `knowledge/asdc/recipes/energy-budget.md` for how
to read what comes back.

## Where the executor is

The provider bundle arrives with the `nasa-daac-knowledge` dependency.
Its root is the `installPath` of that entry in
`claude plugin list --json`, which is the installer's own record of
what is installed; a checkout named by `NASA_DAAC_KNOWLEDGE` is the one
override, for a workspace that holds the repository beside this one.
`$ASDC` below stands for `<that root>/knowledge/asdc`:

- concept: `$ASDC/computations/energy-budget.md`
- executor: `$ASDC/references/computations/energy_budget.py`
- attester: `$ASDC/references/attesters/energy_budget_check.py`
- the committed data root: `$ASDC/references/retrieval/energy-budget-root`
- the loaders that built it: `$ASDC/references/loaders/eb_ceres_ebaf.py`
  and `eb_data_root.py`

Never edit the executor or the attester. The attester hashes the
executor on disk, so an edited computation invalidates every earlier
receipt by construction.

## The parameters this skill binds

The concept declares one parameter, and this skill binds it on every
run:

- `window` (string, required), bound as `--window YYYY-MM:YYYY-MM`: an
  inclusive month range inside the radiation record. The Argo receipt
  read for the ocean side must be over this same window; its rate is a
  whole-window quantity and a receipt over any other window is refused.

The rest of the command line is execution plumbing, not science:
`--runtime NAME` names the runtime that ran it (from Claude Code pass
`--runtime claude-code`, from another runtime its own name, with
`--runtime-version V` where the runtime states one); `--fixture
[--seed N]` or `--data-root DIR [--ohc-receipt PATH]` selects the
input; `--receipt PATH` says where the receipt is written;
`--capability-root DIR` names the package tree a run is evidence for.
The run identifier is bound to the runtime name, so the same run under
two runtime names carries two identifiers and the same numbers.

## The ocean side is a receipt, never a recomputation

`ohc_0_2000` is not computed here and not computed by the executor.
It is read from the Argo ocean heat content receipt that the
ocean-science capability's computation
(`knowledge/computations/argo-ohc.md` in that capability, executor
`argo_ohc.py`, wrapped by its `argo-ohc` skill) produced on that
capability's own committed data root, attested there, and placed in
this bundle's data root as
`$ASDC/references/retrieval/energy-budget-root/ohc-2000-receipt.json`.
The executor copies that receipt's identity (its computation, code
digest, run id, window, bundle and record) into its own receipt, and
the attester checks the copy against the tree.

What follows from that, and belongs in every report:

- Another window needs another Argo receipt over exactly that window,
  produced and attested in ocean-science first. Never relabel a
  receipt's window, never interpolate one, and never substitute an
  ocean heat content number from anywhere else.
- The Argo rate is over the Roemmich and Gilson product's mapped
  open-ocean domain and is never scaled to the global ocean, so it
  understates the global ocean by construction. The concept's reference
  run states the size of that understatement and what it would do to
  the residual.
- `deep_ocean` and `non_ocean` are published rates over their own
  periods, carried as terms with their sources. They are not
  measurements over the window.

## Behavior, in order

1. **Parse and show back:** the window; whether the run is a rehearsal
   on the synthetic fixture or a real run on the committed data root;
   which Argo receipt the ocean side will come from and over what
   window; and what the user means to do with the verdict. Consult the
   concept and the two gotchas it rests on, and cite all three by bundle
   path, the concept first, because it is the one that owns every number
   this run can report: `knowledge/asdc/computations/energy-budget.md`,
   then `knowledge/asdc/gotchas/ebaf-imbalance-anchored-to-ocean-heating.md`
   (the anchor, its decade, and what the ocean data did not set) and
   `knowledge/asdc/gotchas/ebaf-climatology-baseline.md` (the product's
   climatology base period, which this computation never uses as the
   anomaly baseline). Restate what each fixes about the bookkeeping
   before anything runs.
2. **The fixture run** (the rehearsal, and the reference the concept
   records):

   ```bash
   uv run $ASDC/references/computations/energy_budget.py \
     --fixture --seed 7 --window 2006-01:2020-12 \
     --runtime claude-code --receipt /tmp/energy-budget-receipt.json
   ```

   The fixture is regenerated deterministically from the seed (a
   hash-based Gaussian stream, no numeric library in the path), with a
   planted level, trend and closure and a planted Argo-shaped receipt;
   the attester regenerates it and compares every value. A fixture
   receipt says in its own caveats that it proves the chain and not the
   Earth, and a report of a fixture run says the same.
3. **The real run on the committed data root:**

   ```bash
   uv run $ASDC/references/computations/energy_budget.py \
     --data-root $ASDC/references/retrieval/energy-budget-root \
     --window 2006-01:2020-12 \
     --runtime claude-code --receipt /tmp/energy-budget-record.json
   ```

   The root carries `RECORD.json` (the stamp, the manifest, the
   bookkeeping table and the Argo receipt's identity), `toa-net.csv`,
   `toa-net-stamp.json`, `ohc-2000-receipt.json` and `SOURCES.json`;
   `--ohc-receipt PATH` names the Argo receipt where it is not the
   default `DIR/ohc-2000-receipt.json`. The executor checks every file
   against its manifest hash before it reads a number, and refuses a
   stamp missing any required statement. One real-data window exists
   today, 2006-01 through 2020-12, because that is the window of the
   Argo receipt the root carries.
4. **The refusal rule.** A refusal is never a number: the run writes a
   refusal receipt with `refused: true`, a reason code and the reason
   in words, and exits 3.

   ```bash
   uv run $ASDC/references/computations/energy_budget.py \
     --fixture --window 1998-01:2005-12 \
     --runtime claude-code --receipt /tmp/refusal.json
   echo $?   # 3, and the receipt carries window-outside-record
   ```

   The codes are `window-outside-record`, `ohc-window-mismatch` (the
   Argo receipt is over another window), `ohc-receipt-refused` (the
   Argo receipt is itself a refusal), `too-few-months` (fewer than 24
   months of the window carry a value) and `interval-not-stated`.
   Report the refusal and its reason in the executor's own words. A
   refusal attests PASS only as a refusal, and the attester's verdict
   line then reads `PASS refusal`.
5. **Attest before quoting anything.** Every number quoted from a
   receipt comes after the attester has said PASS on that exact
   receipt:

   ```bash
   uv run $ASDC/references/attesters/energy_budget_check.py \
     /tmp/energy-budget-receipt.json [--data-root DIR] [--out /tmp/attestation.json]
   ```

   A data-root receipt is attested with `--data-root DIR` naming the
   tree: without it the data digests are taken on the executor's word
   and are not verified, and a data-root refusal is not reproduced at
   all and FAILS. The checks are `fields`, `code`, `release`,
   `runtime`, `data`, `ohc-window`, `series`, `recompute`,
   `bookkeeping` and `plausible`; `--out` writes the attestation for a
   qualification record, and `--selftest` runs the tampers, the wrong
   release, the refusals and the forged cases. Report the attester's
   verdict, not your own reading of the numbers.
6. **Report**, with each of these beside the number it qualifies: the
   four terms with their uncertainties and the stamp each came from;
   the residual against the combined uncertainty and the verdict as the
   receipt states them; the months used and the months missing; the run
   identifier and the runtime name the receipt carries; and the
   attester's verdict. Then the caveats the concept states, in the
   report and not in a footnote:

   - **The anchor.** The EBAF global mean net flux was set once to an
     in situ heat uptake over July 2005 through June 2015, so over the
     months the window shares with that decade the `toa_net` term is
     not independent of ocean heating. The receipt counts those shared
     months; quote that count. The absolute closure is not a test of
     one instrument against another.
   - **What the bar is made of.** The combined uncertainty over a
     single fixed window is mostly the natural variability both sides
     share, so `closed_within_uncertainty` reads as "the residual is
     within sampling noise" more than as "the two instruments agree".
   - **The anomaly trend** is the statement the anchor does not reach,
     because the adjustment is one-time and cancels in an anomaly. Its
     comparison with the published trend partly reproduces the same
     radiation record, so it is a consistency check and not an
     independent test, and it is a bookkeeping term and not the
     verdict.
   - **The ocean side's domain**, as the section above states it.

## Must NOT

- Never quote a number from a receipt the attester has not passed, and
  never edit the sanctioned executor or attester.
- Never present a refusal as a number, and never widen or relabel a
  window to get past one.
- Never recompute, rescale or substitute the ocean heat content term.
  It is another capability's attested receipt over exactly this window,
  and a budget missing that receipt is not a budget with a term to
  estimate.
- Never present the absolute closure as an independent confirmation of
  ocean heating over months the window shares with the anchor decade,
  and never drop the shared-month count from a report.
- Never form the anomaly against the product's own climatology; the
  computation forms it against the window's own mean, and the base
  period of that climatology is the anchor decade.
- Never state a number this release owns. Every figure in a report
  comes from the receipt or from the concept, cited by bundle path.
- Never commit a receipt, an attestation or a generated fixture to this
  repository.
