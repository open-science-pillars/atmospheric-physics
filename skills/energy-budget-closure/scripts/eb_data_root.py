#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Assemble and stamp the data root of the attested energy budget
closure: the radiation term file the loader wrote, its stamp, the Argo
ocean heat content receipt the ocean side is read from, SOURCES.json,
and the RECORD.json the sanctioned computation refuses to run without.

The record carries the record name, the SHA-256 manifest of every file
in the root (toa-net.csv, toa-net-stamp.json, ohc-2000-receipt.json,
SOURCES.json), the time of stamping, the loader's stamp, the identity
of the Argo receipt (its computation, code digest, run id, window,
depth, bundle and the record it was run on), and the bookkeeping table
under `bookkeeping` with every statement the computation requires:
`anchoring` (the product's anchor and what it means for a window
mean), `weighting` (the cos-latitude mean against the product's
geodetic mean, with the offset the loader measured), `edition` (the
product version, release date, DOI and file), `uncertainty` (the basis
of the per-month floor) and `ocean_input` (which receipt supplies the
ocean side and what its rate covers). The statements are read from the
loader's stamp and the receipt where they determined them and from the
sources the bundle's concepts cite for the rest; this file is where
they are written down, so a reader auditing a residual starts here.

Usage:
  eb_data_root.py --root DIR --record NAME
      DIR holds toa-net.csv, toa-net-stamp.json, ohc-2000-receipt.json
      and SOURCES.json
  eb_data_root.py --root DIR --check
      verify an existing RECORD.json against the files (exit 1 on drift)
  eb_data_root.py --selftest
      build and check a root from synthetic files
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import sys
import tempfile
from pathlib import Path

FILES = ("toa-net.csv", "toa-net-stamp.json", "ohc-2000-receipt.json", "SOURCES.json")


def sha256(p: Path) -> str:
    return "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()


def manifest(root: Path) -> dict:
    out = {}
    for name in FILES:
        p = root / name
        if not p.is_file():
            sys.exit(f"{root} lacks {name}")
        out[name] = sha256(p)
    return out


def receipt_identity(r: dict) -> dict:
    d = r.get("data") or {}
    return {"computation": r.get("computation"), "code_sha256": r.get("code_sha256"),
            "run_id": r.get("run_id"), "refused": r.get("refused"),
            "bound_parameters": r.get("bound_parameters"), "bundle": r.get("bundle"),
            "capability": r.get("capability"), "runtime": r.get("runtime"),
            "generated_utc": r.get("generated_utc"), "record": d.get("record"),
            "record_sha256": d.get("record_sha256"), "data_root": d.get("data_root"),
            "trend_ZJ_yr": ((r.get("terms") or {}).get("trend") or {}).get("value"),
            "trend_uncertainty_ZJ_yr": ((r.get("terms") or {}).get("trend") or {}).get("uncertainty")}


def bookkeeping(stamp: dict, ohc: dict) -> dict:
    anchor = stamp.get("anchoring") or {}
    cross = stamp.get("weighting_cross_check") or {}
    cov = ((ohc.get("bookkeeping") or {}).get("coverage") or {})
    return {
        "anchoring": {
            "statement": anchor.get("statement", ""),
            "value_W_m2": anchor.get("value_W_m2"),
            "uncertainty_W_m2": anchor.get("uncertainty_W_m2"),
            "period": anchor.get("period"),
            "note": "the anchor is defined on the product's geodetic global mean; a window mean "
                    "of that series is the anchored quantity and carries the anchor's "
                    "uncertainty; the anomaly against the window mean does not",
        },
        "weighting": {
            "statement": stamp.get("weights", ""),
            "loader_cross_check": cross,
            "note": "the fourth column of toa-net.csv is the product's own global mean; the "
                    "computation forms the absolute term from it and the anomaly from the "
                    "cos-latitude column",
        },
        "edition": {
            "statement": f"{stamp.get('product')}; {stamp.get('product_version')}; DOI "
                         f"{stamp.get('doi')}; file {stamp.get('file')}",
            "product_version": stamp.get("product_version"),
            "doi": stamp.get("doi"),
            "file": stamp.get("file"),
            "climatology_note": stamp.get("climatology_note"),
        },
        "uncertainty": {
            "basis": stamp.get("uncertainty_basis", ""),
            "toa_net_W_m2": stamp.get("uncertainty_W_m2"),
            "published_monthly_random_error_W_m2": stamp.get("published_monthly_random_error_W_m2"),
        },
        "ocean_input": {
            "statement": f"the 0 to 2000 dbar ocean heat content rate is read from the Argo "
                         f"receipt ohc-2000-receipt.json in this root ({ohc.get('computation')}, "
                         f"run {ohc.get('run_id')}, window "
                         f"{(ohc.get('bound_parameters') or {}).get('window')}), produced by the "
                         f"ocean-science plugin's computation on its committed data root "
                         f"{(ohc.get('data') or {}).get('record')}",
            "receipt": receipt_identity(ohc),
            "domain": cov.get("statement"),
            "domain_area_m2": cov.get("domain_area_m2"),
            "note": "the rate is over the product's mapped open-ocean domain and is never "
                    "scaled to the global ocean",
        },
        "months": {"toa_net": stamp.get("months"), "toa_net_n_months": stamp.get("n_months")},
    }


