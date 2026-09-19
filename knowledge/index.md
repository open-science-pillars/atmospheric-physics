---
okf_version: "0.2"
---

# atmospheric-physics bundle

This capability's own knowledge bundle. OKF v0.2 conformant
(okf_version "0.2" above).

## It holds no concepts

There is nothing to list below, and that is the release rather than an
omission. This is a wrap-only release (ADR D in the marketplace
repository's docs/decisions): the capability wraps attested
computations that are already signed stable in a provider bundle and
computes nothing of its own, so it owns no scientific claim and states
no convention a provider does not already state. Every concept its
skills consult lives in the provider bundle named below and arrives as
a declared dependency, never as a copy.

A concept belongs here when the capability itself owns the convention:
a rule about how this discipline's workflows are run that no provider
bundle states, decided and signed here. The first such concept is
listed here when it lands, and the knowledge-linter flags a concept
unreachable from this page.

## Provider bundles (declared dependencies)

**nasa-daac-knowledge, the `asdc` bundle** (the Atmospheric Science
Data Center's radiation budget and cloud products). Canonical home:
[nasa-daac-knowledge](https://github.com/open-science-pillars/nasa-daac-knowledge),
`knowledge/asdc/` in that repository. It is declared under
`dependencies.knowledge` in `.osp/package.yaml` with a version floor
(the plugin manifests are rendered from that file, never edited), so
it installs with this capability.

How it is consulted: the core skill `consult-knowledge` finds every
installed bundle through the installer's record; the skills here cite
provider concepts by bundle path,
`knowledge/asdc/<type>/<concept>.md`, and reach the sanctioned
executors and attesters under `knowledge/asdc/references/`. On a
conflict the provider concept wins, `stable` outranks `draft`, and a
draft is voiced as a draft. Nothing from that bundle is copied here.

What the skills of this release wrap:

- `knowledge/asdc/computations/energy-budget.md`, wrapped by the
  `energy-budget-closure` skill. Its ocean side is an attested receipt
  produced by the ocean-science capability's Argo computation and
  committed in this bundle's data root; it is read, never recomputed.
- `knowledge/asdc/computations/cloud-radiative-effect.md`, wrapped by
  the `cloud-radiative-effect` skill.

The concepts those two rest on, and which the skills cite rather than
restate, are the bundle's `datasets/ceres-ebaf-ed4-2.md`, its
`conventions/ceres-clear-sky-conventions.md`, its gotchas
`ebaf-imbalance-anchored-to-ocean-heating.md`,
`ebaf-clear-sky-definitions.md` and `ebaf-climatology-baseline.md`,
and its recipes `energy-budget.md` and `cloud-radiative-effect.md`.
