---
name: sweep
description: "Sweep one parameter an attested computation of this capability declares and table the receipts: the sanctioned executor once per value, the attester on every receipt before any field is read, and a CSV, a markdown table and a JSON manifest of the executor's own headline fields, with a refused run as a row carrying its refusal code. Keywords: parameter sweep, every region, both clear-sky conventions, total-region, cloud-free-area, convention contrast, window dependence, sensitivity, table of runs, cloud radiative effect by region, energy budget closure over many windows."
---

# sweep

This skill computes nothing. Every number it puts in a table is a field
of one receipt that the provider bundle's attester passed, copied by
the receipt field path the script records beside each column, and the
computation that owns those numbers is the concept the sweep names
(`knowledge/computations/cloud-radiative-effect.md` for the cloud
radiative effect, `knowledge/computations/energy-budget.md` for
the closure). The script fits nothing, averages nothing and carries no
expected value of its own. What the sweep adds is arrangement: a
concept states its boundaries in prose from a handful of runs someone
made by hand, and a sweep turns that sentence into a measured table by
running the sanctioned executor once per value of one parameter the
concept declares.

This is the port of the ocean-science skill of the same name. The
command line, the three outputs, the five refusal codes and the exit
codes are that skill's, so a reader who knows one sweep knows both.

Use it when the question is how an answer moves with a parameter the
concept declares: every region on one clear-sky convention, the same
region on both conventions, every window of a stated length stepping
through the record. Use the wrapping skill (`cloud-radiative-effect`,
`energy-budget-closure`) when the question is about one run, which is
also the only thing a reader may quote as a number.

The runs it drives are the wrapping skills' runs, so read the wrapping
skill first: it states the parameters, the refusal codes, the receipt
fields and the caveats that travel with every number. The sweep changes
none of that. It runs the same executor with the same flags, one value
at a time.

## Where the executors, the attesters and the concepts are

Both computations are carried by this package, and the script
resolves them at `${CLAUDE_PLUGIN_ROOT}`, exactly as the skills that
run them and the receipt-figures renderer do. `$ROOT` below stands for
`${CLAUDE_PLUGIN_ROOT}`:

- `--computation cloud-radiative-effect`: concept
  `$ROOT/knowledge/computations/cloud-radiative-effect.md`, executor
  `$ROOT/skills/cloud-radiative-effect/scripts/cloud_radiative_effect.py`,
  attester
  `$ROOT/skills/cloud-radiative-effect/scripts/cloud_radiative_effect_check.py`,
  data root
  `$ROOT/knowledge/references/retrieval/cloud-radiative-effect-root`.
- `--computation energy-budget`: concept
  `$ROOT/knowledge/computations/energy-budget.md`, executor
  `$ROOT/skills/energy-budget-closure/scripts/energy_budget.py`,
  attester
  `$ROOT/skills/energy-budget-closure/scripts/energy_budget_check.py`,
  data root `$ROOT/knowledge/references/retrieval/energy-budget-root`.

The declared parameter set is read from each concept's frontmatter, not
kept as a list in the script. A declared parameter whose name carries
an underscore is passed to the executor with a hyphen, so `clear_sky`
is bound as `--clear-sky`; the script derives the flag from the
declared name.

## The command line

Every run states the parameter swept, its values, and the fixed value
of every other parameter the concept declares. A declared parameter
that is neither swept nor fixed is a refusal, so the table always says
what every run was bound to.

```bash
uv run skills/sweep/scripts/sweep.py \
  --computation cloud-radiative-effect --parameter region \
  --values global,tropics,northern-extratropics,southern-extratropics,northern-midlatitudes,southern-midlatitudes,arctic,antarctic \
  --fixed window=2005-07:2015-06 --fixed clear_sky=total-region \
  --input data-root --data-root $ROOT/knowledge/references/retrieval/cloud-radiative-effect-root \
  --runtime claude-code --capability-root . \
  --out-dir /tmp/sweep-cre-regions
```

- `--parameter NAME` is swept; `--values A,B,C` states the values one
  by one, or `--windows LENGTH:STEP --span FIRST:LAST` states a window
  rule in months that expands to explicit values, which the manifest
  and every row then carry.
- `--fixed NAME=VALUE` states another declared parameter. Every
  parameter both computations declare is required, so
  `NAME=unbound` here makes the executor reject the run rather than
  produce a receipt; state a value.
- `--input fixture [--seed N]` rehearses on the executor's synthetic
  record; `--input data-root DIR` is a real run on a stamped tree. One
  input for the whole sweep: a table is one method on one root. The
  tree is given to the attester as well as to the executor, because
  without it the attesters take the data digests on the executor's
  word and do not reproduce a data-root refusal at all.
- `--runtime NAME` is passed to every run (from Claude Code, pass
  `--runtime claude-code`), and `--capability-root DIR` names the
  package the runs are evidence for.
