#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Golden for the three receipt skills: sweep, receipt-figures and
methods, exercised offline against the expectations committed beside
this file.

Nothing scientific is reimplemented here and nothing is downloaded. The
three skills drive the sanctioned executors and attesters in the ASDC
bundle (knowledge/asdc/references/, under the contracts
knowledge/asdc/computations/cloud-radiative-effect.md and
knowledge/asdc/computations/energy-budget.md) on those executors'
synthetic fixtures, which are generated at run time from the seed the
expectations file names, so this golden is headless and offline with no
NASA host reachable. The bundle root is resolved by each skill's script
the way the wrapping skills resolve it: NASA_DAAC_KNOWLEDGE names a
checkout of the provider repository, else the installer's record.

What is checked, in order:

  1. each script's own selftest, which exercises every refusal it
     enforces on the executors' fixtures;
  2. the convention sweep: the Antarctic band on both clear-sky
     conventions, every row attested, every cell equal to the cell
     recorded in verification/fixtures/receipt-skills-fixture.json, and
     the sign of the convention difference as the rows carry it;
  3. the region sweep: a resolvable region and one the computation
     refuses, the refused row carrying its reason code and no number;
  4. the closure sweep: one window inside the record and one outside,
     the same way;
  5. the aggregate a reader wants most, one global cloud radiative
     effect across the two conventions, refused with its reason code,
     naming the clear-sky gotcha by bundle path, and leaving no partial
     table;
  6. the three figures, drawn from receipts those sweeps attested, each
     array's sha256 equal to the recorded one, with the map mode and a
     restated wrong digest both refused and no file written;
  7. the two methods paragraphs, every sentence filled from the receipt
     fields the recorded provenance names, the recorded facts present,
     the reference list the concept's own source ids, and a fact from
     outside the receipt refused.

Exit 0 only when all of it holds.

  uv run verification/receipt_skills.py
  uv run verification/receipt_skills.py --measure   # rewrite the expectations
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGE_ROOT = HERE.parent
SWEEP = PACKAGE_ROOT / "skills" / "sweep" / "scripts" / "sweep.py"
FIGURE = PACKAGE_ROOT / "skills" / "receipt-figures" / "scripts" / "receipt_figure.py"
METHODS = PACKAGE_ROOT / "skills" / "methods" / "scripts" / "methods.py"
EXPECTATIONS = HERE / "fixtures" / "receipt-skills-fixture.json"
TOLERANCE = 1e-9
RUNTIME = "golden"
SEED = 7
CLEAR_SKY_GOTCHA = "knowledge/asdc/gotchas/ebaf-clear-sky-definitions.md"

SWEEPS = {
    "conventions": {
        "computation": "cloud-radiative-effect",
        "parameter": "clear_sky",
        "values": "total-region,cloud-free-area",
        "fixed": {"window": "2006-01:2020-12", "region": "antarctic"},
        "why": "the Antarctic band on both clear-sky conventions, the table "
               "the bundle's clear-sky gotcha describes in words",
    },
    "regions": {
        "computation": "cloud-radiative-effect",
        "parameter": "region",
        "values": "global,antarctic,ocean",
        "fixed": {"window": "2006-01:2020-12", "clear_sky": "total-region"},
        "why": "two regions the computation resolves and one it refuses, so "
               "the refused row is part of the table",
    },
    "windows": {
        "computation": "energy-budget",
        "parameter": "window",
        "values": "2006-01:2020-12,1998-01:2005-12",
        "fixed": {},
        "why": "one window inside the radiation record and one outside it",
    },
}

FIGURES = {
    "contrast": {"sweep": "conventions", "row": 0, "mode": "contrast",
                 "attester": "cloud_radiative_effect_check", "extra": []},
    "cre-series": {"sweep": "conventions", "row": 0, "mode": "cre-series",
                   "attester": "cloud_radiative_effect_check",
                   "extra": ["--band", "net"]},
    "budget": {"sweep": "windows", "row": 0, "mode": "budget",
               "attester": "energy_budget_check", "extra": []},
}

METHODS_RUNS = {
    "cloud-radiative-effect": {"sweep": "conventions", "row": 0},
    "energy-budget": {"sweep": "windows", "row": 0},
}


def fail(message: str) -> int:
    print(f"receipt-skills golden: {message}")
    return 1


class Failed(Exception):
    pass


