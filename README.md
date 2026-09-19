# Atmospheric Physics

This capability wraps attested computations that are signed stable in a
provider knowledge bundle, and computes nothing of its own. Every number
it can report is owned by a concept in the ASDC bundle of
[nasa-daac-knowledge](https://github.com/open-science-pillars/nasa-daac-knowledge):
a skill here names that concept, runs its sanctioned executor at the
path the installed bundle puts it, runs the attester on the receipt
before a number is quoted, and reports the verdict, the run identifier,
the runtime and the caveats the concept states. Reachability is what
this release adds, not breadth; a capability that computed a number of
its own would be domain expansion and waits on the decision that
governs it.

A domain capability: discipline Atmospheric Physics inside the
Atmosphere sphere. Pillar means sphere, one of the five Earth science
spheres; a capability is skills, knowledge signed by its stewards and
deterministic checks, delivered as one plugin. The words used on this
page are defined in the
[glossary](https://github.com/open-science-pillars/marketplace/blob/main/GLOSSARY.md),
and the decision this release is made under is ADR D in
[marketplace/docs/decisions](https://github.com/open-science-pillars/marketplace/tree/main/docs/decisions).

## Install

On Claude Code:

```bash
claude plugin marketplace add open-science-pillars/marketplace
claude plugin install atmospheric-physics@open-science-pillars
```

What comes with it: `core`, the foundation capability, and
`nasa-daac-knowledge`, the provider bundle whose ASDC concepts the
skills here run. Both are declared dependencies, so the installer
brings them; nothing from either is copied into this repository.

On Claude Cowork: add the marketplace by repository
(`open-science-pillars/marketplace`) under Customize > Plugins > Add
marketplace, then install the same capability from it; the shell
commands on this page are for Claude Code.

Local requirements: [uv](https://docs.astral.sh/uv/getting-started/installation/).
Every script a skill here invokes declares its dependencies in a PEP 723
header and runs as `uv run <script>`; uv builds the environment on first
run. Never `python script.py`, which skips the header. No account and no
credential are needed to run either chain on its fixture, and no
download is needed to run either on the data root the provider bundle
commits.

## Runtimes

Which runtimes this release is qualified on is the table below, rendered
from the qualification records; what each word asserts is in the
marketplace repository's
[docs/runtime-distribution.md](https://github.com/open-science-pillars/marketplace/blob/main/docs/runtime-distribution.md).
This is a first release and carries no qualification record yet, so no
surface says supported.

<!-- osp-runtimes:start -->
Runtime support for atmospheric-physics 0.1.0, rendered by build-kit's `osp.py advertise` from `.osp/surfaces.yaml` and the qualification records; edit those, not this block.

| Runtime | Role | Declared status | Qualification |
|---|---|---|---|
| Claude Code | development and runtime, required | tested | Not qualified |
| Claude Cowork | runtime, required | planned | Not qualified |
| OpenAI Codex | runtime, required | planned | Not qualified |
| Claude Science | future runtime | limited-release | Outside the required matrix |

A runtime is advertised as supported only on a qualified record for this exact release; a release stays valid when a runtime is not qualified, and that runtime is simply not advertised.
<!-- osp-runtimes:end -->

## What's inside

- **Skills** (`skills/`, one `SKILL.md` each), one per wrapped
  computation and named for the workflow rather than for the product:

  - `energy-budget-closure` wraps
    `knowledge/asdc/computations/energy-budget.md`: the CERES EBAF net
    top-of-atmosphere flux over a window against the 0 to 2000 dbar
    ocean heat content rate, with the published deep ocean and
    non-ocean terms, the residual against the combined uncertainty, and
    the anomaly trend in which the product's anchor cancels. The ocean
    side is an attested receipt produced by the ocean-science
    capability's Argo computation and committed in the provider
    bundle's data root; this skill reads it and never recomputes it.
  - `cloud-radiative-effect` wraps
    `knowledge/asdc/computations/cloud-radiative-effect.md`: the
    shortwave, longwave and net effect of clouds at the top of the
    atmosphere over a window and a region, formed against a clear-sky
    convention the user chooses deliberately, with the same three terms
    under the other convention reported beside them.

- **Knowledge** (`knowledge/`): this capability's own bundle. It holds
  no concepts, and `knowledge/index.md` says so and says why: the
  scientific concepts the skills consult live in the provider bundle
  and arrive as the declared dependency. A concept lands here when the
  capability itself owns a convention that no provider bundle states.

- **Verification** (`verification/`): `wrapped_computations.py`, the
  golden that runs both chains headless and offline (the executor on
  its fixture, the attester on the receipt, the receipt against the
  values the signed concept records, then the chain's refusal case),
  and the committed expectations it reads under `fixtures/`.

## What this release does not do

It carries no skill that computes a number, no connector, no agent and
no computation of its own. An analysis that needs something the ASDC
bundle has not signed belongs in that bundle first, where the number
can be reviewed and signed, and reaches a reader here only once it is.

## Ownership

Owned by @open-science-pillars/atmosphere-maintainers (`CODEOWNERS`);
one person holds the team during the interim solo period, and accepting
a maintainer is a membership change, never a rearrangement. Provider
contacts who could confirm the facts this capability relies on: ASDC
(CERES). A confirmation is invited on every concept the skills cite and
required on none; the concepts live in the provider bundle, and each
carries its own confirm link.

## Contributing

Start with the marketplace repository's
[CONTRIBUTING.md](https://github.com/open-science-pillars/marketplace/blob/main/CONTRIBUTING.md)
and the guides under its `docs/` (contributing a skill, contributing
knowledge, testing, the package authoring guide). A change to what a
skill here reports is usually a change to the concept it wraps, in
nasa-daac-knowledge, and is reviewed there.

## Place in the organization

What this repository is and how far along it is are declared once, in
`.osp/repository.yaml`; the organization profile, build-kit's
[sphere view](https://github.com/open-science-pillars/build-kit/blob/main/SPHERE-VIEW.md)
and the GitHub topics are rendered from that file, never the other way
round. The runtime manifests are rendered from `.osp/package.yaml` by
build-kit's `osp.py render` and are never edited by hand.

## License

Apache 2.0, the organization's license; see `LICENSE`.
