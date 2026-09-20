#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Sweep one declared parameter of an attested ASDC computation and table
the receipts, computing nothing.

The concept of a computation states its boundaries in prose, often from
a handful of runs someone made by hand ("the sign of the convention
difference reverses over the Antarctic band"). This script turns that
sentence into a measured table: it runs the sanctioned executor once per
value of one parameter the concept declares, runs the attester on every
receipt BEFORE reading a field out of it, and writes the executor's own
headline fields as a CSV, a markdown table and a JSON manifest that
names every receipt with the attester's verdict line, so a reader can
follow any cell back to a receipt that passed.

This is the atmospheric-physics port of the ocean-science sweep. The
command line, the three outputs, the five refusal codes and the exit
codes are that skill's, so a reader who knows one sweep knows both. What
differs is the catalog (the two ASDC computations this capability
wraps), the flag spelling rule (a declared parameter with an underscore,
`clear_sky`, is passed as `--clear-sky`) and one correctness change: the
attester is given `--data-root DIR` on a data-root sweep, because the
ASDC attesters take the data digests on the executor's word without it
and FAIL a data-root refusal outright.

Every cell of the table is a field of one receipt, read by the path the
catalog below records. The script fits nothing, averages nothing and
carries no expected value of its own. A run the executor refused is a
row carrying its reason code, never a skipped row, because a refusal is
part of the measurement: for the energy budget closure one real-data
window exists, the window of the one Argo receipt the data root carries,
and every other window is a row carrying `ohc-window-mismatch`. A
receipt the attester did not pass is a failed row carrying the
attester's own line, and no number from that receipt is copied into the
table.

What it refuses, each with exit 4 and a reason code, and never a
partial table:

  aggregate-across-rows   any aggregate over the rows (--aggregate):
                          a mean, an overall rate, a count of closures
                          read as a rate. Those are numbers no concept
                          owns. A capability that computes a number of
                          its own is domain expansion under ADR D of
                          the marketplace decisions and waits on the
                          ablation; a sweep is a wrap, so it stops here
                          and says which single receipt a reader may
                          quote instead. A mean across the two
                          clear-sky conventions is the one a reader
                          wants most and the one this refusal was
                          written for: the two conventions are two
                          definitions of the subtrahend and their
                          difference reverses sign between the globe
                          and the Antarctic band, so their mean is a
                          quantity of neither.
  parameter-not-declared  a parameter the concept does not declare
                          (the declared set is read from the concept's
                          Parameters in its frontmatter, not from a
                          list kept here).
  parameter-not-stated    a declared parameter that the command line
                          neither sweeps nor fixes: every run states
                          the swept parameter, its values and the fixed
                          value of every other parameter.
  mixed-method            two receipts in one sweep whose executor
                          digest (code_sha256) differs, so the table
                          would be two methods.
  mixed-input             two receipts in one sweep whose input
                          identity differs (the data root's record and
                          manifest digest, or the fixture's seed and
                          digest), so the table would be two roots.

The executor, the attester and the concept are reached at the installed
provider bundle's path, the way the wrapping skills reach them: the
installer's record (`claude plugin list --json`), or a checkout named
by NASA_DAAC_KNOWLEDGE. Nothing is copied here.

Usage:
  sweep.py --computation cloud-radiative-effect --parameter region \
      --values global,tropics,antarctic \
      --fixed window=2006-01:2020-12 --fixed clear_sky=total-region \
      --input fixture --seed 7 --runtime claude-code --out-dir DIR

  sweep.py --computation energy-budget --parameter window \
      --windows 60:60 --span 2006-01:2020-12 \
      --input data-root --data-root DIR --runtime claude-code --out-dir DIR

  sweep.py --selftest
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROVIDER_PLUGIN = "nasa-daac-knowledge"
BUNDLE = "asdc"

# One entry per computation this sweep can drive. The columns are the
# receipt fields the concept's Reference run section names, each a
# dotted path into the receipt: the table is those fields and nothing
# else. Adding a computation here adds no number; it names paths.
#
# Both executors write a rounded headline field (cre_net_W_m2,
# toa_net_W_m2) beside the full-precision term it rounds
# (terms.cre_net.value, terms.toa_net.value). Both are tabled as the
# receipt carries them; nothing here rounds or unrounds a number.
CATALOG = {
    "cloud-radiative-effect": {
        "concept": "computations/cloud-radiative-effect.md",
        "executor": "references/computations/cloud_radiative_effect.py",
        "attester": "references/attesters/cloud_radiative_effect_check.py",
        "skill": "atmospheric-physics/cloud-radiative-effect",
        "columns": [
            ("window", "bound_parameters.window"),
            ("region", "bound_parameters.region"),
            ("clear_sky", "bound_parameters.clear_sky"),
            ("months_used", "months.n_used"),
            ("months_calendar", "months.n_calendar"),
            ("cre_shortwave_W_m2", "cre_shortwave_W_m2"),
            ("cre_longwave_W_m2", "cre_longwave_W_m2"),
            ("cre_net_W_m2", "cre_net_W_m2"),
            ("cre_shortwave_value_W_m2", "terms.cre_shortwave.value"),
            ("cre_longwave_value_W_m2", "terms.cre_longwave.value"),
            ("cre_net_value_W_m2", "terms.cre_net.value"),
            ("cre_shortwave_uncertainty_W_m2", "terms.cre_shortwave.uncertainty"),
            ("cre_longwave_uncertainty_W_m2", "terms.cre_longwave.uncertainty"),
            ("cre_net_uncertainty_W_m2", "terms.cre_net.uncertainty"),
            ("residual_W_m2", "residual.value"),
            ("bar_W_m2", "verdict.bar_W_m2"),
            ("decomposition_closes", "verdict.decomposition_closes"),
            ("contrast_convention", "convention_contrast.convention"),
            ("contrast_cre_net_W_m2", "convention_contrast.cre_net"),
            ("published_distance_net_W_m2", "published_comparison.distance_W_m2.cre_net"),
        ],
    },
    "energy-budget": {
        "concept": "computations/energy-budget.md",
        "executor": "references/computations/energy_budget.py",
        "attester": "references/attesters/energy_budget_check.py",
        "skill": "atmospheric-physics/energy-budget-closure",
        "columns": [
            ("window", "bound_parameters.window"),
            ("months_used", "months.n_used"),
            ("months_calendar", "months.n_calendar"),
            ("toa_net_W_m2", "toa_net_W_m2"),
            ("toa_net_value_W_m2", "terms.toa_net.value"),
            ("toa_net_uncertainty_W_m2", "terms.toa_net.uncertainty"),
            ("ohc_0_2000_W_m2", "terms.ohc_0_2000.value"),
            ("ohc_0_2000_uncertainty_W_m2", "terms.ohc_0_2000.uncertainty"),
            ("deep_ocean_W_m2", "terms.deep_ocean.value"),
            ("non_ocean_W_m2", "terms.non_ocean.value"),
            ("ocean_side_W_m2", "ocean_side_W_m2"),
            ("residual_W_m2", "residual.value"),
            ("bar_W_m2", "verdict.bar_W_m2"),
            ("closed_within_uncertainty", "verdict.closed_within_uncertainty"),
            ("toa_net_anomaly_trend_W_m2_per_decade",
             "toa_net_anomaly_trend_W_m2_per_decade"),
            ("months_shared_with_anchor_decade",
             "bookkeeping.anchoring.months_shared_with_anchor_decade"),
            ("argo_receipt_run_id", "bookkeeping.ocean_input.receipt.run_id"),
        ],
    },
}

# Columns the sweep owns rather than the receipt: the bookkeeping that
# says whether a cell may be read at all.
STATUS_COLUMNS = ("status", "run_id", "reason_code")
UNBOUND = "unbound"
REFUSALS = ("aggregate-across-rows", "parameter-not-declared",
            "parameter-not-stated", "mixed-method", "mixed-input")
CONVENTION_PARAMETER = "clear_sky"
CLEAR_SKY_GOTCHA = f"knowledge/{BUNDLE}/gotchas/ebaf-clear-sky-definitions.md"
CLEAR_SKY_CONVENTION = f"knowledge/{BUNDLE}/conventions/ceres-clear-sky-conventions.md"


# ---- refusing

def refuse(code: str, message: str) -> int:
    print(f"SWEEP REFUSED ({code}): {message}")
    return 4


# ---- the installed bundle

def provider_root() -> Path:
    """The installed provider plugin's root, from the installer's record."""
    override = os.environ.get("NASA_DAAC_KNOWLEDGE")
    if override:
        return Path(override).expanduser().resolve()
    claude = shutil.which("claude")
    if claude is None:
        sys.exit("no `claude` on PATH to read the installed-plugin record; "
                 "set NASA_DAAC_KNOWLEDGE to a checkout of the provider "
                 "repository instead")
    rec = subprocess.run([claude, "plugin", "list", "--json"],
                         capture_output=True, text=True)
    if rec.returncode != 0:
        sys.exit(f"`claude plugin list --json` failed: {rec.stderr.strip()}")
    for entry in json.loads(rec.stdout):
        if entry.get("id", "").split("@")[0] != PROVIDER_PLUGIN:
            continue
        if not entry.get("enabled", True) or entry.get("errors"):
            sys.exit(f"{entry['id']} is installed but not usable: "
                     f"{entry.get('errors') or 'disabled'}")
        return Path(entry["installPath"])
    sys.exit(f"{PROVIDER_PLUGIN} is not installed; it arrives with this "
             "plugin's dependencies (`claude plugin install "
             "atmospheric-physics@open-science-pillars`), or set "
             "NASA_DAAC_KNOWLEDGE to a checkout of the provider repository")


def bundle_paths(computation: str):
    """The concept, the executor and the attester at the installed
    bundle's path; nothing is copied into this repository."""
    spec = CATALOG[computation]
    base = provider_root() / "knowledge" / BUNDLE
    paths = {k: base / spec[k] for k in ("concept", "executor", "attester")}
    for name, p in paths.items():
        if not p.is_file():
            sys.exit(f"the provider bundle carries no {name} for {computation} "
                     f"at {p}; the sweep needs {PROVIDER_PLUGIN} at a release "
                     "that ships it")
    return paths


def declared_parameters(concept: Path):
    """The parameter names the concept declares, read from its
    frontmatter's Parameters block rather than kept in a list here."""
    text = concept.read_text(encoding="utf-8")
    if not text.startswith("---"):
        sys.exit(f"{concept} carries no frontmatter to read parameters from")
    front = text.split("---", 2)[1]
    names, inside = [], False
    for line in front.splitlines():
        if re.match(r"^parameters:\s*$", line):
            inside = True
            continue
        if inside:
            if not line.startswith((" ", "\t")) and line.strip():
                break
            found = re.search(r"\bname:\s*['\"]?([A-Za-z0-9_-]+)", line)
            if found:
                names.append(found.group(1))
    if not names:
        sys.exit(f"{concept} declares no parameters; a sweep needs one to sweep")
    return names


def flag(parameter: str) -> str:
    """The command-line flag for a declared parameter. The executors
    spell a parameter's flag with hyphens where the concept declares it
    with underscores (`clear_sky` is bound as `--clear-sky`), so the
    flag is derived from the declared name and never kept as a list."""
    return "--" + parameter.replace("_", "-")


# ---- the values swept

def month_index(label: str) -> int:
    y, m = label.split("-")
    return int(y) * 12 + int(m) - 1


def month_label(index: int) -> str:
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def windows(span: str, length: int, step: int):
    """Every window of `length` months stepping `step` months through
    `span`. Calendar arithmetic on the stated rule, so the values are
    explicit in the manifest and in every row; no science number is
    formed here."""
    first, last = span.split(":")
    out, start = [], month_index(first)
    while start + length - 1 <= month_index(last):
        out.append(f"{month_label(start)}:{month_label(start + length - 1)}")
        start += step
    if not out:
        sys.exit(f"no window of {length} months fits in {span}")
    return out


# ---- running, attesting, reading

def run_executor(executor: Path, parameter: str, value: str, fixed: dict,
                 args, receipt: Path) -> subprocess.CompletedProcess:
    """One run of the sanctioned executor with every declared parameter
    stated: the swept one at this value, the others at their fixed
    values. Exit 3 is the executor's refusal and is a row, not a stop."""
    cmd = ["uv", "run", str(executor), flag(parameter), value,
           "--runtime", args.runtime, "--receipt", str(receipt)]
    for name, bound in fixed.items():
        if bound != UNBOUND:
            cmd += [flag(name), bound]
    if args.input == "fixture":
        cmd += ["--fixture", "--seed", str(args.seed)]
    else:
        cmd += ["--data-root", str(args.data_root)]
    if args.runtime_version:
        cmd += ["--runtime-version", args.runtime_version]
    if args.capability_root:
        cmd += ["--capability-root", str(args.capability_root)]
    return subprocess.run(cmd, capture_output=True, text=True)


def attest(attester: Path, receipt: Path, attestation: Path, data_root=None):
    """The attester on this receipt, before any field of it is read.

    A data-root receipt is attested with --data-root naming the tree:
    without it the ASDC attesters take the data digests on the
    executor's word, and a data-root refusal is not reproduced at all
    and FAILS. Returns (passed, the attester's own verdict line)."""
    cmd = ["uv", "run", str(attester), str(receipt), "--out", str(attestation)]
    if data_root is not None:
        cmd += ["--data-root", str(data_root)]
    run = subprocess.run(cmd, capture_output=True, text=True)
    text = (run.stdout or "").strip() or (run.stderr or "").strip()
    lines = [line for line in text.splitlines() if line.strip()]
    line = lines[-1] if lines else "the attester printed nothing"
    return run.returncode == 0 and line.startswith("PASS"), line


def field(receipt: dict, path: str):
    """One receipt field by its dotted path, or None where the receipt
    does not carry it (a refusal receipt carries no term, and a fixture
    receipt carries no Argo receipt identity)."""
    node = receipt
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def method_identity(receipt: dict) -> str:
    return receipt.get("code_sha256") or ""


def input_identity(receipt: dict) -> dict:
    """What makes a table one root: the stamped record and its manifest
    digest for a data root, the seed and digest for a fixture."""
    data = receipt.get("data") or {}
    if data.get("mode") == "data-root":
        return {"mode": "data-root", "record": data.get("record"),
                "manifest_sha256": data.get("manifest_sha256")}
    return {"mode": data.get("mode"), "seed": data.get("seed"),
            "digest": data.get("digest"),
            "generator_sha256": data.get("generator_sha256")}


def one_method(rows):
    """(code, message) where two rows carry different methods or
    different inputs, else None. A sweep is one method on one root."""
    seen_method, seen_input = {}, {}
    for row in rows:
        receipt = row.get("receipt_body")
        if receipt is None:
            continue
        seen_method.setdefault(method_identity(receipt), row["value"])
        key = json.dumps(input_identity(receipt), sort_keys=True)
        seen_input.setdefault(key, row["value"])
    if len(seen_method) > 1:
        first, second = list(seen_method.items())[:2]
        return ("mixed-method",
                f"the receipts in this sweep were produced by two executors: "
                f"{first[0]} at {first[1]} and {second[0]} at {second[1]}; a "
                "table is one method, and these rows are not comparable")
    if len(seen_input) > 1:
        first, second = list(seen_input.items())[:2]
        return ("mixed-input",
                f"the receipts in this sweep read two different inputs: "
                f"{first[0]} at {first[1]} and {second[0]} at {second[1]}; a "
                "table is one root, and these rows are not comparable")
    return None


def build_row(value: str, receipt_path: Path, attestation_path: Path,
              exit_code: int, attester: Path, columns, data_root=None):
    """One row: the attester first, then the receipt's own fields. A
    receipt the attester did not pass is a failed row carrying the
    attester's line and no number."""
    row = {"value": value, "receipt": str(receipt_path), "cells": {},
           "attested": False, "attestation": None, "run_id": None,
           "status": "not-attested", "reason_code": None,
           "receipt_body": None, "executor_exit": exit_code}
    if not receipt_path.is_file():
        row["attestation"] = f"the executor wrote no receipt (exit {exit_code})"
        return row
    passed, line = attest(attester, receipt_path, attestation_path, data_root)
    row["attestation"] = line
    row["attested"] = passed
    if not passed:
        return row
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    row["receipt_body"] = receipt
    row["run_id"] = receipt.get("run_id")
    row["reason_code"] = receipt.get("reason_code")
    row["status"] = "refused" if receipt.get("refused") else "computed"
    row["cells"] = {name: field(receipt, path) for name, path in columns}
    return row


# ---- the table

def show(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def show_md(value) -> str:
    if isinstance(value, float):
        return f"{value:+.4f}" if value else "0.0000"
    return show(value)


def headers(columns):
    return list(STATUS_COLUMNS) + [name for name, _ in columns]


def row_cells(row, columns):
    out = {"status": row["status"], "run_id": row["run_id"] or "",
           "reason_code": row["reason_code"] or ""}
    for name, _ in columns:
        out[name] = row["cells"].get(name)
    return out


def write_csv(path: Path, rows, columns) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers(columns))
        for row in rows:
            cells = row_cells(row, columns)
            writer.writerow([show(cells[name]) for name in headers(columns)])


def write_markdown(path: Path, rows, columns, head: dict) -> None:
    names = headers(columns)
    lines = [f"# {head['computation']}: {head['parameter']} swept over "
             f"{len(rows)} values", ""]
    lines += [head["provenance"], "",
              "| " + " | ".join(names) + " |",
              "| " + " | ".join("---" for _ in names) + " |"]
    for row in rows:
        cells = row_cells(row, columns)
        lines.append("| " + " | ".join(show_md(cells[name]) for name in names) + " |")
    lines += ["", head["reading"], ""]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(path: Path, rows, columns, head: dict) -> None:
    doc = dict(head)
    doc["columns"] = [{"name": name, "receipt_field": field_path}
                      for name, field_path in columns]
    doc["rows"] = [{
        "value": row["value"],
        "status": row["status"],
        "run_id": row["run_id"],
        "reason_code": row["reason_code"],
        "receipt": row["receipt"],
        "attested": row["attested"],
        "attestation": row["attestation"],
        "cells": row["cells"],
    } for row in rows]
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


# ---- the sweep

def aggregate_refusal(args, spec, across_conventions: bool) -> int:
    """The aggregate a reader asks for first, refused, with the reason
    that is also the answer to give. Where the rows would span both
    clear-sky conventions the refusal leads with that, because a mean
    across the two is the aggregate this refusal was written for."""
    concept = f"knowledge/{BUNDLE}/{spec['concept']}"
    message = (
        f"this sweep will not emit an aggregate across its rows, and what was "
        f"asked for is one: {args.aggregate}. Each row is a receipt the "
        f"attester passed, and an aggregate over the rows is a number no "
        f"concept owns: {concept} owns the terms of one run over one window, "
        f"one region and one bound convention, and nothing in the bundle owns "
        f"a mean of them. Computing one here would be a number of this "
        f"capability's own, which is domain expansion under ADR D of the "
        f"marketplace decisions and waits on the ablation. Quote one row "
        f"instead: its receipt carries the terms, their uncertainties, the "
        f"months used and the verdict, and its run id is in the manifest.")
    if across_conventions:
        message = (
            f"this sweep will not average across the clear-sky conventions, "
            f"and what was asked for is that: {args.aggregate}. The rows of "
            f"this sweep are of two conventions, and the two are two "
            f"definitions of the flux that was subtracted, not two "
            f"measurements of one quantity: {CLEAR_SKY_CONVENTION} owns what "
            f"each one is and {CLEAR_SKY_GOTCHA} owns the published size of "
            f"the adjustment between them. Their difference does not even "
            f"keep its sign from one region to another, as {concept} records "
            f"over the Antarctic band, so no single number moves a result "
            f"from one convention to the other and their mean is a quantity "
            f"of neither. Report both conventions' rows side by side, say "
            f"which convention the question is of, and quote that row: its "
            f"receipt carries the terms, their uncertainties, the months used "
            f"and the other convention's terms in its contrast block, and its "
            f"run id is in the manifest. An aggregate across rows would also "
            f"be a number no concept owns, which is domain expansion under "
            f"ADR D of the marketplace decisions and waits on the ablation.")
    return refuse("aggregate-across-rows", message)


def sweep(args) -> int:
    spec = CATALOG[args.computation]
    paths = bundle_paths(args.computation)
    declared = declared_parameters(paths["concept"])

    if args.aggregate:
        return aggregate_refusal(
            args, spec,
            args.parameter == CONVENTION_PARAMETER
            and CONVENTION_PARAMETER in declared)
    if args.parameter not in declared:
        return refuse(
            "parameter-not-declared",
            f"{args.parameter} is not a parameter "
            f"knowledge/{BUNDLE}/{spec['concept']} declares; it declares "
            f"{', '.join(declared)}. Sweeping execution plumbing (a seed, an "
            "output path) or an invented knob produces a table of runs no "
            "concept licenses.")
    fixed = {}
    for item in args.fixed:
        if "=" not in item:
            return refuse("parameter-not-stated",
                          f"--fixed takes NAME=VALUE, or NAME={UNBOUND} for a "
                          f"parameter left unbound; got {item}")
        name, bound = item.split("=", 1)
        if name not in declared:
            return refuse("parameter-not-declared",
                          f"{name} is not a parameter "
                          f"knowledge/{BUNDLE}/{spec['concept']} declares; it "
                          f"declares {', '.join(declared)}")
        if name == args.parameter:
            return refuse("parameter-not-stated",
                          f"{name} is the swept parameter and cannot also be "
                          "fixed")
        fixed[name] = bound
    unstated = [name for name in declared
                if name != args.parameter and name not in fixed]
    if unstated:
        return refuse(
            "parameter-not-stated",
            f"every declared parameter is stated on every run: "
            f"{', '.join(unstated)} is neither swept nor fixed. State it with "
            f"--fixed {unstated[0]}=VALUE, or --fixed {unstated[0]}={UNBOUND} "
            "to leave it unbound on every run, so the table says what it was. "
            "Every parameter both ASDC computations declare is required, so "
            f"{UNBOUND} makes the executor reject the run rather than produce "
            "a receipt.")

    if args.values:
        values = [v for v in (item.strip() for item in args.values.split(",")) if v]
    else:
        length, step = (int(part) for part in args.windows.split(":"))
        values = windows(args.span, length, step)
    if not values:
        return refuse("parameter-not-stated",
                      "the sweep has no values; state them with --values or "
                      "--windows LENGTH:STEP with --span FIRST:LAST")

    out_dir = Path(args.out_dir).expanduser().resolve()
    receipts_dir = out_dir / "receipts"
    receipts_dir.mkdir(parents=True, exist_ok=True)
    tree = args.data_root if args.input == "data-root" else None

    rows = []
    for index, value in enumerate(values):
        stem = f"{index:03d}-{re.sub(r'[^A-Za-z0-9._-]', '_', value)}"
        receipt = receipts_dir / f"{stem}.json"
        attestation = receipts_dir / f"{stem}-attestation.json"
        run = run_executor(paths["executor"], args.parameter, value, fixed,
                           args, receipt)
        if run.returncode not in (0, 3):
            print((run.stderr or run.stdout or "").strip())
            return refuse("executor-failed",
                          f"the executor exited {run.returncode} at "
                          f"{args.parameter} {value}; that is neither a result "
                          "nor a refusal, so the sweep stops rather than "
                          "tabling a run it cannot read")
        rows.append(build_row(value, receipt, attestation, run.returncode,
                              paths["attester"], spec["columns"], tree))

    mixed = one_method(rows)
    if mixed:
        return refuse(*mixed)

    attested = [row for row in rows if row["attested"]]
    body = attested[0]["receipt_body"] if attested else {}
    head = {
        "sweep": "one declared parameter swept; every cell is a field of a "
                 "receipt this sweep attested, and no aggregate across rows "
                 "is computed here",
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "computation": args.computation,
        "concept": f"knowledge/{BUNDLE}/{spec['concept']}",
        "executor": f"knowledge/{BUNDLE}/{spec['executor']}",
        "attester": f"knowledge/{BUNDLE}/{spec['attester']}",
        "wrapping_skill": spec["skill"],
        "parameter": args.parameter,
        "values": values,
        "values_rule": (f"--windows {args.windows} --span {args.span}"
                        if args.windows else "--values, stated one by one"),
        "fixed": fixed,
        "runtime": args.runtime,
        "code_sha256": method_identity(body),
        "input": input_identity(body),
        "refusals_enforced": list(REFUSALS),
        "not_computed": "the mean of any column, a mean across the two "
                        "clear-sky conventions above all, and any rate read "
                        "off the count of closed rows: no concept owns them",
    }
    head["provenance"] = (
        f"Every cell is a field of a receipt the attester passed. Executor "
        f"{head['executor']} at {head['code_sha256']}; attester "
        f"{head['attester']}; concept {head['concept']}; input "
        f"{json.dumps(head['input'], sort_keys=True)}; runtime "
        f"{args.runtime}. Floats are shown to four decimals; the CSV and the "
        f"receipts carry them as the receipt does, the rounded headline field "
        f"beside the full-precision term it rounds.")
    head["reading"] = (
        "A refused row is a measurement: the executor wrote a refusal receipt "
        "with that reason code and no number. Read one row at a time, with "
        f"the caveats {head['concept']} states beside it. This table licenses "
        "no statement about the rows together, and this sweep refuses to "
        "compute one.")

    write_csv(out_dir / "sweep.csv", rows, spec["columns"])
    write_markdown(out_dir / "sweep.md", rows, spec["columns"], head)
    write_manifest(out_dir / "sweep.json", rows, spec["columns"], head)

    computed = sum(1 for row in rows if row["status"] == "computed")
    refused = sum(1 for row in rows if row["status"] == "refused")
    failed = [row for row in rows if not row["attested"]]
    print((out_dir / "sweep.md").read_text(encoding="utf-8"))
    print(f"sweep: {len(rows)} rows over {args.parameter}, {computed} computed, "
          f"{refused} refused by the executor, {len(failed)} not attested; "
          f"{out_dir}/sweep.csv, sweep.md, sweep.json")
    for row in failed:
        print(f"  not attested at {args.parameter} {row['value']}: "
              f"{row['attestation']}")
    return 1 if failed else 0


# ---- selftest

def selftest() -> int:
    """Every refusal, on the executors' synthetic fixtures."""
    cre_paths = bundle_paths("cloud-radiative-effect")
    cre_columns = CATALOG["cloud-radiative-effect"]["columns"]
    eb_columns = CATALOG["energy-budget"]["columns"]
    base = ["--input", "fixture", "--seed", "7", "--runtime", "selftest"]

    def run_sweep(computation, extra, work, seed="7"):
        cmd = [sys.executable, str(Path(__file__).resolve()),
               "--computation", computation, "--input", "fixture",
               "--seed", seed, "--runtime", "selftest",
               "--out-dir", str(work), *extra]
        return subprocess.run(cmd, capture_output=True, text=True)

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)

        # 1. The sweep the convention gotcha describes in words: the
        #    same window and region on both clear-sky conventions, two
        #    rows, each a receipt the attester passed, and the contrast
        #    block of each naming the other.
        done = run_sweep("cloud-radiative-effect",
                         ["--parameter", "clear_sky",
                          "--values", "total-region,cloud-free-area",
                          "--fixed", "window=2006-01:2020-12",
                          "--fixed", "region=antarctic"], work / "conventions")
        assert done.returncode == 0, done.stdout + done.stderr
        doc = json.loads((work / "conventions" / "sweep.json").read_text())
        assert [row["value"] for row in doc["rows"]] == ["total-region",
                                                         "cloud-free-area"]
        assert all(row["attested"] for row in doc["rows"]), doc["rows"]
        assert all(row["status"] == "computed" for row in doc["rows"])
        assert doc["rows"][0]["cells"]["contrast_convention"] == "cloud-free-area"
        assert doc["rows"][1]["cells"]["contrast_convention"] == "total-region"
        for row in doc["rows"]:
            receipt = json.loads(Path(row["receipt"]).read_text())
            for name, path in cre_columns:
                assert row["cells"][name] == field(receipt, path), (name, row["value"])
            assert row["run_id"] == receipt["run_id"]
        assert (work / "conventions" / "sweep.csv").is_file()
        assert "| status |" in (work / "conventions" / "sweep.md").read_text()
        assert doc["fixed"] == {"window": "2006-01:2020-12",
                                "region": "antarctic"}

        # 2. A region sweep, the other shape the concept's table takes.
        regions = "global,tropics,arctic,antarctic"
        done = run_sweep("cloud-radiative-effect",
                         ["--parameter", "region", "--values", regions,
                          "--fixed", "window=2006-01:2020-12",
                          "--fixed", "clear_sky=total-region"], work / "regions")
        assert done.returncode == 0, done.stdout + done.stderr
        doc = json.loads((work / "regions" / "sweep.json").read_text())
        assert [row["value"] for row in doc["rows"]] == regions.split(",")
        assert all(row["attested"] for row in doc["rows"])

        # 3. A region the computation does not resolve is a row carrying
        #    its reason code and no number, never a skipped row.
        done = run_sweep("cloud-radiative-effect",
                         ["--parameter", "region", "--values", "global,ocean",
                          "--fixed", "window=2006-01:2020-12",
                          "--fixed", "clear_sky=total-region"], work / "refused")
        assert done.returncode == 0, done.stdout + done.stderr
        doc = json.loads((work / "refused" / "sweep.json").read_text())
        assert [row["status"] for row in doc["rows"]] == ["computed", "refused"]
        assert doc["rows"][1]["reason_code"] == "region-not-resolvable"
        assert doc["rows"][1]["cells"]["cre_net_W_m2"] is None
        assert "PASS refusal" in doc["rows"][1]["attestation"]

        # 4. The energy budget sweeps its one declared parameter, and on
        #    the fixture every window inside the record computes; the
        #    Argo receipt identity column is empty because the fixture
        #    plants an Argo-shaped block and not a receipt.
        #    The fixture plants a level and a trend the attester checks
        #    the recovery of, and that check is stated over a window of
        #    the reference run's length, so the fixture windows swept
        #    here are 180 months like the reference run's.
        done = run_sweep("energy-budget",
                         ["--parameter", "window", "--windows", "180:60",
                          "--span", "2000-03:2026-05"], work / "budget")
        assert done.returncode == 0, done.stdout + done.stderr
        doc = json.loads((work / "budget" / "sweep.json").read_text())
        assert [row["value"] for row in doc["rows"]] == ["2000-03:2015-02",
                                                          "2005-03:2020-02",
                                                          "2010-03:2025-02"]
        assert all(row["attested"] for row in doc["rows"])
        assert doc["values_rule"] == "--windows 180:60 --span 2000-03:2026-05"
        assert doc["rows"][0]["cells"]["argo_receipt_run_id"] is None
        for row in doc["rows"]:
            receipt = json.loads(Path(row["receipt"]).read_text())
            for name, path in eb_columns:
                assert row["cells"][name] == field(receipt, path), (name, row["value"])

        # 5. A window the record does not cover is a row with its code.
        done = run_sweep("energy-budget",
                         ["--parameter", "window",
                          "--values", "2006-01:2020-12,1998-01:2005-12"],
                         work / "outside")
        assert done.returncode == 0, done.stdout + done.stderr
        doc = json.loads((work / "outside" / "sweep.json").read_text())
        assert [row["status"] for row in doc["rows"]] == ["computed", "refused"]
        assert doc["rows"][1]["reason_code"] == "window-outside-record"
        assert doc["rows"][1]["cells"]["toa_net_W_m2"] is None

        # 6. The aggregate a reader asks for first is refused, and over a
        #    sweep of the two conventions the refusal is the convention
        #    one: it names the gotcha and the reversal, and says to
        #    report both rows.
        out = run_sweep("cloud-radiative-effect",
                        ["--parameter", "clear_sky",
                         "--values", "total-region,cloud-free-area",
                         "--fixed", "window=2006-01:2020-12",
                         "--fixed", "region=global",
                         "--aggregate", "one global net cloud radiative effect"],
                        work / "agg-convention")
        assert out.returncode == 4 and "aggregate-across-rows" in out.stdout, out.stdout
        assert "will not average across the clear-sky conventions" in out.stdout
        assert CLEAR_SKY_GOTCHA in out.stdout and "Antarctic" in out.stdout
        assert "ADR D" in out.stdout
        assert not (work / "agg-convention" / "sweep.csv").is_file()
        out = run_sweep("energy-budget",
                        ["--parameter", "window",
                         "--values", "2006-01:2010-12,2011-01:2015-12",
                         "--aggregate", "the mean residual over the windows"],
                        work / "agg-window")
        assert out.returncode == 4 and "aggregate-across-rows" in out.stdout, out.stdout
        assert "ADR D" in out.stdout and "Quote one row instead" in out.stdout

        # 7. A parameter the concept does not declare, swept or fixed.
        out = run_sweep("cloud-radiative-effect",
                        ["--parameter", "seed", "--values", "7,8",
                         "--fixed", "window=2006-01:2020-12",
                         "--fixed", "region=global",
                         "--fixed", "clear_sky=total-region"], work / "undeclared")
        assert out.returncode == 4 and "parameter-not-declared" in out.stdout, out.stdout
        out = run_sweep("cloud-radiative-effect",
                        ["--parameter", "region", "--values", "global,tropics",
                         "--fixed", "window=2006-01:2020-12",
                         "--fixed", "clear_sky=total-region",
                         "--fixed", "seed=7"], work / "undeclared2")
        assert out.returncode == 4 and "parameter-not-declared" in out.stdout, out.stdout

        # 8. A declared parameter the command line leaves unstated.
        out = run_sweep("cloud-radiative-effect",
                        ["--parameter", "region", "--values", "global,tropics",
                         "--fixed", "window=2006-01:2020-12"], work / "unstated")
        assert out.returncode == 4 and "parameter-not-stated" in out.stdout, out.stdout
        assert "clear_sky" in out.stdout

        # 9. Two methods or two inputs in one table, on real receipts:
        #    the same region at two fixture seeds gives two inputs, and a
        #    receipt whose executor digest differs gives two methods.
        seven = run_sweep("cloud-radiative-effect",
                          ["--parameter", "region", "--values", "global",
                           "--fixed", "window=2006-01:2020-12",
                           "--fixed", "clear_sky=total-region"], work / "seed7")
        assert seven.returncode == 0, seven.stdout + seven.stderr
        eight = run_sweep("cloud-radiative-effect",
                          ["--parameter", "region", "--values", "global",
                           "--fixed", "window=2006-01:2020-12",
                           "--fixed", "clear_sky=total-region"], work / "seed8",
                          seed="8")
        assert eight.returncode == 0, eight.stdout + eight.stderr

        def only_receipt(out_dir: Path):
            # by the manifest, never by a glob: the receipts directory
            # holds each attestation beside its receipt, and the order a
            # glob returns them in is the filesystem's business
            manifest = json.loads((out_dir / "sweep.json").read_text())
            return json.loads(Path(manifest["rows"][0]["receipt"]).read_text())

        first = only_receipt(work / "seed7")
        second = only_receipt(work / "seed8")
        assert first["data"]["seed"] == 7 and second["data"]["seed"] == 8
        mixed = one_method([{"value": "seed 7", "receipt_body": first},
                            {"value": "seed 8", "receipt_body": second}])
        assert mixed and mixed[0] == "mixed-input", mixed
        other = json.loads(json.dumps(first))
        other["code_sha256"] = "sha256:" + "0" * 64
        mixed = one_method([{"value": "a", "receipt_body": first},
                            {"value": "b", "receipt_body": other}])
        assert mixed and mixed[0] == "mixed-method", mixed
        assert one_method([{"value": "a", "receipt_body": first}]) is None

        # 10. A receipt the attester does not pass is a failed row with
        #     the attester's own line and no number in it.
        tampered = work / "tampered.json"
        doctored = json.loads(json.dumps(first))
        doctored["cre_net_W_m2"] = doctored["cre_net_W_m2"] + 0.5
        tampered.write_text(json.dumps(doctored, indent=2) + "\n")
        row = build_row("global", tampered, work / "tampered-att.json", 0,
                        cre_paths["attester"], cre_columns)
        assert row["attested"] is False and row["status"] == "not-attested", row
        assert row["cells"] == {} and row["run_id"] is None
        assert row["attestation"].startswith("FAIL"), row["attestation"]

        # 11. The window rule expands to explicit values, the flag
        #     spelling comes from the declared name, and the declared
        #     sets come from the concepts and not from here.
        assert windows("2005-01:2010-12", 24, 12) == [
            "2005-01:2006-12", "2006-01:2007-12", "2007-01:2008-12",
            "2008-01:2009-12", "2009-01:2010-12"]
        assert flag("clear_sky") == "--clear-sky" and flag("window") == "--window"
        assert declared_parameters(cre_paths["concept"]) == [
            "window", "region", "clear_sky"]
        assert declared_parameters(
            bundle_paths("energy-budget")["concept"]) == ["window"]

    print("sweep selftest: ok "
          f"({len(REFUSALS)} refusals exercised: {', '.join(REFUSALS)}; "
          "the aggregate across the two clear-sky conventions is refused by "
          "name; a tampered receipt is a failed row, not a number)")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--computation", choices=sorted(CATALOG),
                    help="the attested computation to sweep")
    ap.add_argument("--parameter", help="the declared parameter swept")
    ap.add_argument("--values", help="the values, comma separated, stated explicitly")
    ap.add_argument("--windows", help="LENGTH:STEP in months, expanded over --span "
                                      "into explicit values")
    ap.add_argument("--span", help="FIRST:LAST as YYYY-MM:YYYY-MM, with --windows")
    ap.add_argument("--fixed", action="append", default=[],
                    help=f"NAME=VALUE for another declared parameter, or "
                         f"NAME={UNBOUND} to leave it unbound; every declared "
                         "parameter is stated on every run")
    ap.add_argument("--input", choices=("fixture", "data-root"),
                    help="the executor's input, one for the whole sweep")
    ap.add_argument("--data-root", type=Path,
                    help="the stamped tree, with --input data-root; it is "
                         "given to the attester too, so the digests are "
                         "verified against the tree and a refusal is "
                         "reproduced from it")
    ap.add_argument("--seed", type=int, default=7, help="fixture seed (default 7)")
    ap.add_argument("--runtime", help="the runtime that ran this, passed to every run")
    ap.add_argument("--runtime-version", default=None)
    ap.add_argument("--capability-root", type=Path, default=None,
                    help="the package tree these runs are evidence for")
    ap.add_argument("--out-dir", help="where sweep.csv, sweep.md, sweep.json and "
                                      "the receipts go")
    ap.add_argument("--aggregate", default=None,
                    help="an aggregate across the rows; always refused, and the "
                         "refusal says which receipt to quote instead")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    missing = [name for name in ("computation", "parameter", "input", "runtime",
                                 "out_dir") if getattr(args, name) is None]
    if missing:
        ap.error("these are required for a sweep: "
                 + ", ".join("--" + name.replace("_", "-") for name in missing))
    if bool(args.values) == bool(args.windows):
        ap.error("state the values with --values, or a window rule with "
                 "--windows LENGTH:STEP and --span FIRST:LAST, not both")
    if args.windows and not args.span:
        ap.error("--windows needs --span FIRST:LAST")
    if (args.input == "data-root") != bool(args.data_root):
        ap.error("--input data-root needs --data-root DIR, and --data-root is "
                 "not read with --input fixture")
    return sweep(args)


if __name__ == "__main__":
    sys.exit(main())
