#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Write the methods paragraph and the reference list of an attested
run from the receipt's bookkeeping block and the concept's sources, and
from nothing else.

This is the paragraph a scientist hands a postdoc to paste into a draft.
It computes nothing and it composes nothing freehand: every sentence is
filled from receipt fields by the dotted paths the catalog below
records, every reference is a source entry the concept's frontmatter
carries, in the concept's own words, and the provenance section names
the field behind every sentence so a reader can check each one against
the receipt. A fact the receipt does not carry is not written; it is
listed as not carried.

What the paragraph names, as the receipt records them: the product
edition and its release date, the clear-sky convention and the variable
suffix it reads (for the cloud radiative effect), the anchoring decade
and the months the window shares with it, and the Argo receipt's
identity (for the energy budget closure).

What it refuses, each with exit 4 and a reason code, and never a
partial paragraph:

  attester-did-not-pass   the attester did not PASS this receipt. A
                          data-root receipt is attested with
                          --data-root DIR, without which the
                          attesters take the data digests on the
                          executor's word.
  refused-receipt         a refusal receipt. It carries a reason code
                          and no terms, and a refusal is reported in
                          the executor's words, not written up as a
                          method that produced a number.
  fact-not-in-receipt     a sentence asked for with --claim TEXT. Any
                          fact that is not a field of this receipt or a
                          source entry of its concept is not this
                          skill's to write: it goes in the author's own
                          words, over the author's own name.
  source-not-in-concept   a reference asked for with --cite ID that the
                          concept's frontmatter does not carry. A
                          citation is never reconstructed from memory.
  unknown-computation     a receipt of a computation this catalog does
                          not carry a paragraph for.

The concept, the attester and the receipt's computation are files of
this package, reached at `${CLAUDE_PLUGIN_ROOT}` the way the skills
that run them reach them.

Usage:
  uv run skills/methods/scripts/methods.py RECEIPT.json \
      --data-root DIR --out methods.md
  uv run skills/methods/scripts/methods.py --selftest
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

BUNDLE = "asdc"
CAPABILITY = "atmospheric-physics"
REFUSALS = ("attester-did-not-pass", "refused-receipt", "fact-not-in-receipt",
            "source-not-in-concept", "unknown-computation")