- `--out-dir DIR` receives `sweep.csv` (every column as the receipt
  carries it), `sweep.md` (the same columns, floats shown to four
  decimals, with the provenance line above the table), `sweep.json`
  (the manifest: the command, the one executor digest, the one input
  identity, the column-to-receipt-field map, and every row with its
  receipt path, run id and the attester's own verdict line) and
  `receipts/` (every receipt and its attestation).
- `--selftest` runs the whole discipline on the executors' synthetic
  fixtures and exercises every refusal below.

## Behavior, in order

1. **Name the concept first, then show the sweep back.** State the
   concept by bundle path, the parameter to be swept as that concept
   declares it, the values, the fixed value of every other declared
   parameter, and the input (the fixture as a rehearsal, or the stamped
   data root for a real run). Consult the wrapping skill and the
   concepts it names before running. For any sweep that touches the
   clear-sky convention, consult
   `knowledge/asdc/conventions/ceres-clear-sky-conventions.md` and
   `knowledge/asdc/gotchas/ebaf-clear-sky-definitions.md` first and
   cite both by bundle path.
2. **Run the sweep.** One executor run per value, each writing its own
   receipt. A run the executor refuses (exit 3) is a row carrying its
   reason code, never a skipped row and never retried with a different
   binding to get a number out of it: the refusal is part of what the
   sweep measures. For the closure on the committed data root, one
   window computes, the window of the one Argo receipt the root
   carries, and every other window is a row carrying
   `ohc-window-mismatch`. For the cloud radiative effect, a region the
   fields cannot resolve is a row carrying `region-not-resolvable` and
   a convention the product does not carry a row carrying
   `clear-sky-convention-not-carried`.
3. **The attester runs on every receipt before any field is read.**
   The script attests each receipt and only then copies fields out of
   it. A receipt that does not pass is a failed row carrying the
   attester's own line and no number, and the script exits nonzero so
   the failure cannot pass for a table. Do not work around it; report
   it.
4. **Read the table.** The columns are the receipt fields the concept's
   reference run names. Both executors write a rounded headline field
   beside the full-precision term it rounds (`cre_net_W_m2` beside
   `terms.cre_net.value`, `toa_net_W_m2` beside `terms.toa_net.value`),
   and the table carries both as the receipt carries them; nothing here
   rounds or unrounds a number. The manifest maps every column to its
   receipt field path and every row to its receipt and run id. A
   fixture row leaves `argo_receipt_run_id` empty because the fixture
   plants an Argo-shaped block and not a receipt.
5. **Report the table with its provenance and the concept's caveats.**
   Hand over the markdown table together with the provenance line the
   script writes above it (the executor digest, the attester, the
   concept, the input identity, the runtime), the run identifiers of
   the rows discussed, and the caveats the concept states, beside the
   numbers and not after them. Say how many rows the executor refused
   and why. A fixture sweep proves the chain, not the Earth, and says
   so.
6. **Answer the aggregate question with a row.** A reader who sees a
   table asks for one number across it. Give the row that answers the
   question as asked (the region the question names, the window the
   question names), quote it with its uncertainty and its run id, and
   say that the spread across the rows is what the table shows and not
   a quantity any receipt carries. The script refuses `--aggregate`
   with that reason, and the reason is the answer to give.

## Reading a sweep of the cloud radiative effect

- **A sweep across the two conventions is two definitions, not two
  measurements.** The eight regions on `total-region` and the same
  eight on `cloud-free-area` are the table the bundle's clear-sky
  gotcha describes in words. Report the two conventions' rows side by
  side, name the convention every term is of, and read the difference
  as the size of the incomparability and never as a conversion.
- **The sign of the convention difference reverses.** The concept
  records that globally the total-region net effect is the more
  negative of the two and over the Antarctic band it is the less
  negative. That is why no single global number moves a regional result
  from one convention to the other, and why the mean of the two
  conventions is a quantity of neither. The script refuses that mean by
  name.
- **Compare a row against its own bar.** Each row carries its own
  uncertainty and the decomposition tolerance the verdict is measured
  against. The residual column is a check on the product's own fields
  and not a physical closure, as the concept states.
- **A published distance is stated only where the run is of the
  published figure's region, convention and period.** Every other row
  leaves that column empty, and an empty cell there is a refusal to
  compare, not a missing number.

## Reading a sweep of the closure

- **One real-data window exists.** The data root carries one Argo
  receipt, over 2006-01 through 2020-12, and the ocean side is that
  receipt and not a parameter. Every other window on that root is a
  refused row. Another window needs another Argo receipt over exactly
  that window, produced and attested in ocean-science first.
- **The anchor travels with every absolute row.** The
  `months_shared_with_anchor_decade` column is the count the concept's
  gotcha asks for; quote it beside any absolute closure. The anomaly
  trend column is the statement the anchor does not reach.
- **On the fixture, sweep windows of the reference run's length.** The
  attester checks the recovery of the planted level and trend over a
  window of that length, and a much shorter fixture window fails that
  check; a failed row is a finding about the window, not a licence to
  loosen anything.

## Must NOT

- Never state the headline number a reader will ask for first: one
  global cloud radiative effect across the two conventions, the mean
  net effect over the regions, the mean residual over the windows, or
  the fraction of windows that closed read as a rate. No receipt
  carries any of them and no concept owns them; a capability that
  computes one is computing a number of its own, which is domain
  expansion under ADR D of the marketplace decisions and waits on the
  ablation. The script refuses them; do not do by hand what it refuses.
- Never average, interpolate or otherwise combine the two clear-sky
  conventions, and never present a number without naming the
  convention it is of.
- Never compare or table rows whose receipts carry different executor
  digests or different input identities. The script refuses that too:
  a table is one method on one root.
- Never quote a number from a receipt the attester did not pass, and
  never drop a failed row to make the table look complete.
- Never drop a refused row, and never rerun it with an invented
  binding (a relabelled window, an approximated region) to fill the
  cell.
- Never sweep something the concept does not declare (a seed, an output
  path, a knob invented for the occasion); the script reads the
  declared set from the concept and refuses the rest.
- Never present a table without the run identifiers, the executor
  digest and the concept's caveats, and never commit a receipt, an
  attestation or a generated table to the bundle or to this repository.