def check(condition, message: str) -> None:
    if not condition:
        raise Failed(message)


def same(got, want) -> bool:
    if isinstance(want, float) or isinstance(got, float):
        if got is None or want is None:
            return got is want
        return abs(float(got) - float(want)) <= TOLERANCE * max(1.0, abs(float(want)))
    return got == want


def run(script: Path, args):
    return subprocess.run(["uv", "run", str(script), *args],
                          capture_output=True, text=True, cwd=PACKAGE_ROOT)


def sweep_args(spec, out_dir: Path):
    return ["--computation", spec["computation"],
            "--parameter", spec["parameter"],
            "--values", spec["values"],
            *[f"--fixed={name}={value}" for name, value in spec["fixed"].items()],
            "--input", "fixture", "--seed", str(SEED),
            "--runtime", RUNTIME, "--capability-root", str(PACKAGE_ROOT),
            "--out-dir", str(out_dir)]


def do_sweeps(work: Path):
    """Every sweep this golden drives, run once and kept for the figures
    and the paragraphs, so a figure is of a receipt this golden itself
    attested through the sweep."""
    done = {}
    for name, spec in SWEEPS.items():
        out_dir = work / name
        got = run(SWEEP, sweep_args(spec, out_dir))
        check(got.returncode == 0,
              f"the {name} sweep exited {got.returncode}; every row of it "
              f"attests, so anything but 0 is a finding\n"
              f"{(got.stdout or '').strip()}\n{(got.stderr or '').strip()}")
        done[name] = json.loads((out_dir / "sweep.json").read_text(encoding="utf-8"))
    return done


def measure(work: Path) -> dict:
    """Record what the three skills produce on the fixtures today. The
    numbers are receipt fields and the digests are of arrays the figures
    drew; nothing here is asserted by hand."""
    done = do_sweeps(work)
    doc = {
        "about": [
            "What the three receipt skills produce on the ASDC executors' synthetic",
            "fixtures at seed 7, read by verification/receipt_skills.py. Every cell",
            "below is a field of a receipt the bundle's attester passed, copied by the",
            "receipt field path the sweep manifest records beside each column; every",
            "figure digest is the sha256 of an array the renderer drew from such a",
            "receipt; every methods entry is the set of receipt fields the paragraph",
            "was filled from. This capability owns none of these numbers.",
            "The run identifier of a fixture run is bound to the runtime name, so it is",
            "deliberately not recorded here; the values are the same under any name.",
        ],
        "recorded": "2026-09-20",
        "seed": SEED,
        "sweeps": {},
        "figures": {},
        "methods": {},
        "refusals": {
            "aggregate_across_conventions": "aggregate-across-rows",
            "clear_sky_gotcha_cited": CLEAR_SKY_GOTCHA,
            "map_mode": "map-mode-unavailable",
            "array_hash": "array-hash-mismatch",
            "fact_not_in_receipt": "fact-not-in-receipt",
        },
    }
    for name, spec in SWEEPS.items():
        manifest = done[name]
        doc["sweeps"][name] = {
            "why": spec["why"],
            "computation": spec["computation"],
            "parameter": spec["parameter"],
            "values": spec["values"],
            "fixed": spec["fixed"],
            "concept": manifest["concept"],
            "code_sha256": manifest["code_sha256"],
            "input": manifest["input"],
            "columns": [column["name"] for column in manifest["columns"]],
            "column_fields": {column["name"]: column["receipt_field"]
                              for column in manifest["columns"]},
            "rows": [{"value": row["value"], "status": row["status"],
                      "reason_code": row["reason_code"], "cells": row["cells"]}
                     for row in manifest["rows"]],
        }
    for name, spec in FIGURES.items():
        receipt = Path(done[spec["sweep"]]["rows"][spec["row"]]["receipt"])
        out = work / f"measure-{name}.png"
        got = run(FIGURE, [spec["mode"], str(receipt), "--attester",
                           spec["attester"], *spec["extra"], "--out", str(out)])
        check(got.returncode == 0, f"measuring the {name} figure: {got.stdout}{got.stderr}")
        doc["figures"][name] = {
            "sweep": spec["sweep"], "row": spec["row"], "mode": spec["mode"],
            "attester": spec["attester"], "extra": spec["extra"],
            "arrays": array_digests(got.stdout),
        }
    for name, spec in METHODS_RUNS.items():
        receipt = Path(done[spec["sweep"]]["rows"][spec["row"]]["receipt"])
        out = work / f"measure-{name}.md"
        got = run(METHODS, [str(receipt), "--out", str(out)])
        check(got.returncode == 0, f"measuring the {name} paragraph: "
                                   f"{got.stdout}{got.stderr}")
        text = out.read_text(encoding="utf-8")
        doc["methods"][name] = {
            "sweep": spec["sweep"], "row": spec["row"],
            "sentences": sentences_of(text),
            "fields": sorted(fields_of(text)),
            "references": referenced(text),
            "facts": facts_of(name, text),
        }
    return doc


