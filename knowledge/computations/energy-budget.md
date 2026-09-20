---
type: Attested Computation
spheres: [atmosphere, hydrosphere]
title: "Energy budget closure: CERES EBAF net top-of-atmosphere flux against the Argo ocean heat content change (attested)"
description: "Sanctioned closure of the Earth's energy budget over a stated window: the EBAF global mean net TOA flux (the product's geodetic mean, on which its in situ anchor is defined) against the 0 to 2000 dbar ocean heat content rate read from the ocean-science Argo computation's receipt plus the published deep ocean and non-ocean terms, four rate terms in watts per square metre of the Earth's surface with the stamp each came from, the residual with the uncertainty of both sides, a verdict closed_within_uncertainty, the same terms as energy over the window, and beside them the EBAF net flux anomaly against the window's own mean with its trend, in which the anchor cancels, compared with the published satellite and in situ trend. Refuses (exit 3, never a number) a window the radiation record does not cover or an Argo receipt over another window. Proven on a synthetic fixture with a planted level, trend and closure, and anchored on a real-data run over 2006 through 2020 that closes within uncertainty."
tags: [ceres, ebaf, energy-imbalance, net-toa-flux, ocean-heat-content, argo, earth-heat-inventory, anchoring, attested]
runtime: python
parameters:
  - { name: window, type: string, required: true }
computation: skills/energy-budget-closure/scripts/energy_budget.py
executor:
  resource: skills/energy-budget-closure/scripts/energy_budget.py
  receipt: [run_id, computation, code_sha256, capability, bundle, runtime, generated_utc, data, bound_parameters, refused, months, series, terms, toa_net_W_m2, ocean_side_W_m2, residual_W_m2, toa_net_anomaly_trend_W_m2_per_decade, residual, combined_uncertainty, verdict, energy_over_window_ZJ, published_eei, bookkeeping, known_truth, caveats]
attester:
  resource: skills/energy-budget-closure/scripts/energy_budget_check.py