# One entry per computation this skill writes a paragraph for. A
# sentence is a template and the receipt paths that fill it: every
# number and every name in the output arrives through one of these
# paths, and a sentence whose paths the receipt does not carry is
# dropped and listed as not carried. Nothing here states a fact.
CATALOG = {
    "skills/cloud-radiative-effect/scripts/cloud_radiative_effect.py": {
        "name": "cloud-radiative-effect",
        "concept": "knowledge/computations/cloud-radiative-effect.md",
        "attester": "skills/cloud-radiative-effect/scripts/cloud_radiative_effect_check.py",
        "skill": "atmospheric-physics/cloud-radiative-effect",
        "sentences": [
            ("run",
             "The cloud radiative effect at the top of the atmosphere was "
             "computed for the region {region} over {window} with the "
             "attested computation {concept_path} of the {capability} "
             "capability, run {run_id} under the executor {code_sha256}.",
             {"region": "bound_parameters.region",
              "window": "bound_parameters.window",
              "run_id": "run_id", "code_sha256": "code_sha256"}),
            ("input",
             "The input was the stamped record {record}, whose manifest "
             "hashes to {manifest_sha256} and whose files the executor "
             "checked against that manifest before reading a number.",
             {"record": "data.record", "manifest_sha256": "data.manifest_sha256"}),
            ("fixture",
             "The input was the executor's synthetic fixture at seed {seed}, "
             "digest {digest}, regenerated and compared by the attester; a "
             "fixture run proves the chain and not the Earth.",
             {"seed": "data.seed", "digest": "data.digest"}),
            ("edition",
             "The product is {product}, {product_version}, DOI {doi}, read "
             "from the file {file}.",
             {"product": "data.stamp.product",
              "product_version": "bookkeeping.edition.product_version",
              "doi": "bookkeeping.edition.doi",
              "file": "bookkeeping.edition.file"}),
            ("edition_synthetic",
             "The edition bookkeeping this run carries is: "
             "{edition_statement}",
             {"edition_statement": "bookkeeping.edition.statement"}),
            ("convention",
             "The clear-sky convention was bound to {convention}, read from "
             "the variable suffix {suffix}: {definition}",
             {"convention": "bookkeeping.convention.bound",
              "suffix": "bookkeeping.convention.variable_suffix",
              "definition": "bookkeeping.convention.definition"}),
            ("inheritance",
             "The convention is a receipt fact because {inheritance}",
             {"inheritance": "bookkeeping.convention.inheritance"}),
            ("weighting",
             "The fields were weighted as follows: {weighting}",
             {"weighting": "bookkeeping.weighting.statement"}),
            ("region",
             "The region {region} is the latitude band {band_low} to "
             "{band_high} degrees, on the rule: {region_rule}",
             {"region": "bookkeeping.region.bound",
              "band_low": "bookkeeping.region.latitude_band.0",
              "band_high": "bookkeeping.region.latitude_band.1",
              "region_rule": "bookkeeping.region.rule"}),
            ("months",
             "Of the {n_calendar} calendar months of the window, {n_used} "
             "carried a value and were used; {window_rule}",
             {"n_calendar": "months.n_calendar", "n_used": "months.n_used",
              "window_rule": "bookkeeping.window_handling.rule"}),
            ("uncertainty",
             "The uncertainty of each term is {uncertainty_basis_term}; the "
             "per-month basis is: {uncertainty_basis}",
             {"uncertainty_basis_term": "terms.cre_net.uncertainty_basis",
              "uncertainty_basis": "bookkeeping.uncertainty.basis"}),
            ("terms",
             "The run states a shortwave effect of {sw} W m-2 with an "
             "uncertainty of {sw_u}, a longwave effect of {lw} with {lw_u} "
             "and a net effect of {net} with {net_u}, each a window mean of "
             "a monthly regional mean.",
             {"sw": "terms.cre_shortwave.value",
              "sw_u": "terms.cre_shortwave.uncertainty",
              "lw": "terms.cre_longwave.value",
              "lw_u": "terms.cre_longwave.uncertainty",
              "net": "terms.cre_net.value",
              "net_u": "terms.cre_net.uncertainty"}),
            ("decomposition",
             "The decomposition residual is {residual} W m-2 against a "
             "stated tolerance of {tolerance}, and the verdict "
             "decomposition_closes is {closes}; the rule is {rule}",
             {"residual": "residual.value",
              "tolerance": "bookkeeping.decomposition.tolerance_W_m2",
              "closes": "verdict.decomposition_closes",
              "rule": "bookkeeping.decomposition.rule"}),
            ("contrast",
             "The same three terms over the same months under the other "
             "convention the product carries, {other}, are {o_sw}, {o_lw} "
             "and {o_net} W m-2; the difference is the size of the "
             "incomparability between the two conventions and not a "
             "conversion, and no per-cell conversion is published.",
             {"other": "convention_contrast.convention",
              "o_sw": "convention_contrast.cre_shortwave",
              "o_lw": "convention_contrast.cre_longwave",
              "o_net": "convention_contrast.cre_net"}),
            ("published",
             "The run sits {d_net} W m-2 from the published global mean net "
             "cloud radiative effect of {p_net} W m-2, which is rounded to "
             "{rounding} W m-2; the receipt states of that anchor that it is "
             "{published_statement}",
             {"d_net": "published_comparison.distance_W_m2.cre_net",
              "p_net": "published_comparison.published.cre_net_W_m2",
              "rounding": "published_comparison.published.rounding_W_m2",
              "published_statement": "published_comparison.published.statement"}),
            ("no_published",
             "No distance from the published global mean is stated: "
             "{published_statement}",
             {"published_statement": "published_comparison.statement"}),
            ("sign",
             "The sign convention is the product's own: {sign}",
             {"sign": "bookkeeping.sign_convention.statement"}),
        ],
        "either_or": [("edition", "edition_synthetic"),
                      ("input", "fixture"),
                      ("published", "no_published")],
        # The concept source each sentence rests on, by the footnote id
        # the concept itself uses. A marker is emitted only where the
        # concept carries that id, so a footnote never dangles and no
        # citation is invented.
        "cites": {
            "input": ["data-root", "loaders"],
            "edition": ["dataset", "dqs"],
            "edition_synthetic": ["dataset"],
            "convention": ["convention", "gotcha-clear-sky"],
            "inheritance": ["convention"],
            "weighting": ["geodetic-weights", "dqs"],
            "uncertainty": ["dataset", "loeb-2018"],
            "contrast": ["gotcha-clear-sky", "loeb-2020"],
            "published": ["dqs-ed4-0", "loeb-2018"],
            "no_published": ["dqs-ed4-0"],
            "sign": ["dqs"],
        },
    },
    "skills/energy-budget-closure/scripts/energy_budget.py": {
        "name": "energy-budget",
        "concept": "knowledge/computations/energy-budget.md",
        "attester": "skills/energy-budget-closure/scripts/energy_budget_check.py",
        "skill": "atmospheric-physics/energy-budget-closure",
        "sentences": [
            ("run",
             "The Earth energy budget was closed over {window} with the "
             "attested computation {concept_path} of the {capability} "
             "capability, run {run_id} under the executor {code_sha256}.",
             {"window": "bound_parameters.window", "run_id": "run_id",
              "code_sha256": "code_sha256"}),
            ("input",
             "The input was the stamped record {record}, whose manifest "
             "hashes to {manifest_sha256} and whose files the executor "
             "checked against that manifest before reading a number.",
             {"record": "data.record", "manifest_sha256": "data.manifest_sha256"}),
            ("fixture",
             "The input was the executor's synthetic fixture at seed {seed}, "
             "digest {digest}, regenerated and compared by the attester; a "
             "fixture run proves the chain and not the Earth.",
             {"seed": "data.seed", "digest": "data.digest"}),
            ("edition",
             "The radiation product is {product}, {product_version}, DOI "
             "{doi}, read from the file {file}.",
             {"product": "data.stamp.product",
              "product_version": "bookkeeping.edition.product_version",
              "doi": "bookkeeping.edition.doi",
              "file": "bookkeeping.edition.file"}),
            ("edition_synthetic",
             "The edition bookkeeping this run carries is: "
             "{edition_statement}",
             {"edition_statement": "bookkeeping.edition.statement"}),
            ("weighting",
             "The radiation term was taken from the series described as: "
             "{weighting}",
             {"weighting": "bookkeeping.weighting.statement"}),
            ("anchor",
             "The product's global mean net flux is anchored: {anchor}",
             {"anchor": "bookkeeping.anchoring.anchor.statement"}),
            ("anchor_decade",
             "The anchoring decade is {period_low} through {period_high}, at "
             "{anchor_value} W m-2 with an uncertainty of {anchor_unc}, and "
             "{shared} of the {in_window} months of this window fall inside "
             "it; {independence}",
             {"period_low": "bookkeeping.anchoring.anchor.period.0",
              "period_high": "bookkeeping.anchoring.anchor.period.1",
              "anchor_value": "bookkeeping.anchoring.anchor.value_W_m2",
              "anchor_unc": "bookkeeping.anchoring.anchor.uncertainty_W_m2",
              "shared": "bookkeeping.anchoring.months_shared_with_anchor_decade",
              "in_window": "bookkeeping.anchoring.months_in_window",
              "independence": "bookkeeping.anchoring.independence"}),
            ("argo",
             "The 0 to 2000 dbar ocean heat content rate was read, never "
             "recomputed, from the Argo receipt {argo_run_id} of the "
             "computation {argo_computation} at {argo_code}, over the window "
             "{argo_window} on the record {argo_record}, produced by the "
             "{argo_bundle} capability at version {argo_version}; its stated "
             "rate is {argo_rate} ZJ per year with an uncertainty of "
             "{argo_rate_unc}.",
             {"argo_run_id": "bookkeeping.ocean_input.receipt.run_id",
              "argo_computation": "bookkeeping.ocean_input.receipt.computation",
              "argo_code": "bookkeeping.ocean_input.receipt.code_sha256",
              "argo_window": "bookkeeping.ocean_input.receipt.bound_parameters.window",
              "argo_record": "bookkeeping.ocean_input.receipt.record",
              "argo_bundle": "bookkeeping.ocean_input.receipt.bundle.name",
              "argo_version": "bookkeeping.ocean_input.receipt.bundle.version",
              "argo_rate": "bookkeeping.ocean_input.receipt.trend_ZJ_yr",
              "argo_rate_unc": "bookkeeping.ocean_input.receipt.trend_uncertainty_ZJ_yr"}),
            ("argo_synthetic",
             "The ocean input bookkeeping this run carries is: "
             "{ocean_statement}",
             {"ocean_statement": "bookkeeping.ocean_input.statement"}),
            ("argo_domain",
             "The ocean side's domain is: {domain_scaling}",
             {"domain_scaling": "bookkeeping.ocean_input.scaling"}),
            ("area",
             "The area convention is: {area_rule}",
             {"area_rule": "bookkeeping.area_convention.rule"}),
            ("months",
             "Of the {n_calendar} calendar months of the window, {n_used} "
             "carried a value and were used; {window_rule}",
             {"n_calendar": "months.n_calendar", "n_used": "months.n_used",
              "window_rule": "bookkeeping.window_handling.rule"}),
            ("terms",
             "The run states a net top-of-atmosphere flux of {toa} W m-2 "
             "with an uncertainty of {toa_u}, an ocean heat content rate of "
             "{ohc} with {ohc_u}, a published deep ocean rate of {deep} and "
             "a published non-ocean rate of {non_ocean}.",
             {"toa": "terms.toa_net.value", "toa_u": "terms.toa_net.uncertainty",
              "ohc": "terms.ohc_0_2000.value",
              "ohc_u": "terms.ohc_0_2000.uncertainty",
              "deep": "terms.deep_ocean.value",
              "non_ocean": "terms.non_ocean.value"}),
            ("verdict",
             "The residual is {residual} W m-2 against a combined "
             "uncertainty of {bar}, and the verdict "
             "closed_within_uncertainty is {closed}, on the rule: "
             "{verdict_rule}",
             {"residual": "verdict.residual_W_m2", "bar": "verdict.bar_W_m2",
              "closed": "verdict.closed_within_uncertainty",
              "verdict_rule": "verdict.rule"}),
            ("anomaly",
             "Beside the absolute terms the run states the net flux anomaly "
             "trend against the window's own mean, {trend} W m-2 per decade "
             "with an uncertainty of {trend_u}, formed on the rule: "
             "{series_rule}",
             {"trend": "terms.toa_net_anomaly_trend.value",
              "trend_u": "terms.toa_net_anomaly_trend.uncertainty",
              "series_rule": "terms.toa_net_anomaly_trend.series_rule"}),
        ],
        "either_or": [("edition", "edition_synthetic"),
                      ("input", "fixture"),
                      ("argo", "argo_synthetic")],
        "cites": {
            "input": ["data-root", "loaders"],
            "edition": ["dataset", "dqs"],
            "edition_synthetic": ["dataset"],
            "weighting": ["dqs", "geodetic-weights"],
            "anchor": ["gotcha-anchor", "loeb-2018"],
            "anchor_decade": ["gotcha-anchor", "johnson-2016"],
            "argo": ["ohc-receipt"],
            "argo_synthetic": ["ohc-receipt"],
            "argo_domain": ["ohc-receipt", "vs-2023"],
            "terms": ["vs-2023"],
            "anomaly": ["gotcha-baseline", "loeb-2021"],
        },
    },
}


