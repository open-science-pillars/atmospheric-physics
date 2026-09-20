---
type: Attested Computation
spheres: [atmosphere]
title: "Cloud radiative effect at the top of the atmosphere: the CERES EBAF all-sky flux against the clear-sky flux of a declared convention (attested)"
description: "Sanctioned cloud radiative effect over a stated window and region: the shortwave, longwave and net effect of clouds on the top-of-atmosphere radiation budget, formed as the difference between the all-sky and the clear-sky fluxes of the energy balanced product, with the clear-sky convention bound as a declared parameter because the product carries two and a cloud radiative effect inherits the convention of the field it subtracts. Three rate terms in watts per square metre of the region with the stamp each came from, the residual of the decomposition of the net effect into its two parts, the combined uncertainty, a verdict decomposition_closes, the same three terms under the other convention beside them, and the distance from the published global mean where the run is of its region, convention and period. Refuses (exit 3, never a number) a clear-sky convention the product does not carry, a window the record does not cover and a region whose mask it cannot resolve. Proven on a synthetic fixture with a planted effect and a planted convention offset, and anchored on a real-data run over July 2005 through June 2015 that lands 0.011 W m-2 from the published net cloud radiative effect."
tags: [ceres, ebaf, cloud-radiative-effect, clear-sky, total-region, cloud-free-area, convention, radiation-budget, attested]
runtime: python
parameters:
  - { name: window, type: string, required: true }
  - { name: region, type: string, required: true }
  - { name: clear_sky, type: string, required: true }
computation: skills/cloud-radiative-effect/scripts/cloud_radiative_effect.py
executor:
  resource: skills/cloud-radiative-effect/scripts/cloud_radiative_effect.py
  receipt: [run_id, computation, code_sha256, capability, bundle, runtime, generated_utc, data, bound_parameters, refused, months, series, terms, cre_shortwave_W_m2, cre_longwave_W_m2, cre_net_W_m2, residual, combined_uncertainty, verdict, convention_contrast, published_comparison, bookkeeping, known_truth, caveats]
attester:
  resource: skills/cloud-radiative-effect/scripts/cloud_radiative_effect_check.py
