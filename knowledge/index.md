---
okf_version: "0.2"
---

# atmospheric-physics bundle

This capability's own knowledge bundle. OKF v0.2 conformant
(okf_version "0.2" above).

## Attested Computations

A computation is a skill (ADR E in the marketplace repository's
docs/decisions): the concept of an attested computation lives in the
capability that runs it, its executor and its attester are scripts of
the skill named beside it, a golden under `verification/` proves each
of those scripts, and the stamped data root the executor reads is
committed under `knowledge/references/retrieval/` as data.

- [`computations/energy-budget.md`](computations/energy-budget.md), the
  energy budget closure of the CERES EBAF net top-of-atmosphere flux
  against the Argo ocean heat content change. Run by the
  `energy-budget-closure` skill, whose scripts hold the executor
  `energy_budget.py`, the attester `energy_budget_check.py` and the two
  loaders that built the root. Its data root is
  `references/retrieval/energy-budget-root`, and the ocean side is an
  attested receipt the ocean-science capability's Argo computation
  produced, committed there as evidence and read, never recomputed; no
  install dependency on ocean-science is declared for it.
- [`computations/cloud-radiative-effect.md`](computations/cloud-radiative-effect.md),
  the cloud radiative effect at the top of the atmosphere, the all-sky
  flux minus the clear-sky flux of a clear-sky convention the user
  binds deliberately. Run by the `cloud-radiative-effect` skill, whose
  scripts hold the executor `cloud_radiative_effect.py`, the attester
  `cloud_radiative_effect_check.py` and the two loaders that built the
  root. Its data root is
  `references/retrieval/cloud-radiative-effect-root`.

Both arrived here on 2026-09-20 from the `asdc` bundle of
nasa-daac-knowledge, with their code, their roots and their reference
values re-homed and re-run rather than revised. Both are at `status:
draft` with their signature blocks untouched, because a move changes
digests a signature covers; the maintainer re-signs after merge.

## Evidence under `references/`

`references/retrieval/` holds the two stamped data roots: the record,
the manifest, the loader's stamp, the bookkeeping table, the flux and
radiation files and, for the energy budget, the Argo receipt. They are
data and evidence, never code: nothing under `knowledge/` is runnable,
which `osp.py validate` checks.

## What this bundle does not hold

A dataset, gotcha, convention or recipe concept about a NASA product
belongs to the provider bundle that owns the product, and the skills
here cite those by bundle path rather than restating them. On a
conflict the provider concept wins for a fact about a product, `stable`
outranks `draft`, and a draft is voiced as a draft. A method's
reference values are this capability's, and are owned by the two
concepts above.

## Provider bundles (declared dependencies)

**nasa-daac-knowledge, the `asdc` bundle** (the Atmospheric Science
Data Center's radiation budget and cloud products). Canonical home:
[nasa-daac-knowledge](https://github.com/open-science-pillars/nasa-daac-knowledge),
`knowledge/asdc/` in that repository. It is declared under
`dependencies.knowledge` in `.osp/package.yaml` with a version floor
(the plugin manifests are rendered from that file, never edited), so it
installs with this capability. The core skill `consult-knowledge` finds
every installed bundle through the installer's record.

The concepts the two computations rest on, and which they cite rather
than restate, are that bundle's `datasets/ceres-ebaf-ed4-2.md`, its
`conventions/ceres-clear-sky-conventions.md`, its gotchas
`ebaf-imbalance-anchored-to-ocean-heating.md`,
`ebaf-clear-sky-definitions.md` and `ebaf-climatology-baseline.md`, and
its recipes `energy-budget.md` and `cloud-radiative-effect.md`.

Three receipt skills, `sweep`, `receipt-figures` and `methods`, operate
over the two computations above and add no concept here. A receipt
skill emits only fields of receipts an attester passed, or a table,
figure or paragraph of such fields, and combines no two receipts into a
value no receipt carries; its script enforces that test rather than its
prose. A sweep that averaged its rows, a figure carrying a fitted line
or a paragraph stating a fact no receipt carries would each be a claim
this bundle would have to own, and each script refuses to produce one.