class Refused(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def refuse(code: str, message: str):
    raise Refused(code, message)


# ---- the installed bundle

def package_root() -> Path:
    """This package's root: `${CLAUDE_PLUGIN_ROOT}` where the runtime
    sets it, else the package tree this script ships in. The executor,
    the attester and the concept are files of this package now, so
    nothing is resolved through an installed provider bundle."""
    override = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if override:
        root = Path(override).expanduser().resolve()
        if not (root / ".osp" / "package.yaml").is_file():
            sys.exit(f"CLAUDE_PLUGIN_ROOT={root} is no package tree: it "
                     "carries no .osp/package.yaml")
        return root
    here = Path(__file__).resolve().parent
    for p in (here, *here.parents):
        if (p / ".osp" / "package.yaml").is_file():
            return p
    sys.exit("no CLAUDE_PLUGIN_ROOT in the environment and no package "
             f"tree above {here}; run this script from its plugin")


def attest(receipt_path: Path, attester: Path, data_root=None) -> str:
    cmd = ["uv", "run", str(attester), str(receipt_path)]
    if data_root is not None:
        cmd += ["--data-root", str(data_root)]
    run = subprocess.run(cmd, capture_output=True, text=True)
    text = (run.stdout or "").strip() or (run.stderr or "").strip()
    lines = [line for line in text.splitlines() if line.strip()]
    line = lines[-1] if lines else "the attester printed nothing"
    if run.returncode != 0 or not line.startswith("PASS"):
        refuse("attester-did-not-pass",
               f"{attester.name} did not PASS this receipt, so there is "
               f"nothing licensed to write up. Its last line: {line}.")
    return line


# ---- the concept's sources

def concept_sources(concept: Path):
    """The source entries the concept's frontmatter carries, in its own
    order and its own words. The reference list is these and nothing
    else; no citation is composed here."""
    text = concept.read_text(encoding="utf-8")
    if not text.startswith("---"):
        sys.exit(f"{concept} carries no frontmatter to read sources from")
    front = text.split("---", 2)[1]
    entries, current, inside = [], None, False
    for line in front.splitlines():
        if re.match(r"^sources:\s*$", line):
            inside = True
            continue
        if not inside:
            continue
        if not line.startswith((" ", "\t")) and line.strip():
            break
        item = re.match(r"^\s*-\s+id:\s*(.+?)\s*$", line)
        if item:
            current = {"id": unquote(item.group(1))}
            entries.append(current)
            continue
        pair = re.match(r"^\s+(resource|title):\s*(.*)$", line)
        if pair and current is not None:
            current[pair.group(1)] = unquote(pair.group(2))
    if not entries:
        sys.exit(f"{concept} carries no sources to build a reference list from")
    return entries


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


# ---- the receipt's fields

def field(receipt, path: str):
    """One receipt field by its dotted path; a numeric part indexes a
    list, so a latitude band's ends are reachable as .0 and .1."""
    node = receipt
    for part in path.split("."):
        if isinstance(node, list):
            if not part.isdigit() or int(part) >= len(node):
                return None
            node = node[int(part)]
            continue
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


# Placeholders that hold a magnitude rather than a signed quantity, so
# that an uncertainty or a tolerance is not written with a sign it does
# not carry. The value itself is the receipt's; only its spelling is
# decided here.
MAGNITUDE_KEYS = ("_u", "_unc", "tolerance", "bar", "rounding")


def magnitude(key: str) -> bool:
    return key.endswith(MAGNITUDE_KEYS) or key in ("tolerance", "bar", "rounding")


def show(value, as_magnitude: bool = False) -> str:
    """The receipt's value, spelled. Four decimals, and scientific
    notation below a tenth of a milliunit so that a residual three
    orders under its bar is not shown as zero; the receipt carries the
    value at full precision either way."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if value and abs(value) < 1e-4:
            return f"{abs(value):.3e}" if as_magnitude else f"{value:+.3e}"
        if as_magnitude:
            return f"{abs(value):.4f}"
        return f"{value:+.4f}" if value else "0.0000"
    return str(value)


def compose(receipt: dict, spec: dict, context: dict):
    """Every sentence whose fields the receipt carries, in catalog
    order, with the field behind each one recorded. A sentence the
    receipt cannot fill is dropped and named."""
    written, provenance, missing = [], [], []
    for name, template, paths in spec["sentences"]:
        values, gaps = dict(context), []
        for key, path in paths.items():
            value = field(receipt, path)
            if value is None:
                gaps.append(path)
            else:
                values[key] = show(value, magnitude(key))
        if gaps:
            missing.append((name, gaps))
            continue
        sentence = template.format(**values).strip()
        if not sentence.endswith((".", "!", "?")):
            sentence += "."
        written.append((name, sentence))
        provenance.append((name, dict(paths)))
    chosen = {name for name, _ in written}
    for first, second in spec.get("either_or", []):
        if first in chosen and second in chosen:
            written = [item for item in written if item[0] != second]
            provenance = [item for item in provenance if item[0] != second]
    # a branch that was never going to apply is not a gap
    alternates = {second for _, second in spec.get("either_or", [])}
    alternates |= {first for first, _ in spec.get("either_or", [])}
    kept = {name for name, _ in written}
    missing = [item for item in missing
               if item[0] not in alternates or not (alternates & kept)]
    return written, provenance, missing


def write_methods(receipt: dict, spec: dict, concept_path: str,
                  sources, verdict: str, cite_only, cited_only: bool = False):
    context = {"concept_path": concept_path, "capability": CAPABILITY,
               "bundle": BUNDLE}
    written, provenance, missing = compose(receipt, spec, context)
    ids = [entry["id"] for entry in sources]
    if cite_only:
        unknown = [want for want in cite_only if want not in ids]
        if unknown:
            refuse("source-not-in-concept",
                   f"the concept {concept_path} carries no "
                   f"source {', '.join(unknown)}; it carries "
                   f"{', '.join(ids)}. A citation is the concept's source "
                   "entry or it is not written here.")
        sources = [entry for entry in sources if entry["id"] in cite_only]

    # the footnote markers, filtered to the ids the reference list will
    # carry, so a marker never points at an entry that is not there and
    # no citation is composed from anywhere but the concept
    available = {entry["id"] for entry in sources}
    cites, used, marked = spec.get("cites", {}), [], []
    for name, text in written:
        keys = [want for want in cites.get(name, []) if want in available]
        used += keys
        marked.append(text + "".join(f"[^{key}]" for key in keys))
    if cited_only:
        sources = [entry for entry in sources if entry["id"] in set(used)]

    lines = ["# Methods", "",
             "Every sentence below is filled from a field of the receipt "
             "named in the provenance section, on a receipt the attester "
             "passed. Nothing here is composed freehand and no number is "
             "this capability's own; the computation that owns them is "
             f"{concept_path}, and the footnotes are that "
             "concept's own source entries.", ""]
    lines.append(" ".join(marked))
    lines += ["", "## What this paragraph licenses", "",
              "It licenses a reader to repeat this run and to quote the "
              "numbers of this one receipt with the caveats the concept "
              "states beside them. It licenses nothing about any other run, "
              "any other window, any other region or any other clear-sky "
              "convention, and no quantity formed by combining this receipt "
              "with another.", ""]
    lines += ["## Provenance of every sentence", "",
              f"The attester's own verdict line on this receipt: `{verdict}`",
              "",
              "| sentence | receipt field |", "| --- | --- |"]
    for name, paths in provenance:
        lines.append(f"| {name} | " + ", ".join(sorted(paths.values())) + " |")
    if missing:
        lines += ["", "## Not carried by this receipt, and so not written", ""]
        for name, gaps in missing:
            lines.append(f"- `{name}`: the receipt carries none of "
                         + ", ".join(f"`{gap}`" for gap in gaps))
    lines += ["", "## References", "",
              f"The source entries {concept_path} carries, "
              "in its own order and its own words. A reference this list does "
              "not carry is not one this skill will write.", ""]
    for entry in sources:
        lines.append(f"[^{entry['id']}]: {entry.get('title', '')} "
                     f"({entry.get('resource', '')})")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def run_methods(args) -> int:
    receipt_path = Path(args.receipt).expanduser().resolve()
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if args.claim:
        refuse("fact-not-in-receipt",
               f"this skill will not write a sentence that is not a field of "
               f"the receipt or a source entry of its concept, and what was "
               f"asked for is one: {args.claim}. The provenance section of "
               "the output names the field behind every sentence it did "
               "write; a fact from anywhere else belongs in the author's own "
               "words, over the author's own name, and not in a paragraph "
               "this skill signs with a run id.")
    computation = receipt.get("computation")
    if computation not in CATALOG:
        refuse("unknown-computation",
               f"this skill carries no paragraph for {computation}; it "
               f"carries {', '.join(sorted(CATALOG))}")
    spec = CATALOG[computation]
    base = package_root()
    concept, attester = base / spec["concept"], base / spec["attester"]
    for label, path in (("concept", concept), ("attester", attester)):
        if not path.is_file():
            sys.exit(f"this package carries no {label} at {path}")
    verdict = attest(receipt_path, attester, args.data_root)
    if receipt.get("refused"):
        refuse("refused-receipt",
               f"this receipt is a refusal ({receipt.get('reason_code')}): "
               f"{receipt.get('reason')}. It attests as a refusal and carries "
               "no terms; report it in the executor's own words rather than "
               "writing it up as a method that produced a number.")
    text = write_methods(receipt, spec, spec["concept"],
                         concept_sources(concept), verdict, args.cite,
                         args.cited_only)
    if args.out:
        out = Path(args.out).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"{out}: methods paragraph and reference list for run "
              f"{receipt.get('run_id')} of {spec['name']}")
    else:
        print(text)
    return 0


# ---- selftest

def selftest() -> int:
    """The paragraph and every refusal, on the executors' fixtures."""
    base = package_root()
    cre_exec = (base / "skills" / "cloud-radiative-effect" / "scripts"
                / "cloud_radiative_effect.py")
    eb_exec = (base / "skills" / "energy-budget-closure" / "scripts"
               / "energy_budget.py")
    me = str(Path(__file__).resolve())

    def methods(argv):
        return subprocess.run([sys.executable, me, *argv],
                              capture_output=True, text=True)

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        cre, eb, refusal = work / "cre.json", work / "eb.json", work / "no.json"
        run = subprocess.run(
            ["uv", "run", str(cre_exec), "--fixture", "--seed", "7",
             "--window", "2006-01:2020-12", "--region", "antarctic",
             "--clear-sky", "total-region", "--runtime", "selftest",
             "--receipt", str(cre)], capture_output=True, text=True)
        assert run.returncode == 0, run.stdout + run.stderr
        run = subprocess.run(
            ["uv", "run", str(eb_exec), "--fixture", "--seed", "7",
             "--window", "2006-01:2020-12", "--runtime", "selftest",
             "--receipt", str(eb)], capture_output=True, text=True)
        assert run.returncode == 0, run.stdout + run.stderr
        run = subprocess.run(
            ["uv", "run", str(cre_exec), "--fixture", "--seed", "7",
             "--window", "2006-01:2020-12", "--region", "ocean",
             "--clear-sky", "total-region", "--runtime", "selftest",
             "--receipt", str(refusal)], capture_output=True, text=True)
        assert run.returncode == 3, run.stdout + run.stderr

        # 1. The cloud radiative effect paragraph names the convention,
        #    the variable suffix and the run, cites the concept's own
        #    sources, and says what it licenses.
        out = methods([str(cre), "--out", str(work / "cre.md")])
        assert out.returncode == 0, out.stdout + out.stderr
        text = (work / "cre.md").read_text()
        body = json.loads(cre.read_text())
        assert body["run_id"] in text and body["code_sha256"] in text
        assert "total-region" in text and "clr_t" in text
        assert "cloud-free-area" in text, "the contrast sentence is missing"
        assert "## Provenance of every sentence" in text
        assert "bookkeeping.convention.variable_suffix" in text
        assert "[^convention]:" in text and "[^gotcha-clear-sky]:" in text
        assert "licenses nothing about any other run" in text
        assert "proves the chain and not the Earth" in text
        # every in-text footnote marker points at an entry the list carries
        listed = set(re.findall(r"^\[\^([A-Za-z0-9._-]+)\]:", text, re.M))
        marked = set(re.findall(r"\[\^([A-Za-z0-9._-]+)\](?!:)", text))
        assert marked and marked <= listed, (marked - listed)
        # and the markers are the concept's own source ids
        concept = package_root() / CATALOG[
            "skills/cloud-radiative-effect/scripts/cloud_radiative_effect.py"]["concept"]
        assert marked <= {entry["id"] for entry in concept_sources(concept)}

        # 2. The closure paragraph names the anchoring decade and the
        #    months shared with it; on the fixture there is no Argo
        #    receipt identity to name, and the paragraph says so in the
        #    receipt's own words rather than inventing one.
        out = methods([str(eb), "--out", str(work / "eb.md")])
        assert out.returncode == 0, out.stdout + out.stderr
        text = (work / "eb.md").read_text()
        shared = field(json.loads(eb.read_text()),
                       "bookkeeping.anchoring.months_shared_with_anchor_decade")
        assert "2005-07 through 2015-06" in text, text[:800]
        assert f"{shared} of the 180 months" in text, text[:1200]
        assert "planted Argo-shaped receipt block" in text
        assert "never recomputed" not in text, "a fixture named an Argo receipt"

        # 3. Every sentence written is filled from the paths the
        #    provenance table names, and from no others.
        for path in ("bookkeeping.anchoring.anchor.value_W_m2",
                     "bookkeeping.area_convention.rule",
                     "terms.toa_net_anomaly_trend.value"):
            assert path in text, path

        # 4. A fact from outside the receipt is refused by name.
        out = methods([str(cre), "--claim",
                       "the effect is consistent with the model ensemble"])
        assert out.returncode == 4 and "fact-not-in-receipt" in out.stdout, out.stdout
        assert "over the author's own name" in out.stdout

        # 5. A citation the concept does not carry is refused.
        out = methods([str(cre), "--cite", "ipcc-ar6"])
        assert out.returncode == 4 and "source-not-in-concept" in out.stdout, out.stdout
        out = methods([str(cre), "--cite", "convention", "--cite", "dqs"])
        assert out.returncode == 0, out.stdout + out.stderr
        assert "[^convention]:" in out.stdout and "[^dqs]:" in out.stdout
        assert "[^loeb-2024]:" not in out.stdout

        # 6. A receipt the attester does not pass, and a refusal receipt.
        tampered = work / "tampered.json"
        doctored = json.loads(cre.read_text())
        doctored["cre_net_W_m2"] = doctored["cre_net_W_m2"] + 0.5
        tampered.write_text(json.dumps(doctored, indent=2) + "\n")
        out = methods([str(tampered)])
        assert out.returncode == 4 and "attester-did-not-pass" in out.stdout, out.stdout
        out = methods([str(refusal)])
        assert out.returncode == 4 and "refused-receipt" in out.stdout, out.stdout
        assert "region-not-resolvable" in out.stdout

        # 7. A receipt of a computation this catalog does not carry.
        alien = work / "alien.json"
        other = json.loads(cre.read_text())
        other["computation"] = "references/computations/argo_ohc.py"
        alien.write_text(json.dumps(other, indent=2) + "\n")
        out = methods([str(alien)])
        assert out.returncode == 4 and "unknown-computation" in out.stdout, out.stdout

        # 8. The reference list is the concept's own source entries.
        sources = concept_sources(base / CATALOG[
            "skills/cloud-radiative-effect/scripts/cloud_radiative_effect.py"]["concept"])
        ids = [entry["id"] for entry in sources]
        assert ids[:3] == ["convention", "gotcha-clear-sky", "dataset"], ids
        assert all(entry.get("title") and entry.get("resource")
                   for entry in sources), sources

    print("methods selftest: ok "
          f"(two paragraphs written from receipt fields only; {len(REFUSALS)} "
          f"refusals enforced: {', '.join(REFUSALS)})")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("receipt", nargs="?", help="the attested receipt to write up")
    ap.add_argument("--data-root", default=None,
                    help="the stamped tree, for a data-root receipt; without it "
                         "the attester takes the data digests on the executor's "
                         "word")
    ap.add_argument("--cite", action="append", default=[],
                    help="limit the reference list to these source ids of the "
                         "concept; an id the concept does not carry is refused")
    ap.add_argument("--cited-only", action="store_true",
                    help="list only the source entries the paragraph cites, "
                         "rather than every source the concept carries")
    ap.add_argument("--claim", default=None,
                    help="a sentence to add; always refused, because a fact "
                         "that is not a receipt field or a concept source is "
                         "not this skill's to write")
    ap.add_argument("--out", help="where the methods markdown is written "
                                  "(default stdout)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if not args.receipt:
        ap.error("a receipt is required")
    try:
        return run_methods(args)
    except Refused as refused:
        print(f"METHODS REFUSED ({refused.code}): {refused.message}")
        return 4


if __name__ == "__main__":
    sys.exit(main())