generated: { by: knowledge-seeder/claude, at: 2026-09-19T07:10:00Z }
verified:
  - { by: human:PaulMRamirez, at: 2026-09-19T07:18:47Z, role: maintainer, source: https://github.com/open-science-pillars/nasa-daac-knowledge/pull/196 }
  - { by: human:PaulMRamirez, at: 2026-09-19T08:13:02Z, role: maintainer, source: https://github.com/open-science-pillars/nasa-daac-knowledge/pull/199 }
  - { by: human:PaulMRamirez, at: 2026-09-20T19:04:18Z, role: maintainer, source: https://github.com/open-science-pillars/atmospheric-physics/pull/9 }
status: stable
stale_after: 2027-03-19
sources:
  - id: convention
    resource: knowledge/asdc/conventions/ceres-clear-sky-conventions.md
    title: "This bundle's convention concept: the four quantities the CERES radiation products call clear-sky, which convention each field carries, and why a cloud radiative effect inherits the convention of the field it subtracts; the parameter of this computation is bound to the two conventions it names for the energy balanced product"
  - id: gotcha-clear-sky
    resource: knowledge/asdc/gotchas/ebaf-clear-sky-definitions.md
    title: "This bundle's gotcha: EBAF carries two clear-sky definitions, the cloud radiative effect changed definition at Edition 4.1, and the published size of the adjustment between them (a global mean longwave adjustment of minus 2.2 W m-2 at the top of the atmosphere and a shortwave one of 0.5); this concept cites that size and does not restate it"
  - id: dataset
    resource: knowledge/asdc/datasets/ceres-ebaf-ed4-2.md
    title: "This bundle's EBAF dataset concept: the editions, the geodetic global means, the absence of an uncertainty field, and the regional monthly all-sky and clear-sky flux uncertainties"
  - id: energy-budget
    resource: knowledge/computations/energy-budget.md
    title: "This capability's other attested computation on the same product, whose receipt discipline, refusal style and bookkeeping keys this one follows; its concept owns the product's anchoring to an in situ ocean heating estimate, which the cloud radiative effect does not inherit because the anchor cancels in a difference of two fluxes of the same month"
  - id: dqs
    resource: https://ceres.larc.nasa.gov/documents/DQ_summaries/CERES_EBAF_Ed4.2_DQS.pdf
    title: "CERES_EBAF_Ed4.2 and Ed4.2.1 Data Quality Summary, version 8, released 2026-09-10 (sha256 8b00f86c...), read 2026-09-19: the clear-sky gap problem and its filling, the total-region clear-sky flux added at Edition 4.1, the caution that the cloud radiative effects of Edition 4.2 are determined from it where Edition 4.0 used the cloud-free portions only, the cautions that cloud radiative effects are computed as all-sky flux minus clear-sky flux and that the net flux is downward minus upward, the unphysical cloud effect signs under the cloud-free-area definition, and the statement that global means are determined using zonal geodetic weights"
  - id: dqs-ed4-0
    resource: https://ceres.larc.nasa.gov/documents/DQ_summaries/CERES_EBAF_Ed4.0_DQS.pdf
    title: "CERES_EBAF_Ed4.0 Data Quality Summary, 2018-01-17 (sha256 4ee6affd...), read 2026-09-19: Table 6-1, the global mean TOA fluxes from EBAF Ed4.0 and Ed2.8 for July 2005 through June 2015, which is the published global mean cloud radiative effect this computation is anchored to (shortwave -45.8, longwave 28.0, net -17.9 W m-2 for Edition 4.0, whose clear-sky flux is the cloud-free-area one), with the all-sky and clear-sky fluxes beside them; and Table 6-3, the global mean cloud radiative effect trends for March 2000 through June 2015"
  - id: geodetic-weights
    resource: https://ceres.larc.nasa.gov/documents/GZWdata/zone_weights_lou.txt
    title: "The CERES one degree zonal geodetic weights (180 zones summing to 1.000013; sha256 962c14e8...), read 2026-09-19: the oblate spheroid with the equatorial radius 6378.137 km and the polar radius 6356.752314245 km and the solar division factor 4.0034; applied to the nine regional fields read, they reproduce the product's own global means to 4.5e-4 W m-2"
  - id: dmr
    resource: https://opendap.earthdata.nasa.gov/collections/C3880496704-LARC_CLOUD/granules/CERES_EBAF_Edition4.2.1_200003-202605.nc.dmr
    title: "The granule's OPeNDAP metadata response (sha256 4f0feea3...), read 2026-09-19: the variable names and long names that fix which convention each field carries, the _clr_t_ triple long-named Clear-Sky (for total region), the _clr_c_ triple long-named Clear-Sky (for cloud-free areas of region), and the product's own cloud radiative effect variables whose long names read uses Clear-Sky for total region"
  - id: opendap-subset
    resource: https://opendap.earthdata.nasa.gov/collections/C3880496704-LARC_CLOUD/granules/CERES_EBAF_Edition4.2.1_200003-202605.nc.nc4?toa_sw_all_mon,toa_lw_all_mon,toa_net_all_mon,toa_sw_clr_t_mon,toa_lw_clr_t_mon,toa_net_clr_t_mon,toa_sw_clr_c_mon,toa_lw_clr_c_mon,toa_net_clr_c_mon,toa_cre_sw_mon,toa_cre_lw_mon,toa_cre_net_mon,gtoa_sw_all_mon,gtoa_lw_all_mon,gtoa_net_all_mon,gtoa_sw_clr_t_mon,gtoa_lw_clr_t_mon,gtoa_net_clr_t_mon,gtoa_sw_clr_c_mon,gtoa_lw_clr_c_mon,gtoa_net_clr_c_mon,gtoa_cre_sw_mon,gtoa_cre_lw_mon,gtoa_cre_net_mon,lat,lon,time
    title: "The netCDF-4 subset of CERES_EBAF_Edition4.2.1_200003-202605.nc the loader read through the ASDC OPeNDAP endpoint on 2026-09-19 (553,908,789 bytes, sha256 66dcc604...; Edition 4.2.1, revised data release date March 14, 2025; 315 months 2000-03 through 2026-05, every cell of every field carrying a value in every month): the twenty-four flux variables and their coordinates, hashed in the data root's stamp and SOURCES.json"
  - id: cmr-granules
    resource: https://cmr.earthdata.nasa.gov/search/granules.json?collection_concept_id=C3880496704-LARC_CLOUD&page_size=10
    title: "CMR granule listing of CERES_EBAF Edition4.2.1 (read 2026-09-19): three granules, through 2025-12, 2026-03 and 2026-05; the newest was read"
  - id: cmr-collection
    resource: https://cmr.earthdata.nasa.gov/search/concepts/C3880496704-LARC_CLOUD.umm_json
    title: "CMR collection record for CERES_EBAF Edition4.2.1 (read 2026-09-19): short name CERES_EBAF, version Edition4.2.1, DOI 10.5067/TERRA-AQUA-NOAA20/CERES/EBAF_L3B004.2.1, temporal extent beginning 2000-03-01 and ending at present"
  - id: loeb-2020
    resource: https://doi.org/10.1175/JCLI-D-19-0381.1
    title: "Loeb and others (2020), Toward a Consistent Definition between Satellite and Model Clear-Sky Radiative Fluxes, Journal of Climate 33, 61 to 75: the methodology the data quality summary names for the total-region clear-sky fluxes, and the size of the adjustment between the two definitions (the record verified on the Crossref registry 2026-09-19, title, authors, journal, volume, pages and year; the journal page sits behind a bot check and was not read)"
  - id: loeb-2018
    resource: https://doi.org/10.1175/JCLI-D-17-0208.1
    title: "Loeb and others (2018), Clouds and the Earth's Radiant Energy System (CERES) Energy Balanced and Filled (EBAF) Top-of-Atmosphere (TOA) Edition-4.0 Data Product, Journal of Climate 31, 895 to 918: the Edition 4.0 product whose data quality summary table is the published anchor, and the regional monthly flux uncertainties (the record verified on the Crossref registry 2026-09-19; the journal page was not read)"
  - id: loeb-2024
    resource: https://doi.org/10.1175/JCLI-D-24-0180.1
    title: "Loeb and others (2024), Continuity in Top-of-Atmosphere Earth Radiation Budget Observations, Journal of Climate 37, 6093 to 6108: the satellite transitions the record is stitched across, which is why a run whose window crosses them reads the bundle's dataset concept first (the record verified on the Crossref registry 2026-09-19; the journal page was not read)"
  - id: data-root
    resource: knowledge/references/retrieval/cloud-radiative-effect-root/RECORD.json
    title: "The stamped data root committed beside this concept: the loader's stamp, the coverage table, the bookkeeping table, the manifest of the three files, and SOURCES.json for the downloads and the documents read"
  - id: loaders
    resource: skills/cloud-radiative-effect/scripts/cre_data_root.py
    title: "The loader and the stamp assembler in the running skill's scripts (cre_ceres_fluxes.py, cre_data_root.py), each with a selftest"
---

# Cloud radiative effect at the top of the atmosphere (attested)

The sanctioned computation behind any receipted statement of how much
clouds change the Earth's radiation budget at the top of the
atmosphere over a window and a region: the all-sky flux of CERES EBAF
minus its clear-sky flux, in the shortwave, the longwave and the
net.[^dataset][^dqs] It exists in this capability because the arithmetic
is trivial and the bookkeeping is not. The product carries two fields
that are both called clear-sky, the effect inherits the convention of
whichever one is subtracted, and nothing in a difference of two flux
variables records which that was.[^convention][^gotcha-clear-sky] So
the convention is a declared parameter here, the receipt states which
field it read, the receipt carries the same three terms under the
other convention beside them, and a convention the product does not
carry is refused rather than approximated. Version 1 is proven on a
synthetic fixture with a planted effect and a planted convention
offset, and its real-data anchor is the stamped data root committed
beside it, run over the decade the published global mean covers.[^data-root]
A fixture receipt says in its caveats that it proves the chain, not
the Earth.

**Status note (the move of 2026-09-20).** This concept, its executor,
its attester, its two loaders and its stamped data root moved from the
`asdc` bundle of nasa-daac-knowledge into this capability under ADR E,
a computation is a skill. Nothing about any number changed: all four
reference runs below were re-run at the new paths on 2026-09-20 and
reproduced every value they state, term by term, and the run
identifiers changed only because a run identifier is bound to the
package the run is evidence for. The concept is left at `status:
draft` with its signature block untouched, because a move changes
digests the signature covers; the maintainer re-signs after merge.

## Parameters

- `window` (string, required): an inclusive month range
  `YYYY-MM:YYYY-MM` within the flux record (the fixture spans 2000-03
  through 2026-05; a data root spans what its stamp holds, the same
  months for the committed root). At least 24 months of it must carry
  a value.
- `region` (string, required): one of `global`, `tropics`,
  `northern-extratropics`, `southern-extratropics`,
  `northern-midlatitudes`, `southern-midlatitudes`, `arctic`,
  `antarctic`. Each is a band of whole one degree zones, so its mean
  is the product's own global mean restricted to those zones. A region
  that needs a surface type or sea ice mask (`ocean`, `land`,
  `sea-ice`) is refused, because the fields read carry no such field.
- `clear_sky` (string, required, `--clear-sky`): `total-region` or
  `cloud-free-area`, the two conventions the energy balanced product's
  variables carry. Anything else is refused, `pristine`,
  `computed-cloud-removed` and `total-sky-no-aerosol` by name, because
  those are SYN1deg quantities and this product has no such
  field.[^convention]

## The terms and the bookkeeping

Every term is a flux in watts per square metre of the region, the
window mean of a monthly regional mean, with an uncertainty at the 95
percent level and the stamp it came from:[^dqs][^data-root]

- **cre_shortwave**: the clear-sky minus the all-sky outgoing
  shortwave flux. Negative where clouds reflect more sunlight than the
  clear column, which is everywhere at these scales.
- **cre_longwave**: the clear-sky minus the all-sky outgoing longwave
  flux. Positive where clouds reduce the flux to space.
- **cre_net**: the all-sky minus the clear-sky net downward flux, read
  from the product's net fields and not formed from the two terms
  above.

The sign rule is the product's own: the shortwave and longwave fields
are outgoing fluxes, the net field is downward minus upward, and the
summary states both that cloud radiative effects are computed as
all-sky flux minus clear-sky flux and that the net is downward minus
upward.[^dqs] The receipt states the rule for each term and the
attester checks each series against the flux columns it came from.

The uncertainty of each term is the larger of the sampling half width
of the window mean (the residual about the calendar-month means under
a lag-1 autocorrelated model, Student's t on the effective degrees of
freedom) and the formal error the per-month floor propagates. The
product ships no uncertainty field, so the floor is measured on the
series by the loader (the standard deviation of adjacent-month
differences of that term with its calendar-month means removed, over
the square root of two) and the published regional monthly flux
uncertainties are written in the stamp beside it, for comparison and
never mixed into it.[^dataset][^loeb-2018]

The residual is cre_net minus the sum of the shortwave and longwave
terms. That decomposition is an identity of the product's own fields,
since the net flux is the solar irradiance minus the two outgoing
fluxes, so the residual is a check on the fields and not a physical
closure: the bar is a stated tolerance of 0.01 W m-2, two orders above
the storage and rounding granularity of the six fields that enter it
and three orders below the smallest term, and the verdict
`decomposition_closes` is true when the residual lies inside it. The
combined uncertainty (the three term uncertainties in quadrature) is
carried beside the verdict and is not its bar, because the three terms
are three views of one month's fields and their sampling half widths
are not independent of each other.

The bookkeeping table travels as the receipt's `bookkeeping` block,
and the attester refuses a receipt missing any of it: the convention
(which field was subtracted, what that convention is, the two the
product carries, the ones it does not and why), the weighting, the
edition, the uncertainty basis, the region (the latitude band, the
regions resolvable and the ones that are not), the decomposition rule
and its tolerance, the sign convention, the published anchor, and the
window handling (a month with no value for this region and convention
is a hole dropped from the mean and never interpolated; whether the
window is whole years).[^data-root]

## The convention, and what it is worth

The four quantities the CERES products call clear-sky, and which
convention each field carries, belong to the provider bundle's
convention concept; the size of the EBAF adjustment between its two and the
edition history of the product's own cloud radiative effect belong to
its gotcha. Neither is restated
here.[^convention][^gotcha-clear-sky][^loeb-2020] What this
computation adds is that the choice becomes a receipt fact. The
receipt names the bound convention and the variable suffix it reads
(`clr_t` for the total region, `clr_c` for the cloud-free areas,
which the granule's own metadata response spells out in the long
names), and its `convention_contrast` block carries the same three
terms over the same window and region under the other convention,
with the difference.[^dmr] Over the published decade the global net
cloud radiative effect is -17.889 W m-2 on the cloud-free-area
convention and -19.635 on the total-region one, a difference of 1.746
W m-2, which is a fifth of a decade's worth of any cloud feedback
signal a reader would be looking for, produced by nothing but the
choice of subtrahend.[^data-root]

The sign of that difference is not the same everywhere, and the
receipt says so where it matters: over the Antarctic band the
total-region convention gives a net effect of -10.995 W m-2 against
-12.664 on the cloud-free-area one, so the total-region effect is the
less negative of the two where globally it is the more negative. That
is the high latitude structure of the published adjustment showing up
in the terms, and it is the reason a regional cloud radiative effect
compared across conventions cannot be corrected by a single global
number.[^loeb-2020][^gotcha-clear-sky]

The product's anchoring to an in situ ocean heating estimate, which
this capability's energy budget computation carries as a caveat on every
absolute flux, does not reach these terms: the anchor is a one-time
adjustment applied to the shortwave and longwave fluxes of the whole
record, and it enters the all-sky and the clear-sky field of the same
month, so it cancels in their difference. The terms here are
differences of two fields, never an absolute level, which is why this
concept carries no anchoring block where the energy budget's carries
one.[^energy-budget]

## The weighting and the region

The fields are area weighted with the CERES one degree zonal geodetic
weights, the weights the product's own global means are formed with:
an oblate spheroid with the equatorial radius 6378.137 km and the
polar radius 6356.752 km, and the solar division factor 4.0034 rather
than 4.[^geodetic-weights][^dqs] A region is a band of whole one
degree zones, so its mean is the same weighted mean restricted to
those zones, which is what weighting a region the way the product's
own global mean is defined means here. The loader checks itself: the
weights applied to the global band reproduce the product's own
`gtoa_` global means of all nine fields to a maximum of 4.5e-4 W m-2
across the 315 months, and the total-region cloud radiative effect
formed from them reproduces the product's own `gtoa_cre_` variables to
4.1e-5 (shortwave), 1.4e-5 (longwave) and 1.5e-3 (net) W m-2. Both
cross-checks are in the stamp.[^data-root]

## The fixture and its known truth

`--fixture --seed N` generates the record deterministically from a
hash-based Gaussian stream (no numeric library in the path, so the
digest cannot drift with a release): for every region one all-sky
series, as the product carries one all-sky field; a total-region
clear-sky column formed from a planted cloud radiative effect with an
annual cycle, an interannual AR(1) component and noise at the stated
0.40 W m-2; a cloud-free-area column formed from that same effect plus
a planted per-region offset and a small independent part, as the
product's two clear-sky fields are two measurements of nearly the same
thing; and net columns formed from the other two, so the decomposition
holds by construction. The planted effects and offsets are the order
of the real record's regional means over the product's anchor decade,
the polar offsets with the reversed sign the record shows. The receipt
carries the seed, the fixture digest, the generator's digest (the
executor itself), the planted truth, and a `known_truth` block with
the planted terms and the planted convention contrast beside what was
recovered; the attester regenerates the fixture and compares every
value.

## The refusal rule

A run writes a refusal receipt (`refused: true`, a `reason_code` and
the reason in words) and exits 3, never a number, when the clear-sky
convention is not one the product carries
(`clear-sky-convention-not-carried`); when the region is not one the
computation resolves (`region-not-resolvable`); when the window lies
outside the flux record (`window-outside-record`); when fewer than 24
months of the window carry a value (`too-few-months`); or when a
window mean's half width cannot be stated (`interval-not-stated`).
The first two are settled by the bound parameters alone, so the
attester reproduces them without the record; the rest need the
fixture or the tree. The attester attests a refusal PASS only as a
refusal, with the reason reproduced; its verdict line reads `PASS
refusal`.

## The attester criterion (deterministic, consumer-side)

A run PASSES only when all hold: every declared field present; the
code hash is the sanctioned file; the `bundle` block names this
package, version and release lock digest and the `capability` block is
well formed; a runtime is named; the fixture regenerated at the
receipt's seed hashes to the receipt's digest and so does the
generator (for a data root, the record, the files and the stamp are
present, and with the tree given they hash to the receipt's digests);
the bound convention is one the product carries, its bookkeeping is
the sanctioned block for it and the contrast names the other one; the
bound region is one the computation resolves and carries its
sanctioned latitude band; the months used and missing partition the
window and the three effect series are the stated differences of the
six flux columns; the three window means with their half widths and
formal errors, the term uncertainties, the residual, the combined
uncertainty, the verdict, the other convention's three terms and the
distance from the published global mean recompute from the receipt
(1e-9 relative, with the attester's own Student's t from the density);
the bookkeeping is complete, the published anchor block is the
sanctioned one and the decomposition tolerance is the sanctioned one;
and stated plausibility bounds hold (the shortwave term between minus
120 and 0 W m-2, the longwave between minus 10 and 60, the net between
minus 80 and 20, the per-month uncertainties positive and below 20),
with, on the fixture, each recovered term within 1.5 W m-2 of the
planted one and the recovered convention contrast within 0.3 of it.
The selftest covers a pass on two regions and both conventions,
thirteen tampers each failing on its check (a relabelled convention, a
relabelled region, a forged convention contrast, a forged published
distance and an unsanctioned published anchor among them), a wrong
release, a tampered computation, all five refusals and a forged one, a
synthetic data root verified against its tree, a fabricated tree, the
published anchor comparison on a data root, and the attestation
document.

## The data root, for a real run

A computation is a skill (ADR E in the marketplace repository): this
concept lives in the capability that runs it, and the skill that runs
it is `cloud-radiative-effect` beside it, whose scripts hold the
executor, the attester and the two loaders this concept names. The
executor's usage text (`--help`) states the fixture run, the refusal
rule and the receipt path, the attester's usage text states how a
receipt is attested, and this section is the part that is contract and
not procedure, the layout of the data root the executor reads.

The real run's tree is committed at
knowledge/references/retrieval/cloud-radiative-effect-root, built by
the loader in the skill's scripts (cre_ceres_fluxes.py for the flux means, with
`--selftest` on a synthetic grid and `--fetch` for the downloads) and
stamped by cre_data_root.py, which writes RECORD.json with the
coverage table and the bookkeeping table from the loader's stamp;
SOURCES.json records the downloads and the documents read. This is the
layout the computation reads. `--data-root DIR` in place of
`--fixture`:

```
DIR/
  RECORD.json             the stamp: record name, the manifest of every file,
                          manifest_sha256, verified_utc, the loader's stamp,
                          the coverage table (the months each region and
                          convention carries), and the bookkeeping table
                          under "bookkeeping"
  cre-fluxes.csv          region,convention,month,sw_all_W_m2,lw_all_W_m2,
                          net_all_W_m2,sw_clr_W_m2,lw_clr_W_m2,net_clr_W_m2,
                          cre_sw_uncertainty_W_m2,cre_lw_uncertainty_W_m2,
                          cre_net_uncertainty_W_m2
                          one row per region, convention and calendar month
  cre-fluxes-stamp.json   what the loader read, from where, when, the product
                          version, the grid, the weights and their hash, the
                          variable each convention reads, the regions and their
                          share of the geodetic weight, the aggregation, the
                          uncertainty floors, the two cross-checks, and the
                          sha256 of every file read
  SOURCES.json            every file read with its URL, hash and time, and the
                          registry records verified
```

Months are `YYYY-MM`, unique and in order within each region and
convention. `bookkeeping` must carry `convention.statement`,
`weighting.statement`, `edition.statement`, `uncertainty.basis` and
`region.statement`, each a statement in words; the executor refuses a
stamp that lacks any of them, and checks every file in the manifest
against its hash before it reads a number. The receipt copies the
stamp and the file digests.

Which tool produces each file:

- `cre-fluxes.csv` and `cre-fluxes-stamp.json`: the loader
  cre_ceres_fluxes.py, from the Edition 4.2.1 file and the zonal
  geodetic weights file; with `--fetch` it downloads a netCDF-4 subset
  of the granule through the ASDC OPeNDAP endpoint into the path
  `--product` names (outside the tree), first without credentials and
  then once with the Earthdata Login bearer token from
  `EARTHDATA_TOKEN` as a request header, which it never writes down,
  and the weights file from the CERES documents host. Its usage text
  states the arguments.
- `RECORD.json`: the stamp assembler cre_data_root.py (`--root DIR
  --record NAME`, then `--root DIR --check`), after SOURCES.json is
  written.

The data root is recorded package-relative when it sits under this
repository, so the run id reproduces on any machine.

## Reference runs

**Fixture run (seed 7, global, total-region, 2006-01 through 2020-12,
measured 2026-09-19 in the provider bundle and reproduced 2026-09-20
at this path, under the runtime name run_checks, run
sha256:70659951ad0d9a66; the id is bound to the runtime name and to
the package the run is evidence for, so it is not the id the provider
bundle recorded, while every value below is).** 180 of
180 months. cre_shortwave -45.5600 W m-2 with an uncertainty of 0.3096
against the planted -45.3500; cre_longwave +25.7230 with 0.2449
against the planted +25.7200; cre_net -19.8370 with 0.3774 against the
planted -19.6300. Residual -2.8e-14 against a bar of 0.01;
`decomposition_closes` true. The other convention gives a net effect of
-18.0774, a contrast of -1.7596 against the planted -1.7500. The
refusal case the chain exercises is `--clear-sky pristine` on the
fixture: exit 3 with `clear-sky-convention-not-carried`, attested as a
refusal. The registry entry `cloud-radiative-effect` in
verification/reference_runs.yaml records the arguments, and the golden
verification/cloud_radiative_effect_chain.py runs the chain.

**Real-data run, the published anchor (the stamped data root
cloud-radiative-effect-root-2026-09-19, global, cloud-free-area,
2005-07 through 2015-06, measured 2026-09-19 in the provider bundle
and reproduced 2026-09-20 at this path, under the runtime name
run_checks, run sha256:67600ea561c41465).** The flux terms were built
by the loader from the Edition 4.2.1 granule through 2026-05 read
through the ASDC OPeNDAP endpoint, as 315 monthly area weighted
regional means per region and convention, every cell of every field
carrying a value in every month.[^opendap-subset][^loaders][^data-root]
120 of 120 months. cre_shortwave -45.8232 W m-2 with an uncertainty of
0.1267 (sampling half width 0.1267 at an effective sample of 56.1
months, the formal error 0.0775); cre_longwave +27.9340 with 0.0633
(effective sample 80.9); cre_net -17.8894 with 0.1433 (effective
sample 46.2). Residual -1.1e-04 W m-2 against a bar of 0.01, the
largest single month 1.6e-03; `decomposition_closes` true. The other
convention over the same months gives -45.3500, +25.7148 and -19.6352,
so the cloud-free-area convention sits +1.7458 W m-2 from the
total-region one in the net.

**The published anchor.** The CERES_EBAF_Ed4.0 Data Quality Summary's
table of global mean TOA fluxes for July 2005 through June 2015 gives
a shortwave cloud radiative effect of -45.8, a longwave one of 28.0
and a net one of -17.9 W m-2, and the clear-sky flux of Edition 4.0 is
the cloud-free-area one, which is why the anchored run binds that
convention and that decade.[^dqs-ed4-0][^loeb-2018] The run sits
-0.023 W m-2 from the published shortwave, -0.066 from the longwave
and +0.011 from the net, all inside the 0.1 W m-2 the published table
is rounded to. The distance carries both that rounding and the change
from Edition 4.0 to Edition 4.2.1, and the receipt says so; it is not
a measurement of either. The companion run on the same window and
region with `--clear-sky total-region` (run sha256:e66cfd9751224962)
gives a net effect of -19.6352 and states no distance, because the
published number is not of that convention, and the receipt records
that refusal to compare rather than comparing.

**A regional run (the same data root, antarctic, total-region,
2006-01 through 2020-12, run sha256:f4f2eaf640f54544).** 180 of 180
months. cre_shortwave -28.8432 W m-2, cre_longwave +17.8481, cre_net
-10.9951, against -12.6639 on the cloud-free-area convention: the
reversed sign of the convention difference at high latitude, quoted in
the convention section above.

**Pass bar.** There is no measured science tolerance to record. The
verdict compares the decomposition residual against the stated
granularity of the product's fields, and the attester recomputes both.
The plausibility bounds are sanity bounds on the chain, not science
tolerances, and the distance from the published anchor is stated, not
gated.

## Boundaries

The terms are differences of two fields of the same product, the same
month and the same grid, so what they do not carry is as important as
what they do. They are not a cloud feedback: a cloud radiative effect
is the difference clouds make to the flux in the atmosphere as it was,
not the response of clouds to warming, and the two are different
quantities with different signs in parts of the literature. They are
not comparable across conventions, and the receipt's contrast block is
the size of the incomparability rather than a conversion; no
conversion between the two conventions is computed here, because the
documentation states the size of the adjustment in the global mean and
its regional shape but publishes no per-cell conversion.[^loeb-2020]
They carry the regional monthly flux uncertainties of the product only
through the measured per-month floor, not through the published
numbers, which are of a different kind and are written in the stamp for
comparison.[^loeb-2018] A window that crosses the Terra-only, Terra
plus Aqua and NOAA-20-only boundaries carries the climatology
adjustments the record is stitched with, which the provider bundle's dataset
concept owns; no trend is computed here, and a reader who wants one
reads that concept and the continuity paper
first.[^dataset][^loeb-2024] The regions are latitude bands: no ocean,
land or sea ice region is resolvable from the fields read, and the
computation refuses one rather than approximating it. One real-data
tree exists, covering 2000-03 through 2026-05 for the eight regions and
both conventions. Produced by Open Science Pillars, not a NASA or CERES
product.

**Verification.** The Edition 4.2 data quality summary was read on
2026-09-19 for the clear-sky definitions, the cloud radiative effect's
definition change and the sign rule; the Edition 4.0 summary the same
day for the published global mean table that anchors the real
run.[^dqs][^dqs-ed4-0] The granule was read the same day through the
ASDC OPeNDAP endpoint after CMR listed it, its metadata response read
first for the variable long names that fix which convention each field
carries, and its hash is in the data root's
stamp.[^cmr-granules][^cmr-collection][^dmr][^opendap-subset] The
zonal geodetic weights were read the same day and reproduce the
product's own global means to 4.5e-4 W m-2, which is the basis of the
weighting statement.[^geodetic-weights] Every DOI was verified against
the Crossref registry the same day (title, authors, journal, volume,
pages, year); the three journal pages sit behind a bot check and were
not read, and the concept says so where each is
cited.[^loeb-2020][^loeb-2018][^loeb-2024] The chain is verified on
every change by the repository's check routine, which runs the
attester's selftest, the fixture run and its refusal, the loaders'
selftests, the data root's manifest check and the record run attested
against the tree, all of it in the golden
verification/cloud_radiative_effect_chain.py, which also runs the
eight regions on both conventions and holds the sign reversal of the
convention difference over the polar bands.

[^convention]: knowledge/asdc/conventions/ceres-clear-sky-conventions.md, the four quantities called clear-sky and which convention each field carries
[^gotcha-clear-sky]: knowledge/asdc/gotchas/ebaf-clear-sky-definitions.md, the two EBAF definitions, the edition history and the size of the adjustment
[^dataset]: knowledge/asdc/datasets/ceres-ebaf-ed4-2.md, the product, its editions, its uncertainties and the satellite transitions
[^energy-budget]: knowledge/computations/energy-budget.md, this capability's other attested computation on this product
[^dqs]: CERES_EBAF_Ed4.2 and Ed4.2.1 Data Quality Summary, version 8, 2026-09-10
[^dqs-ed4-0]: CERES_EBAF_Ed4.0 Data Quality Summary, 2018-01-17, Table 6-1
[^geodetic-weights]: CERES zonal geodetic weights, zone_weights_lou.txt
[^dmr]: the granule's OPeNDAP metadata response, read 2026-09-19
[^opendap-subset]: the netCDF-4 subset of CERES_EBAF_Edition4.2.1_200003-202605.nc read through the ASDC OPeNDAP endpoint
[^cmr-granules]: CMR granule listing of CERES_EBAF Edition4.2.1, read 2026-09-19
[^cmr-collection]: CMR collection record C3880496704-LARC_CLOUD, read 2026-09-19
[^loeb-2020]: Loeb and others (2020), Journal of Climate 33, doi:10.1175/JCLI-D-19-0381.1
[^loeb-2018]: Loeb and others (2018), Journal of Climate 31, doi:10.1175/JCLI-D-17-0208.1
[^loeb-2024]: Loeb and others (2024), Journal of Climate 37, doi:10.1175/JCLI-D-24-0180.1
[^data-root]: knowledge/references/retrieval/cloud-radiative-effect-root/RECORD.json, the stamped data root
[^loaders]: skills/cloud-radiative-effect/scripts, the flux loader and the stamp assembler