def array_digests(stdout: str) -> dict:
    return {match.group(1): match.group(2) for match in
            re.finditer(r"^\s+array (\S+) sha256 ([0-9a-f]{64})$", stdout, re.M)}


def sentences_of(text: str):
    rows = re.findall(r"^\| ([a-z_]+) \| (.+) \|$", text, re.M)
    return [name for name, _ in rows if name != "sentence"]


def fields_of(text: str):
    out = set()
    for _, fields in re.findall(r"^\| ([a-z_]+) \| (.+) \|$", text, re.M):
        out |= {part.strip() for part in fields.split(",")}
    return {field for field in out if "." in field or field.isidentifier()}


def referenced(text: str):
    return sorted(set(re.findall(r"^\[\^([A-Za-z0-9._-]+)\]:", text, re.M)))


FACTS = {
    "cloud-radiative-effect": {
        "convention_bound": r"bound to (total-region|cloud-free-area)",
        "variable_suffix": r"variable suffix (clr_[tc])",
        "other_convention": r"the other convention the product carries, "
                            r"(total-region|cloud-free-area)",
        "region": r"for the region (\S+) over",
    },
    "energy-budget": {
        "anchor_decade": r"The anchoring decade is (\S+ through \S+?),",
        "shared_months": r"and (\d+ of the \d+ months) of this window",
        "ocean_input": r"The ocean input bookkeeping this run carries is: "
                       r"(synthetic[^.]*)",
    },
}


def facts_of(name: str, text: str) -> dict:
    out = {}
    for label, pattern in FACTS[name].items():
        found = re.search(pattern, text)
        check(found is not None,
              f"the {name} paragraph states no {label}; the pattern "
              f"{pattern!r} found nothing")
        out[label] = found.group(1)
    return out


def check_sweeps(expect: dict, done: dict) -> None:
    for name, spec in expect["sweeps"].items():
        manifest = done[name]
        where = f"the {name} sweep"
        check(manifest["code_sha256"] == spec["code_sha256"],
              f"{where}: the executor in the installed bundle is "
              f"{manifest['code_sha256']}, not the {spec['code_sha256']} these "
              "expectations were measured with; the table is a different "
              f"method, so re-measure {EXPECTATIONS.name} and record the new "
              "digest rather than loosening this check")
        check(manifest["input"]["digest"] == spec["input"]["digest"],
              f"{where}: the regenerated fixture does not hash to the digest "
              "the expectations were measured on")
        got_columns = [column["name"] for column in manifest["columns"]]
        check(got_columns == spec["columns"],
              f"{where}: the columns are {got_columns}, not {spec['columns']}")
        got_fields = {column["name"]: column["receipt_field"]
                      for column in manifest["columns"]}
        check(got_fields == spec["column_fields"],
              f"{where}: a column no longer reads the receipt field it read "
              "when the expectations were measured")
        check(len(manifest["rows"]) == len(spec["rows"]),
              f"{where}: {len(manifest['rows'])} rows, not the "
              f"{len(spec['rows'])} the expectations record")
        for got, want in zip(manifest["rows"], spec["rows"]):
            at = f"{where}, {spec['parameter']} {want['value']}"
            check(got["value"] == want["value"],
                  f"{at}: the row is {got['value']}")
            check(got["attested"], f"{at}: the receipt did not attest: "
                                   f"{got['attestation']}")
            check(got["status"] == want["status"],
                  f"{at}: is {got['status']}, not {want['status']}")
            check(got["reason_code"] == want["reason_code"],
                  f"{at}: refused with {got['reason_code']}, not "
                  f"{want['reason_code']}")
            check(bool(got["run_id"]), f"{at}: carries no run id to follow back")
            if got["status"] == "refused":
                numbers = [key for key, cell in got["cells"].items()
                           if isinstance(cell, (int, float))
                           and not isinstance(cell, bool)]
                check(not numbers,
                      f"{at}: the refused row carries numbers "
                      f"({', '.join(numbers)}); a refusal is never a number")
            for column in spec["columns"]:
                check(same(got["cells"].get(column), want["cells"].get(column)),
                      f"{at}, column {column}: {got['cells'].get(column)} is "
                      f"not the recorded {want['cells'].get(column)}")