def build(root: Path, record: str):
    stamp_path, ohc_path = root / "toa-net-stamp.json", root / "ohc-2000-receipt.json"
    for p in (stamp_path, ohc_path):
        if not p.is_file():
            sys.exit(f"{root} lacks {p.name}")
    stamp = json.loads(stamp_path.read_text(encoding="utf-8"))
    ohc = json.loads(ohc_path.read_text(encoding="utf-8"))
    if ohc.get("refused") is not False:
        sys.exit("the Argo receipt in the root is a refusal or malformed; nothing to record")
    files = manifest(root)
    mh = hashlib.sha256("\n".join(f"{k} {v}" for k, v in sorted(files.items())).encode()).hexdigest()
    doc = {
        "record": record,
        "manifest": files,
        "manifest_sha256": "sha256:" + mh,
        "verified_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "terms": {"toa-net": stamp},
        "ocean_receipt": receipt_identity(ohc),
        "bookkeeping": bookkeeping(stamp, ohc),
    }
    (root / "RECORD.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(f"RECORD.json written for {record}: manifest sha256:{mh[:16]}, toa-net "
          f"{stamp['months'][0]} to {stamp['months'][1]}, Argo receipt {ohc.get('run_id')} over "
          f"{(ohc.get('bound_parameters') or {}).get('window')}")


def check(root: Path):
    p = root / "RECORD.json"
    if not p.is_file():
        sys.exit(f"{root} lacks RECORD.json")
    doc = json.loads(p.read_text(encoding="utf-8"))
    files = manifest(root)
    if files != doc.get("manifest"):
        sys.exit("RECORD.json manifest does not match the files")
    if "toa-net" not in (doc.get("terms") or {}):
        sys.exit("RECORD.json lacks the toa-net stamp")
    for key in ("anchoring", "weighting", "edition", "uncertainty", "ocean_input"):
        if key not in (doc.get("bookkeeping") or {}):
            sys.exit(f"RECORD.json bookkeeping lacks {key}")
    print("RECORD.json matches the files")


def selftest():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        with (root / "toa-net.csv").open("w", newline="") as f:
            w = csv.writer(f); w.writerow(["month", "value_W_m2", "uncertainty_W_m2", "product_global_W_m2"])
            for i in range(24):
                w.writerow([f"{2010 + i // 12:04d}-{i % 12 + 1:02d}", f"{1.0 + 0.01 * i:.6f}", "0.3", f"{0.8 + 0.01 * i:.6f}"])
        (root / "toa-net-stamp.json").write_text(json.dumps({
            "term": "toa-net", "product": "toy", "product_version": "toy", "doi": "10.5067/TOY",
            "file": "toy.nc", "weights": "cos-latitude", "months": ["2010-01", "2011-12"],
            "n_months": 24, "uncertainty_W_m2": 0.3, "uncertainty_basis": "toy floor",
            "anchoring": {"statement": "toy anchor", "value_W_m2": 0.71, "uncertainty_W_m2": 0.1,
                          "period": "2005-07 through 2015-06"},
            "weighting_cross_check": {"mean_difference_W_m2": 0.2}}) + "\n")
        (root / "ohc-2000-receipt.json").write_text(json.dumps({
            "computation": "references/computations/argo_ohc.py", "code_sha256": "sha256:x",
            "run_id": "sha256:y", "refused": False,
            "bound_parameters": {"window": "2010-01:2011-12", "depth": 2000},
            "data": {"record": "toy-root"}, "terms": {"trend": {"value": 9.0, "uncertainty": 1.0}},
            "bookkeeping": {"coverage": {"statement": "toy domain", "domain_area_m2": 3.0e14}}}) + "\n")
        (root / "SOURCES.json").write_text("{}\n")
        build(root, "toy-record")
        check(root)
        rec = json.loads((root / "RECORD.json").read_text())
        assert set(rec["manifest"]) == set(FILES)
        assert rec["bookkeeping"]["ocean_input"]["receipt"]["run_id"] == "sha256:y"
        assert rec["bookkeeping"]["anchoring"]["value_W_m2"] == 0.71
        (root / "toa-net.csv").write_text("month,value_W_m2,uncertainty_W_m2,product_global_W_m2\n2010-01,1,0.3,0.8\n")
        try:
            check(root)
        except SystemExit as e:
            assert "manifest" in str(e), e
        else:
            raise AssertionError("an edited file passed --check")
    print("eb_data_root selftest: ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", type=Path)
    ap.add_argument("--record")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest(); return
    if not a.root:
        ap.error("--root is required")
    if a.check:
        check(a.root); return
    if not a.record:
        ap.error("--record is required to build")
    build(a.root, a.record)


if __name__ == "__main__":
    main()
