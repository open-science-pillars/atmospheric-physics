# Atmospheric Physics

This capability carries two attested computations over the CERES EBAF
radiation budget products: the energy budget closure and the cloud
radiative effect at the top of the atmosphere. A computation is a
skill, so each concept lives in `knowledge/computations/`, its
sanctioned executor and attester are scripts of the skill that runs it,
a golden under `verification/` proves each of those scripts, and the
stamped data root the executor reads is committed under
`knowledge/references/retrieval/` as data. A skill here names its
concept, runs the executor, runs the attester on the receipt before a
number is quoted, and reports the verdict, the run identifier, the
runtime and the caveats the concept states. The facts about the
products themselves stay with the archive that owns them, in the ASDC
bundle of
[nasa-daac-knowledge](https://github.com/open-science-pillars/nasa-daac-knowledge),
and are cited by bundle path rather than restated.

A domain capability: discipline Atmospheric Physics inside the
Atmosphere sphere. Pillar means sphere, one of the five Earth science
spheres; a capability is skills, knowledge signed by its stewards and
deterministic checks, delivered as one plugin. The words used on this
page are defined in the
[glossary](https://github.com/open-science-pillars/marketplace/blob/main/GLOSSARY.md),
and the decision this release is made under is ADR E in
[marketplace/docs/decisions](https://github.com/open-science-pillars/marketplace/tree/main/docs/decisions).

## Install

On Claude Code:

```bash
claude plugin marketplace add open-science-pillars/marketplace
claude plugin install atmospheric-physics@open-science-pillars
```

What comes with it: `core`, the foundation capability, and
`nasa-daac-knowledge`, the provider bundle whose ASDC concepts the
computations here cite for facts about the products. Both are declared
dependencies, so the installer brings them; no concept of either is
copied here, and nothing this capability runs comes from either.

On Claude Cowork: add the marketplace by repository
(`open-science-pillars/marketplace`) under Customize > Plugins > Add
marketplace, then install the same capability from it; the shell
commands on this page are for Claude Code.

Local requirements: [uv](https://docs.astral.sh/uv/getting-started/installation/).
Every script a skill here invokes declares its dependencies in a PEP 723
header and runs as `uv run <script>`; uv builds the environment on first
run. Never `python script.py`, which skips the header. No account and no
credential are needed to run either chain on its fixture, and no
download is needed to run either on the data root this package
commits.

## Runtimes

Which runtimes this release is qualified on is the table below, rendered
from the qualification records; what each word asserts is in the
marketplace repository's
[docs/runtime-distribution.md](https://github.com/open-science-pillars/marketplace/blob/main/docs/runtime-distribution.md).
This is a first release and carries no qualification record yet, so no
surface says supported.

<!-- osp-runtimes:start -->
Runtime support for atmospheric-physics 0.2.0 (release lock `sha256:e045e1f3d270`), rendered by build-kit's `osp.py advertise` from `.osp/surfaces.yaml` and the qualification records; edit those, not this block.

| Runtime | Role | Declared status | Qualification |
|---|---|---|---|
| Claude Code | development and runtime, required | tested | Not qualified, waived for this release (Claude Code is not qualified for this release because the release environment could not produce a record that would be evidence. In this same round two runs of another capability's candidate disagreed with each other, once through a concurrent run sharing the plugin cache and once through the shell tool being denied part way through, so a record made here would say more about the environment than about the package. No run was made for this release rather than one made and presented as more than it is. What the gate does establish is unchanged: the goldens pass on this commit, the release lock is current, and the package's own verification exercises every script at its new path. The surface is not advertised until a run passes on a machine that can run it.; human:PaulMRamirez, 2026-09-20) |
| Claude Cowork | runtime, required | planned | Not qualified, waived for this release (Claude Cowork is not qualified for this release. A Cowork record is a run by a person with Cowork in front of them, installing from the catalog, and no such run has been made for 0.2.0; the runtime cannot be driven headlessly, so the coordinator carrying this release on the maintainer's behalf cannot make one either. This repeats the decision recorded for land-ice 0.1.0 on 2026-09-19 for the same reason. Nothing about the capability is known to fail there: its projection renders and validates in the gate. The surface is not advertised until a run exists.; human:PaulMRamirez, 2026-09-20) |
| OpenAI Codex | runtime, required | planned | Not qualified, waived for this release (OpenAI Codex is not qualified for this release. No release in this organization has been qualified on Codex: the Agent Plugins projection renders and passes plugin-check in the gate, but the Codex leg has never been exercised, so there is no procedure to run and nothing to record. This repeats the decision recorded for land-ice 0.1.0 on 2026-09-19 for the same reason. The surface is not advertised, and the projection is published as conformant rather than as tested.; human:PaulMRamirez, 2026-09-20) |
| Claude Science | future runtime | limited-release | Outside the required matrix |

A runtime is advertised as supported only on a qualified record for this exact release; a release stays valid when a runtime is not qualified, and that runtime is simply not advertised.
<!-- osp-runtimes:end -->

## What's inside

- **Computation skills** (`skills/`, one `SKILL.md` each), one per
  computation and named for the workflow rather than for the product.
  Each carries its executor, its attester and the loaders that built
  its data root in its own `scripts/` directory:

  - `energy-budget-closure` runs
    `knowledge/computations/energy-budget.md`: the CERES EBAF net
    top-of-atmosphere flux over a window against the 0 to 2000 dbar
    ocean heat content rate, with the published deep ocean and
    non-ocean terms, the residual against the combined uncertainty, and
    the anomaly trend in which the product's anchor cancels. The ocean
    side is an attested receipt produced by the ocean-science
    capability's Argo computation and committed in this package's data
    root as evidence; this skill reads it and never recomputes it, and
    no install dependency on ocean-science is declared for it.
  - `cloud-radiative-effect` runs
    `knowledge/computations/cloud-radiative-effect.md`: the
    shortwave, longwave and net effect of clouds at the top of the
    atmosphere over a window and a region, formed against a clear-sky
    convention the user chooses deliberately, with the same three terms
    under the other convention reported beside them.

- **Skills that compute nothing** (`skills/`), the postdoc's three.
  Each of them computes nothing of its own: every number it emits is a
  field of a receipt an attester passed, or a table, figure or
  paragraph of such fields, and it combines no two receipts into a
  value no receipt carries. Each script enforces that rather than its
  prose:

  - `sweep` runs an executor once per value of one parameter the
    concept declares and writes a CSV, a markdown table and a JSON
    manifest of the executor's own headline fields per receipt, a
    refused run included as a row carrying its reason code. It refuses
    any aggregate across the rows, an average across the two clear-sky
    conventions above all.
  - `receipt-figures` draws the series and the convention contrast a
    receipt carries, after the attester has passed it and every drawn
    array has been checked, with the run identifier, the code digest
    and the verdict in the caption. It has no map mode, because these
    receipts carry no per-cell field.
  - `methods` writes the methods paragraph and the reference list from
    the receipt's bookkeeping block and the concept's sources, and
    names the receipt field behind every sentence. A fact from anywhere
    else is refused.

- **Knowledge** (`knowledge/`): this capability's own bundle, holding
  the two Attested Computation concepts under `computations/` and the
  two stamped data roots under `references/retrieval/` as data. Nothing
  under `knowledge/` is runnable, which `osp.py validate` checks. The
  dataset, convention, gotcha and recipe concepts about the CERES
  products stay in the provider bundle and are cited by bundle path;
  `knowledge/index.md` says which.

- **Verification** (`verification/`): `energy_budget_chain.py` and
  `cloud_radiative_effect_chain.py`, the two chain goldens (the
  attester's selftest, both loaders' selftests, the executor on its
  fixture, the attester on the receipt, the receipt against what the
  concept records, the chain's refusal case, the data root's manifest
  check and the anchored real-data run attested against the tree, with
  the eight regions on both clear-sky conventions for the cloud
  radiative effect); `wrapped_computations.py`, which runs both fixture
  chains and is the release qualification surface; and
  `receipt_skills.py`, which runs those three the same way (each
  script's selftest, three fixture sweeps checked cell by cell,
  three figures whose every drawn array is checked against the receipt
  field it comes from, two methods paragraphs checked against the
  receipt fields they were filled from, and every refusal each script
  enforces). All read committed expectations under `fixtures/`, and
  `reference_runs.yaml` beside them is the registry `osp.py reattest`
  re-runs a reference run from.

## What this release does not do

It carries no connector, no agent and no computation beyond the two
above. Those three are not an exception: a sweep that averaged its
rows into a rate, a figure with a fitted trend on it or a paragraph
with a fact the receipt does not carry would each be a number no
receipt owns, and each script refuses to produce one. A new computation
in this sphere is domain expansion and waits on the decision that
governs it. A fact about a CERES product that the ASDC bundle has not
signed belongs in that bundle first, where it can be reviewed and
signed, and reaches a reader here only once it is.

## Ownership

Owned by @open-science-pillars/atmosphere-maintainers (`CODEOWNERS`);
one person holds the team during the interim solo period, and accepting
a maintainer is a membership change, never a rearrangement. Provider
contacts who could confirm the facts this capability relies on: ASDC
(CERES). A confirmation is invited on every concept the skills cite and
required on none; the product concepts live in the provider bundle,
and each carries its own confirm link.

## Contributing

Start with the marketplace repository's
[CONTRIBUTING.md](https://github.com/open-science-pillars/marketplace/blob/main/CONTRIBUTING.md)
and the guides under its `docs/` (contributing a skill, contributing
knowledge, testing, the package authoring guide). A change to what a
skill here reports is a change to the concept beside it and is reviewed
here; a change to a fact about a CERES product is a change in
nasa-daac-knowledge and is reviewed there.

## Place in the organization

What this repository is and how far along it is are declared once, in
`.osp/repository.yaml`; the organization profile, build-kit's
[sphere view](https://github.com/open-science-pillars/build-kit/blob/main/SPHERE-VIEW.md)
and the GitHub topics are rendered from that file, never the other way
round. The runtime manifests are rendered from `.osp/package.yaml` by
build-kit's `osp.py render` and are never edited by hand.

## License

Apache 2.0, the organization's license; see `LICENSE`.