def check_reversal(expect: dict) -> None:
    """The finding the convention sweep exists to make: over the
    Antarctic band the total-region net effect is the less negative of
    the two, where the concept records the globe the other way round.
    Both numbers are receipt fields; this golden compares two cells of
    one table and states no number of its own."""
    rows = {row["value"]: row["cells"] for row in expect["sweeps"]["conventions"]["rows"]}
    total = rows["total-region"]["cre_net_value_W_m2"]
    free = rows["cloud-free-area"]["cre_net_value_W_m2"]
    check(total is not None and free is not None,
          "the convention sweep has no net effect on one of its rows")
    check(total > free,
          "over the Antarctic band the recorded total-region net effect "
          f"({total}) is not the less negative of the two ({free}); the "
          "reversal the concept records is what this table is for, so a "
          "table that does not show it is a finding and not a fixture to "
          "re-measure")
    for convention, other in (("total-region", "cloud-free-area"),
                              ("cloud-free-area", "total-region")):
        check(rows[convention]["contrast_convention"] == other,
              f"the {convention} row's contrast block does not name {other}")


def check_aggregate(work: Path) -> None:
    out_dir = work / "aggregate"
    got = run(SWEEP, [*sweep_args(SWEEPS["conventions"], out_dir),
                      "--aggregate",
                      "one global net cloud radiative effect across both "
                      "clear-sky conventions"])
    line = (got.stdout or "").strip()
    check(got.returncode == 4 and "aggregate-across-rows" in line,
          f"the sweep did not refuse the aggregate across its rows (exit "
          f"{got.returncode}); that number is one no concept owns")
    check("will not average across the clear-sky conventions" in line,
          "the refusal of an aggregate across the two conventions does not "
          "say that is what it refuses")
    check(CLEAR_SKY_GOTCHA in line,
          f"the refusal does not cite {CLEAR_SKY_GOTCHA} by bundle path")
    check("Antarctic" in line and "ADR D" in line,
          "the refusal does not name the reversal or the decision record")
    check(not (out_dir / "sweep.csv").is_file(),
          "the refused aggregate still wrote a table; a refusal leaves no "
          "partial output")


def check_figures(expect: dict, done: dict, work: Path) -> None:
    for name, spec in expect["figures"].items():
        receipt = Path(done[spec["sweep"]]["rows"][spec["row"]]["receipt"])
        out = work / f"{name}.png"
        got = run(FIGURE, [spec["mode"], str(receipt), "--attester",
                           spec["attester"], *spec["extra"], "--out", str(out)])
        check(got.returncode == 0,
              f"the {name} figure exited {got.returncode}: "
              f"{got.stdout}{got.stderr}")
        check(out.is_file(), f"the {name} figure wrote no file")
        digests = array_digests(got.stdout)
        check(digests == spec["arrays"],
              f"the {name} figure drew arrays {json.dumps(digests, indent=2)}, "
              f"not the recorded {json.dumps(spec['arrays'], indent=2)}")
        check("PASS" in got.stdout,
              f"the {name} figure's caption carries no attester verdict")
        wrong = run(FIGURE, [spec["mode"], str(receipt), "--attester",
                             spec["attester"], *spec["extra"],
                             "--expect", f"{sorted(spec['arrays'])[0]}="
                                         + "0" * 64,
                             "--out", str(work / f"{name}-wrong.png")])
        check(wrong.returncode == 4 and "array-hash-mismatch" in wrong.stdout,
              f"the {name} figure drew an array whose restated digest did not "
              "match")
        check(not (work / f"{name}-wrong.png").is_file(),
              f"the refused {name} figure still wrote a file")
    receipt = Path(done["conventions"]["rows"][0]["receipt"])
    got = run(FIGURE, ["map", str(receipt), "--attester",
                       "cloud_radiative_effect_check",
                       "--out", str(work / "map.png")])
    check(got.returncode == 4 and "map-mode-unavailable" in got.stdout,
          "a map was not refused; these receipts carry no per-cell field")
    check(not (work / "map.png").is_file(),
          "the refused map still wrote a file")


