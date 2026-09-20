# Bundle change log

Newest first. One line per change: date, concept path, what changed, who.

- 2026-09-20 · STEWARD RE-SIGNING of
  knowledge/computations/energy-budget.md,
  knowledge/computations/cloud-radiative-effect.md: Re-signed after the
  computation moved into the capability that runs it. The coordinator
  compared every number in each concept against the bundle's copy and
  found them identical, 254 and 138 numbers with none added and none
  removed, and osp.py validate reports no warning. The new verified
  event is appended on the steward's word, the earlier events kept as
  history. (steward)

- 2026-09-20 · knowledge/computations/energy-budget.md and knowledge/computations/cloud-radiative-effect.md · the two attested computations of the asdc bundle came into this capability under ADR E, a computation is a skill, from nasa-daac-knowledge: the concepts from knowledge/asdc/computations/, their executors, attesters and loaders from knowledge/asdc/references/{computations,attesters,loaders} into the scripts of the skill that runs each, and their stamped data roots from knowledge/asdc/references/retrieval/{energy-budget-root,cloud-radiative-effect-root} into knowledge/references/retrieval/ as data. Nothing about any number changed: all six reference runs reproduced term by term at the new paths, and the two concepts are left at `status: draft` with their signature blocks untouched, because a move changes digests a signature covers. The bundle keeps its copies until its own seed deletes them. Digests, old to new: energy-budget.md 3e18998 to 3b085f9, cloud-radiative-effect.md 9daef15 to f62c236 · claude
  - energy-budget.md now names computation and executor.resource skills/energy-budget-closure/scripts/energy_budget.py (1f9a687 to 973c55f, the COMPUTATION constant and the contract line), attester.resource skills/energy-budget-closure/scripts/energy_budget_check.py (31c8c74 to 5e758ca, the executor it resolves and the attester path it records), and the data root knowledge/references/retrieval/energy-budget-root, whose five files are byte identical. Its loaders are eb_ceres_ebaf.py (10a6133 to 09dd1b2, the loader label it stamps) and eb_data_root.py (f253e31, unchanged).
  - cloud-radiative-effect.md now names computation and executor.resource skills/cloud-radiative-effect/scripts/cloud_radiative_effect.py (269c799 to e3a48d8), attester.resource skills/cloud-radiative-effect/scripts/cloud_radiative_effect_check.py (0b438bf to c17f63a), and the data root knowledge/references/retrieval/cloud-radiative-effect-root, whose four files are byte identical. Its loaders are cre_ceres_fluxes.py (f2ecc61 to 851db42) and cre_data_root.py (4cc8b01, unchanged).
  - The executor.skill key is retired with the wrap it named; the chains of the bundle's run_checks.sh and the four entries of its reference_runs.yaml are now the goldens verification/energy_budget_chain.py and verification/cloud_radiative_effect_chain.py and the registry verification/reference_runs.yaml.
- 2026-09-20 · knowledge/index.md · three receipt skills added to the capability, `sweep`, `receipt-figures` and `methods`, over the two asdc computations it wraps; no concept changed and no provider bundle changed, because a receipt skill emits only fields of receipts the bundle's attester passed (ADR D as amended, specification 0.6.22) · claude
- 2026-09-19 · knowledge/index.md · bundle opened with the capability's first release; it holds no concepts, because the release wraps computations signed in the asdc provider bundle and owns no claim of its own · claude