generated: { by: knowledge-seeder/claude, at: 2026-09-15T18:30:00Z }
verified:
  - { by: human:PaulMRamirez, at: 2026-09-15T18:57:33Z, role: maintainer, source: https://github.com/open-science-pillars/nasa-daac-knowledge/pull/174 }
  - { by: human:PaulMRamirez, at: 2026-09-16T05:50:55Z, role: maintainer, source: https://github.com/open-science-pillars/nasa-daac-knowledge/pull/183 }
  - { by: human:PaulMRamirez, at: 2026-09-19T08:13:02Z, role: maintainer, source: https://github.com/open-science-pillars/nasa-daac-knowledge/pull/199 }
  - { by: human:PaulMRamirez, at: 2026-09-20T19:04:18Z, role: maintainer, source: https://github.com/open-science-pillars/atmospheric-physics/pull/9 }
status: stable
stale_after: 2027-03-15
sources:
  - id: dataset
    resource: knowledge/asdc/datasets/ceres-ebaf-ed4-2.md
    title: "This bundle's EBAF dataset concept: the editions, the geodetic global means, the absence of an uncertainty field, the random error of a global monthly anomaly after the satellite transitions"
  - id: gotcha-anchor
    resource: knowledge/asdc/gotchas/ebaf-imbalance-anchored-to-ocean-heating.md
    title: "This bundle's gotcha: the net TOA flux is set to an in situ heat uptake of 0.71 W m-2 over July 2005 through June 2015, so the absolute imbalance is not an independent check of ocean heating and the anomaly is what the ocean data did not set"
  - id: gotcha-baseline
    resource: knowledge/asdc/gotchas/ebaf-climatology-baseline.md
    title: "This bundle's gotcha: the product's climatology base period is the anchor decade; this computation forms its anomaly against the window's own mean and never against the product's climatology"
  - id: dqs
    resource: https://ceres.larc.nasa.gov/documents/DQ_summaries/Versioned/CERES_EBAF_Ed4.2_DQS_V7.pdf
    title: "CERES_EBAF_Ed4.2 and Ed4.2.1 Data Quality Summary, version 7, 2026-07-01, the pinned copy (sha256 f778ebd8...), read 2026-09-15: the anchoring paragraph (the SYN1deg net imbalance about 4.3 W m-2 against the expected ocean heating rate about 0.71, the objective constrainment) and the geodetic weighting statement (global means from zonal geodetic weights, the solar division factor 4.0034)"
  - id: geodetic-weights
    resource: https://ceres.larc.nasa.gov/documents/GZWdata/zone_weights_lou.txt
    title: "The CERES one degree zonal geodetic weights (180 zones; sha256 962c14e8...), linked from the general product information page's geodetic zone weights section (read 2026-09-15: an oblate spheroid with the equatorial radius 6378.137 km and the polar radius 6356.752 km); applied offline to the field read, they reproduce the product's own global mean to 2.4e-4 W m-2"
  - id: cmr-granules
    resource: https://cmr.earthdata.nasa.gov/search/granules.json?collection_concept_id=C3880496704-LARC_CLOUD&page_size=10
    title: "CMR granule listing of CERES_EBAF Edition4.2.1 (read 2026-09-15): three granules, through 2025-12, 2026-03 and 2026-05, each with its archive and OPeNDAP URLs; the newest was read"
  - id: opendap-subset
    resource: https://opendap.earthdata.nasa.gov/collections/C3880496704-LARC_CLOUD/granules/CERES_EBAF_Edition4.2.1_200003-202605.nc.nc4?toa_net_all_mon,gtoa_net_all_mon,lat,lon,time
    title: "The netCDF-4 subset of CERES_EBAF_Edition4.2.1_200003-202605.nc the loader read through the ASDC OPeNDAP endpoint on 2026-09-15 (36,788,997 bytes, sha256 9ed59178...; Edition 4.2.1, revised data release date March 14, 2025; 315 months 2000-03 through 2026-05): the variables toa_net_all_mon and gtoa_net_all_mon with their coordinates, hashed in the data root's stamp and SOURCES.json"
  - id: loeb-2021
    resource: https://doi.org/10.1029/2021GL093047
    title: "Loeb and others (2021), Satellite and Ocean Data Reveal Marked Increase in Earth's Heating Rate, Geophysical Research Letters 48, e2021GL093047: the 0.50 plus or minus 0.47 W m-2 per decade increase in the Earth's energy imbalance from mid-2005 to mid-2019 that satellite and in situ observations each yield (the record and abstract read on the Crossref registry 2026-09-15; the journal page and the publisher's PDF sit behind a bot check and were not read)"
  - id: vs-2023
    resource: https://doi.org/10.5194/essd-15-1675-2023
    title: "von Schuckmann and others (2023), Heat stored in the Earth system 1960 to 2020: where does the energy go?, Earth System Science Data 15, 1675 to 1709 (read in full on the journal's site 2026-09-15, PDF sha256 37fffa6b...; the Crossref record verified the same day): Table 1 (the 2006 to 2020 layer rates, 0 to 2000 m 0.62 plus or minus 0.2 W m-2 of the global surface), section 2 (the deep ocean below 2000 m, 0.97 plus or minus 0.48 ZJ per year, 0.06 plus or minus 0.03 W m-2, 1992 to 2020), Table 2 (the atmospheric heat content gain 2006 to 2020), section 6 and figure 9 (the inventory fractions since 2006 and the 0.76 plus or minus 0.2 W m-2 imbalance for 2006 to 2020)"
  - id: loeb-2018
    resource: https://doi.org/10.1175/JCLI-D-17-0208.1
    title: "Loeb and others (2018), CERES EBAF TOA Edition-4.0 Data Product, Journal of Climate 31, 895 to 918: the one-time adjustment that sets the July 2005 through June 2015 global mean net flux to the in situ 0.71 W m-2 (the record verified on the Crossref registry 2026-09-15; the journal page not read)"
  - id: johnson-2016
    resource: https://doi.org/10.1038/nclimate3043
    title: "Johnson, Lyman and Loeb (2016), Improving estimates of Earth's energy imbalance, Nature Climate Change 6, 639 to 640: the in situ heat uptake the anchor cites, 0.71 plus or minus 0.10 W m-2 (the record verified on the Crossref registry 2026-09-15; the value from the summaries and the gotcha that cite it)"
  - id: purkey-johnson-2010
    resource: https://doi.org/10.1175/2010JCLI3682.1
    title: "Purkey and Johnson (2010), Warming of global abyssal and deep Southern Ocean waters between the 1990s and 2000s, Journal of Climate 23, 6336 to 6351: the deep-ocean warming the published rate below 2000 m descends from (the record verified on the Crossref registry 2026-09-15)"
  - id: ohc-receipt
    resource: knowledge/references/retrieval/energy-budget-root/ohc-2000-receipt.json
    title: "The Argo ocean heat content receipt committed in this package's data root (run sha256:0f64c6f9f2f330b6, 0 to 2000 dbar, 2006-01 through 2020-12), produced on 2026-09-15 by the ocean-science plugin's computation references/computations/argo_ohc.py (its concept knowledge/computations/argo-ohc.md, stable) on that plugin's committed data root argo-ohc-root-2026-09-15, and attested PASS there against the tree the same day; the ocean side of this budget is read from its terms"
  - id: data-root
    resource: knowledge/references/retrieval/energy-budget-root/RECORD.json
    title: "The stamped data root committed beside this concept: the loader's stamp, the Argo receipt's identity, the bookkeeping table, the manifest of the four files, and SOURCES.json for the downloads and the documents read"
  - id: ecco-ohc-recipe
    resource: knowledge/podaac/recipes/ecco-ocean-heat-content.md
    title: "The provider bundle's ECCO ocean heat content recipe: the ocean surface area anchor of 3.5801e8 km2 on the ECCO grid, against which the Argo product's mapped domain is compared"
  - id: loaders
    resource: skills/energy-budget-closure/scripts/eb_data_root.py
    title: "The loader and the stamp assembler in the running skill's scripts (eb_ceres_ebaf.py, eb_data_root.py), each with a selftest"
---

# Energy budget closure from CERES EBAF and Argo (attested)

The sanctioned computation behind any receipted statement that the
Earth's radiation imbalance measured from the top of the atmosphere
and the heat found in the Earth system agree, or do not, over a
window: the EBAF global mean net TOA flux against the 0 to 2000 dbar
ocean heat content rate the ocean-science Argo computation states in
its receipt, plus the deep ocean and the non-ocean components as
published rates with their sources.[^dataset][^ohc-receipt][^vs-2023]
It exists in this capability so that the anchoring caveat the
provider bundle's high-severity gotcha states is a set of receipt facts an attester
checks rather than a paragraph a reader trusts: the receipt counts the
months the window shares with the anchor decade, states the absolute
term as anchored, and carries beside it the anomaly comparison in
which the anchor cancels.[^gotcha-anchor] Version 1 is proven on a
synthetic fixture with a planted level, trend and closure, and its
real-data anchor is the stamped data root committed beside it, run
for 2006 through 2020 in the reference run below.[^data-root] A
fixture receipt says in its caveats that it proves the chain, not the
Earth.

**Status note (the move of 2026-09-20).** This concept, its executor,
its attester, its two loaders and its stamped data root moved from the
`asdc` bundle of nasa-daac-knowledge into this capability under ADR E,
a computation is a skill. Nothing about any number changed: both
reference runs below were re-run at the new paths on 2026-09-20 and
reproduced every value they state, term by term, and the run
identifiers changed only because a run identifier is bound to the
package the run is evidence for. The concept is left at `status:
draft` with its signature block untouched, because a move changes
digests the signature covers; the maintainer re-signs after merge.

## Parameters

- `window` (string, required): an inclusive month range
  `YYYY-MM:YYYY-MM` within the radiation record (the fixture spans
  2000-03 through 2026-05; a data root spans what its stamp holds,
  the same months for the committed root). The Argo receipt's window
  must be this window: its rate is a whole-window quantity, and a
  receipt over any other window is refused.

## The terms and the bookkeeping

Every term is a rate in watts per square metre of the Earth's surface
(4 pi R squared with the 6371 km mean radius, the Argo receipt's and
the published inventories' convention), with an uncertainty at the 95
percent level and the stamp it came from:[^vs-2023][^ohc-receipt]

- **toa_net**: the window mean of the product's own global mean net
  TOA flux, all-sky, positive downward, as the loader wrote it from
  gtoa_net_all_mon. The product forms that mean with zonal geodetic
  weights (an oblate spheroid, the solar division factor 4.0034), and
  the anchor of 0.71 W m-2 is defined on it, which is why the absolute
  term is taken from it and not from the cos-latitude mean of the one
  degree grid: the cos-latitude mean sits 0.22 W m-2 above the
  geodetic mean over the record (0.14 to 0.28 across the annual
  cycle), because the net flux has a strong meridional gradient, and
  the loader writes both columns and the offset between
  them.[^dqs][^geodetic-weights][^opendap-subset] The uncertainty is
  the anchor's in situ uncertainty, 0.10 W m-2, in quadrature with the
  larger of the sampling half width of the window mean (the residual
  about the calendar-month means under a lag-1 autocorrelated model,
  Student's t on the effective degrees of freedom) and the formal
  error the per-month floor propagates.[^gotcha-anchor][^johnson-2016]
- **ohc_0_2000**: the Argo receipt's trend term (ZJ per year with the
  uncertainty the receipt states, the larger of its sampling half
  width and its formal error) converted with the Earth's area; the
  receipt's own rate per unit Earth surface must agree to one part in
  a million or the executor stops. The rate is over the Roemmich and
  Gilson product's mapped open-ocean domain (64.5S to 65.5N, the
  columns mapped at every level) and is never scaled to the global
  ocean, so it understates the global ocean by
  construction.[^ohc-receipt]
- **deep_ocean**: the ocean below 2000 m, which the Argo receipt
  states as an omission with a published rate: 0.06 plus or minus
  0.03 W m-2 (0.97 plus or minus 0.48 ZJ per year) over 1992 to 2020
  as a constant linear trend from repeat hydrography, a term of its
  own here; the receipt's statement must agree with the sanctioned
  one, and the agreement is a receipt
  fact.[^vs-2023][^purkey-johnson-2010]
- **non_ocean**: land, cryosphere and atmosphere over 2006 to 2020
  from the Earth heat inventory: land 0.038 plus or minus 0.013 and
  cryosphere 0.030 plus or minus 0.011 W m-2 as about 5 and about 4
  percent of the 0.76 plus or minus 0.2 W m-2 imbalance the inventory
  states for that era (the uncertainty is the percentage point each
  fraction is rounded to and the fraction of the total's uncertainty,
  in quadrature), and atmosphere 0.0142 plus or minus 0.0040 W m-2
  from the global atmospheric heat content gain of 7.25 plus or minus
  1.72 TW over the Earth's area (the paper's range is a 90 percent
  one and is scaled to 95 percent by 1.960 over 1.645, to 2.05 TW, so
  that every term in the quadrature is at one level); 0.0822 plus or
  minus 0.0175 W m-2 together.[^vs-2023]

The residual is toa_net minus the sum of the three ocean-side terms;
the combined uncertainty is the four in quadrature (the anchor's
uncertainty inside the toa_net term); the verdict
`closed_within_uncertainty` is true when the residual lies within it.
What the bar is made of matters for reading the verdict: the toa_net
uncertainty adds the sampling half width of the window mean (0.138
W m-2 in the reference run, the AR(1) residual about the monthly
climatology) to the anchor's 0.10, and the Argo trend's uncertainty is
likewise a sampling half width, so for a closure over one fixed window
the combined bar (0.189 in the reference run) is mostly the natural
variability both sides share, and `closed_within_uncertainty` reads as
"the residual is within sampling noise" more than as "the two
instruments agree". The same four terms are stated as energy over the window (the rate
times the window length times the Earth's area, in zettajoules), and
the Argo receipt's own fitted and endpoint changes are copied beside
them with their shorter span, for the reader and not compared.

The bookkeeping table travels as the receipt's `bookkeeping` block,
and the attester refuses a receipt missing any of it: the anchoring
(the anchor value, its decade, the months the window shares with it,
and the statement that over those months the toa_net term is the in
situ estimate the product was set to), the weighting (the offset
between the cos-latitude and the geodetic mean over the window), the
edition (the product version, the release date, the DOI and the file
read), the uncertainty basis, the ocean input (the receipt's identity,
its domain and its area), the deep and non-ocean statements, the
published imbalance, the area convention and the window handling (a
month with no radiation value is a hole dropped from the mean and the
fit and never interpolated; whether the window is whole
years).[^gotcha-anchor][^data-root]

## The anomaly comparison, in which the anchor cancels

The adjustment that anchors EBAF is made once to the entire record, so
its interannual anomalies and its trend come from the radiometry, and
a comparison of their change with a change in the heat inventory is
the test the product supports without the anchor.[^gotcha-anchor] The receipt
carries the cos-latitude global mean minus its own mean over the
months used (never the product's climatology, whose base period is
the anchor decade),[^gotcha-baseline] and the linear trend of that
anomaly over the window in W m-2 per decade: least squares on the
calendar epochs with the annual cycle removed as calendar-month group
means, the lag-1 autocorrelation over adjacent epochs, the effective
sample size capped at the sample, Student's t on the effective degrees
of freedom, and beside it the formal error the per-month floor
propagates; the term's uncertainty is the larger of the two. The
receipt states the distance of that trend from the published one, the
0.50 plus or minus 0.47 W m-2 per decade increase in the Earth's
energy imbalance from mid-2005 to mid-2019 that satellite and in situ
observations each yield.[^loeb-2021] That published trend is the
CERES record's own trend over mid-2005 to mid-2019 as much as the in
situ one, so the comparison partly reproduces the same record and is
a consistency check, not an independent test; the Argo receipt
carries no acceleration term, so the ocean side is the published in
situ trend and not the receipt, and the comparison is a bookkeeping
term and not the verdict. The independent test, the CERES anomaly
trend against the in situ trend of the heating rate over the same
window, is computable from the Argo receipt's 180-month series
(`series.value_ZJ`) and is a follow-up, not this version.

## The fixture and its known truth

`--fixture --seed N` generates the record deterministically from a
hash-based Gaussian stream (no numeric library in the path, so the
digest cannot drift with a release): a monthly cos-latitude net flux
2000-03 through 2026-05 at a planted level of 0.95 W m-2 in July 2010
rising 0.50 W m-2 per decade, an annual cycle of 8.5 W m-2 peaking in
January, an interannual AR(1) component (0.8, 0.35 W m-2) and noise
at the stated 0.25 W m-2, a planted geodetic column offset by minus
0.218 W m-2 with a seasonal part, and a planted Argo-shaped receipt
whose rate is the noise-free geodetic window mean minus the deep and
non-ocean terms, so the budget closes by construction up to the noise
of the window mean. The receipt carries the seed, the fixture digest,
the generator's digest (the executor itself), the planted truth, and
a `known_truth` block with the planted window mean, trend and ocean
rate beside what was recovered; the attester regenerates the fixture
and compares every value.

## The refusal rule

A run writes a refusal receipt (`refused: true`, a `reason_code` and
the reason in words) and exits 3, never a number, when the window
lies outside the radiation record (`window-outside-record`); when the
Argo receipt's window is not the window asked for
(`ohc-window-mismatch`); when the Argo receipt is itself a refusal
(`ohc-receipt-refused`); when fewer than 24 months of the window carry
a value (`too-few-months`); or when the window mean's half width or
the anomaly trend's interval cannot be stated
(`interval-not-stated`). The attester attests a refusal PASS only as
a refusal, with the reason reproduced from the window and the
regenerated fixture or the tree it is given; its verdict line reads
`PASS refusal`.

## The attester criterion (deterministic, consumer-side)

A run PASSES only when all hold: every declared field present; the
code hash is the sanctioned file; the `bundle` block names this
package, version and release lock digest and the `capability` block is
well formed; a runtime is named; the fixture regenerated at the
receipt's seed hashes to the receipt's digest and so does the
generator (for a data root, the record, the files, the stamp and the
Argo receipt's identity are present, and with the tree given they
hash to the receipt's digests and the tree's Argo receipt carries the
run id, code digest and bound parameters copied into the receipt);
the Argo receipt's window and depth copied into the receipt are the
bound window and the 0 to 2000 dbar layer; the months used and missing partition
the window and the anomaly is the cos-latitude series minus its mean;
the window mean with its half width, the anomaly trend with its
interval and formal error, the four terms, the residual, the combined
uncertainty, the verdict, the energy over the window and the published
distances recompute from the receipt (1e-9 relative, with the
attester's own Student's t from the density); the bookkeeping is
complete, the anchor block is the sanctioned one and the shared months
are what the window gives; and stated plausibility bounds hold (the
toa_net term between minus 1 and 3 W m-2, the Argo rate between 0 and
2, the deep term between 0 and 0.2, the non-ocean term between 0 and
0.3, the anomaly trend within 3 W m-2 per decade of zero), with, on
the fixture, the recovered window mean within 0.3 W m-2 of the
planted one and the recovered trend within 1 W m-2 per decade of it.
The selftest covers a pass, eleven tampers each failing on its check
(a relabelled Argo window and a swapped Argo identity among them), a
wrong release, a tampered computation, two fixture refusals and a
forged one, a synthetic data root verified against its tree, a
fabricated tree, the window mismatch, refused-receipt and
interval-not-stated refusals reproduced only against the tree, and
the attestation document.

## The data root, for a real run

A computation is a skill (ADR E in the marketplace repository): this concept lives in the capability that runs it, and the skill that runs it is `energy-budget-closure` beside it, whose scripts hold the executor, the attester and the two loaders this concept names. The executor's usage text (`--help`) states the fixture run, the refusal rule and the receipt path, the attester's usage text states how a receipt is attested, and this section is the part that is contract and not procedure, the layout of the data root the executor reads.

The real run's tree is committed at
knowledge/references/retrieval/energy-budget-root, built by the loader
in the skill's scripts (eb_ceres_ebaf.py for the EBAF file, with
`--selftest` on a synthetic grid and `--fetch` for the download) and
stamped by eb_data_root.py, which writes RECORD.json with the
bookkeeping table from the loader's stamp and the Argo receipt;
SOURCES.json records the download, the documents read and the
receipt's provenance. This is the layout the computation reads.
`--data-root DIR` in place of `--fixture`, with `--ohc-receipt PATH`
naming the Argo receipt (default `DIR/ohc-2000-receipt.json`):

```
DIR/
  RECORD.json             the stamp: record name, the manifest of every file,
                          manifest_sha256, verified_utc, the loader's stamp,
                          the Argo receipt's identity, and the bookkeeping
                          table under "bookkeeping"
  toa-net.csv             month,value_W_m2,uncertainty_W_m2,product_global_W_m2
                          one row per calendar month: the cos-latitude mean,
                          the per-month floor, the product's geodetic mean
  toa-net-stamp.json      what the loader read, from where, when, the product
                          version, the grid, the weights, the mask, the
                          aggregation, the anchoring, the cross-check between
                          the two weightings, the sha256 of the file read
  ohc-2000-receipt.json   the Argo ocean heat content receipt for the window
  SOURCES.json            every file read with its URL, hash and time, and
                          the receipt's provenance
```

Months are `YYYY-MM`, unique and in order. `bookkeeping` must carry
`anchoring.statement`, `weighting.statement`, `edition.statement`,
`uncertainty.basis` and `ocean_input.statement`, each a statement in
words; the executor refuses a stamp that lacks any of them, and checks
every file in the manifest against its hash before it reads a number.
The receipt copies the stamp, the file digests and the Argo receipt's
identity (its computation, code digest, run id, window, bundle and
record).

Which tool produces each file:

- `toa-net.csv` and `toa-net-stamp.json`: the loader eb_ceres_ebaf.py, from the
  Edition 4.2.1 file; with `--fetch` it downloads a netCDF-4 subset of the
  granule through the ASDC OPeNDAP endpoint into the path `--product` names
  (outside the tree), first without credentials and then once with the
  Earthdata Login bearer token from `EARTHDATA_TOKEN` as a request header,
  which it never writes down. Its usage text states the arguments.
- `ohc-2000-receipt.json`: the ocean-science plugin's Argo computation
  (argo_ohc.py) on its committed data root, run in a clone of that plugin
  beside this repository over the budget's window, attested by its attester
  (argo_ohc_check.py) before it is placed in the tree; no network. It is
  committed here as evidence, and this package declares no install
  dependency on ocean-science for it.
- `RECORD.json`: the stamp assembler eb_data_root.py (`--root DIR --record
  NAME`, then `--root DIR --check`), after SOURCES.json is written.

The data root and the receipt path are recorded package-relative when
they sit under this repository, so the run id reproduces on any
machine.

## Reference run

**Fixture run (seed 7, 2006-01 through 2020-12, measured 2026-09-15
in the provider bundle and reproduced 2026-09-20 at this path, under
the runtime name knowledge-seeder, run sha256:4ac1081f7e979785; the id
is bound to the runtime name and to the package the run is evidence
for, so it is not the id the provider bundle recorded, while every
value below is).** 180 of 180 months. toa_net +1.0448
W m-2 with an uncertainty of 0.2632 (sampling 0.2434, the anchor
0.10), against the planted geodetic window mean of 0.8799 (the
difference is the interannual component's contribution to a fifteen
year mean, inside the sampling half width); ohc_0_2000 +0.7377 with
0.0746 (the planted 11.8746 ZJ per year with the planted 1.2);
deep_ocean 0.06 with 0.03; non_ocean 0.0822 with 0.0175. Residual
+0.1649 against a bar of 0.2757; `closed_within_uncertainty` true.
Anomaly trend +0.1527 W m-2 per decade, 95 percent interval
[-0.4216, +0.7269], the planted 0.50 inside it. The refusal case the
chain exercises is the window 1998-01 through 2005-12 on the fixture:
exit 3 with `window-outside-record`, attested as a refusal. The
registry entry `energy-budget` in verification/reference_runs.yaml
records the arguments, and the golden
verification/energy_budget_chain.py runs the chain.

**Real-data run (the stamped data root energy-budget-root-2026-09-15,
2006-01 through 2020-12, measured 2026-09-15 in the provider bundle and
reproduced 2026-09-20 at this path, under the runtime name
knowledge-seeder, run sha256:856e8381cc8bf595).** The radiation term was built by the loader
from the Edition 4.2.1 granule through 2026-05 read through the ASDC
OPeNDAP endpoint (the direct download host is unreachable from the
drafting environment, SOURCES.json says so), as 315 monthly global
means, every cell carrying a value; the ocean term is the Argo
receipt in the root.[^opendap-subset][^loaders][^data-root][^ohc-receipt]
180 of 180 months, 114 of them shared with the anchor decade.
toa_net +0.8746 W m-2 with an uncertainty of 0.1703 (sampling half
width 0.1378 at an effective sample of 87.6 months, the formal error
0.0801, the anchor 0.10); the cos-latitude window mean is 1.0921 and
the weighting offset 0.2176 (at most 0.2817 in a month). ohc_0_2000
+0.6005 with 0.0753 (the receipt's +9.6664 plus or minus 1.2118 ZJ per
year); deep_ocean 0.06 with 0.03; non_ocean 0.0822 with 0.0175; the
ocean side 0.7427 with 0.0829. Residual +0.1319 W m-2 against a bar
of 0.1894; `closed_within_uncertainty` true. The ocean term is over
the Argo product's mapped domain, 3.06e14 m2 against about 3.58e14 m2
of global ocean on the ECCO grid (the provider bundle's ECCO ocean
heat content recipe, knowledge/podaac/recipes/ecco-ocean-heat-content.md),
and if the unmapped 15 percent warmed at the domain's per-area rate
the term would be about 0.70 W m-2 and the residual about +0.03
instead of +0.13, so the residual is within what the domain
understatement alone could produce, and the verdict is not an
agreement between two complete quantities.[^ecco-ohc-recipe] As energy over the
fifteen years: toa_net 211.2 with 41.1 ZJ, the ocean side 179.3
(ocean 145.0 with 18.2, deep 14.5, non-ocean 19.9), residual 31.8
against a bar of 45.7; the Argo receipt's own fitted change is
+135.3 ZJ over its 14.0 year span. Anomaly trend +0.3706 W m-2 per
decade, 95 percent interval [+0.0762, +0.6649] (lag-1 autocorrelation
0.29, effective sample 98.0 of 180), 0.13 below the published 0.50
plus or minus 0.47, 0.28 of the published uncertainty.[^loeb-2021]

**The published anchor.** The Earth heat inventory states 0.76 plus
or minus 0.2 W m-2 for 2006 to 2020; the run's toa_net sits 0.11
above it and the run's ocean side 0.02 below it, both inside the
published uncertainty, the ocean side the closer because the
inventory's ocean is the same kind of estimate.[^vs-2023] The
toa_net term is not independent of the in situ estimate over the 114
shared months, which is the caveat the receipt states; the anomaly
trend carries no anchor, and its comparison with the published trend
is a consistency check, as the anomaly section says.[^gotcha-anchor] Observed on the file read and left for the
reviewer: the mean of the product's geodetic global net flux over the
anchor decade itself is 0.7387 W m-2, 0.03 above the 0.71 the
summaries name for the anchor.[^opendap-subset][^dqs]

**Pass bar.** There is no measured tolerance to record: the verdict
is a comparison of the residual against the uncertainty the receipt
itself carries, and the attester recomputes both. The plausibility
bounds are sanity bounds on the chain, not science tolerances.

## Boundaries

One real-data run exists, over 2006 through 2020, the window of the
Argo receipt the root carries; another window needs another Argo
receipt over exactly that window. The toa_net term carries the
product's anchor and its 0.10 W m-2 in situ uncertainty, and the
independent content of the absolute comparison is the radiometric
change between the anchor decade and the window; the anomaly trend is
the radiometric statement. The ocean term is over the Argo product's
mapped domain and understates the global ocean; the deep and
non-ocean terms are published rates over other periods (1992 to 2020,
2006 to 2020), not measurements over the window. The anomaly
comparison has no ocean-side acceleration from the receipt and is
made against the published in situ trend. The record was read through
the archive's OPeNDAP service as a subset; the loader also reads a
full product file from the ordering tool. Produced by Open Science
Pillars, not a NASA or CERES product.

**Verification.** The Edition 4.2 data quality summary and the
geodetic zone weights were read on 2026-09-15, and the weights applied
to the field read reproduce the product's own global mean to 2.4e-4
W m-2, which is the basis of the weighting statement
above;[^dqs][^geodetic-weights] the granule was read the same day
through the ASDC OPeNDAP endpoint after CMR listed it, and its hash is
in the data root's stamp;[^cmr-granules][^opendap-subset] the heat
inventory paper was read in full on the journal's site and every DOI
verified against the Crossref registry the same day (title, authors,
journal, year);[^vs-2023][^loeb-2018][^johnson-2016][^purkey-johnson-2010]
Loeb and others 2021 is cited on its registry record and abstract,
the journal page being behind a bot check;[^loeb-2021] the Argo
receipt was produced from the ocean-science plugin's committed data
root and attested there against the tree on 2026-09-15, and its
identity, hash and command are in SOURCES.json.[^ohc-receipt][^data-root]
The chain is verified on every change by the golden
verification/energy_budget_chain.py, which runs the attester's
selftest, the fixture run and its refusal, the loaders' selftests, the
data root's manifest check and the record run attested against the
tree.

[^dataset]: knowledge/asdc/datasets/ceres-ebaf-ed4-2.md, the product, its editions and the geodetic global means
[^gotcha-anchor]: knowledge/asdc/gotchas/ebaf-imbalance-anchored-to-ocean-heating.md, the anchor, its decade and what the ocean data did not set
[^gotcha-baseline]: knowledge/asdc/gotchas/ebaf-climatology-baseline.md, the product's climatology base period
[^dqs]: CERES_EBAF_Ed4.2 and Ed4.2.1 Data Quality Summary, version 7, 2026-07-01
[^geodetic-weights]: CERES zonal geodetic weights, zone_weights_lou.txt, and the general product information page
[^cmr-granules]: CMR granule listing of CERES_EBAF Edition4.2.1, read 2026-09-15
[^opendap-subset]: the netCDF-4 subset of CERES_EBAF_Edition4.2.1_200003-202605.nc read through the ASDC OPeNDAP endpoint
[^loeb-2021]: Loeb and others (2021), Geophysical Research Letters 48, doi:10.1029/2021GL093047
[^vs-2023]: von Schuckmann and others (2023), Earth System Science Data 15, doi:10.5194/essd-15-1675-2023
[^loeb-2018]: Loeb and others (2018), Journal of Climate 31, doi:10.1175/JCLI-D-17-0208.1
[^johnson-2016]: Johnson, Lyman and Loeb (2016), Nature Climate Change 6, doi:10.1038/nclimate3043
[^purkey-johnson-2010]: Purkey and Johnson (2010), Journal of Climate 23, doi:10.1175/2010JCLI3682.1
[^ohc-receipt]: knowledge/references/retrieval/energy-budget-root/ohc-2000-receipt.json, the Argo receipt the ocean side is read from
[^data-root]: knowledge/references/retrieval/energy-budget-root/RECORD.json, the stamped data root
[^loaders]: skills/energy-budget-closure/scripts, the radiation loader and the stamp assembler
[^ecco-ohc-recipe]: knowledge/podaac/recipes/ecco-ocean-heat-content.md, the ocean surface area on the ECCO grid