def check_methods(expect: dict, done: dict, work: Path) -> None:
    for name, spec in expect["methods"].items():
        receipt = Path(done[spec["sweep"]]["rows"][spec["row"]]["receipt"])
        out = work / f"{name}.md"
        got = run(METHODS, [str(receipt), "--out", str(out)])
        check(got.returncode == 0,
              f"the {name} paragraph exited {got.returncode}: "
              f"{got.stdout}{got.stderr}")
        text = out.read_text(encoding="utf-8")
        check(sentences_of(text) == spec["sentences"],
              f"the {name} paragraph writes {sentences_of(text)}, not the "
              f"recorded {spec['sentences']}")
        check(sorted(fields_of(text)) == spec["fields"],
              f"the {name} paragraph is filled from fields that are not the "
              "recorded ones")
        check(referenced(text) == spec["references"],
              f"the {name} reference list is {referenced(text)}, not the "
              f"recorded {spec['references']}")
        check(facts_of(name, text) == spec["facts"],
              f"the {name} paragraph states {facts_of(name, text)}, not the "
              f"recorded {spec['facts']}")
        body = json.loads(receipt.read_text(encoding="utf-8"))
        check(body["run_id"] in text and body["code_sha256"] in text,
              f"the {name} paragraph does not name the run it is of")
        marked = set(re.findall(r"\[\^([A-Za-z0-9._-]+)\](?!:)", text))
        check(marked and marked <= set(spec["references"]),
              f"the {name} paragraph cites {marked - set(spec['references'])}, "
              "which the reference list does not carry")
    receipt = Path(done["conventions"]["rows"][0]["receipt"])
    got = run(METHODS, [str(receipt), "--claim",
                        "the effect agrees with the model ensemble"])
    check(got.returncode == 4 and "fact-not-in-receipt" in got.stdout,
          "a fact from outside the receipt was written into the paragraph")


def selftests() -> None:
    for script, marker in ((SWEEP, "sweep selftest: ok"),
                           (FIGURE, "receipt-figures selftest: ok"),
                           (METHODS, "methods selftest: ok")):
        got = run(script, ["--selftest"])
        print((got.stdout or "").strip() or (got.stderr or "").strip())
        check(got.returncode == 0 and marker in got.stdout,
              f"{script.name} --selftest FAILED\n{(got.stderr or '').strip()}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--measure", action="store_true",
                    help="rewrite the expectations file from what the skills "
                         "produce today, for a deliberate re-measure")
    args = ap.parse_args()

    for script in (SWEEP, FIGURE, METHODS):
        if not script.is_file():
            return fail(f"no script at {script}")

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        try:
            if args.measure:
                doc = measure(work)
                EXPECTATIONS.write_text(json.dumps(doc, indent=2) + "\n",
                                        encoding="utf-8")
                print(f"receipt-skills golden: re-measured "
                      f"{EXPECTATIONS.relative_to(PACKAGE_ROOT)}")
                return 0
            expect = json.loads(EXPECTATIONS.read_text(encoding="utf-8"))
            selftests()
            done = do_sweeps(work)
            check_sweeps(expect, done)
            check_reversal(expect)
            check_aggregate(work)
            check_figures(expect, done, work)
            check_methods(expect, done, work)
        except Failed as bad:
            return fail(str(bad))

    rows = sum(len(spec["rows"]) for spec in expect["sweeps"].values())
    refused = sum(1 for spec in expect["sweeps"].values()
                  for row in spec["rows"] if row["status"] == "refused")
    print(f"receipt-skills golden: 3 selftests, {len(expect['sweeps'])} sweeps "
          f"of {rows} rows ({refused} refused by an executor) every cell equal "
          f"to {EXPECTATIONS.relative_to(PACKAGE_ROOT)}, "
          f"{len(expect['figures'])} figures with every array digest equal to "
          f"the recorded one, {len(expect['methods'])} methods paragraphs "
          "filled from the recorded receipt fields; the aggregate across the "
          "two clear-sky conventions, a map, a restated wrong array digest "
          "and a fact from outside the receipt are all refused")
    return 0


if __name__ == "__main__":
    sys.exit(main())
