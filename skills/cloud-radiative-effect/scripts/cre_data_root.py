#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Assemble and stamp the data root of the attested cloud radiative
effect at the top of the atmosphere: the flux file the loader wrote,
its stamp, SOURCES.json, and the RECORD.json the sanctioned
computation refuses to run without.

The record carries the record name, the SHA-256 manifest of every file
in the root (cre-fluxes.csv, cre-fluxes-stamp.json, SOURCES.json), the
time of stamping, the loader's stamp, a table of the regions and
conventions the flux file carries with the months each holds, and the
bookkeeping table under `bookkeeping` with every statement the
computation requires: `convention` (which product variable each
clear-sky convention reads and what the convention is), `weighting`
(the CERES one degree zonal geodetic weights and the loader's
cross-check against the product's own global means), `edition` (the
product version, release date, DOI and file), `uncertainty` (the basis
of the per-month floor) and `region` (the latitude bands, their share
of the geodetic weight and the absence of a surface type mask). The
statements are read from the loader's stamp where it determined them
and from the sources the bundle's concepts cite for the rest; this
file is where they are written down, so a reader auditing a cloud
radiative effect starts here.

Usage:
  cre_data_root.py --root DIR --record NAME
      DIR holds cre-fluxes.csv, cre-fluxes-stamp.json and SOURCES.json
  cre_data_root.py --root DIR --check
      verify an existing RECORD.json against the files (exit 1 on drift)
  cre_data_root.py --selftest
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

FILES = ("cre-fluxes.csv", "cre-fluxes-stamp.json", "SOURCES.json")
REQUIRED = ("convention", "weighting", "edition", "uncertainty", "region")


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


def coverage(csv_path: Path) -> dict:
    """The months each region and convention of the flux file carries."""
    months = {}
    with csv_path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            key = f"{row['region'].strip()}/{row['convention'].strip()}"
            months.setdefault(key, []).append(row["month"].strip())
    if not months:
        sys.exit(f"{csv_path.name} carries no rows")
    return {k: {"months": [min(v), max(v)], "n_months": len(v)}
            for k, v in sorted(months.items())}


def bookkeeping(stamp: dict) -> dict:
    return {
        "convention": {
            "statement": "the two clear-sky conventions the energy balanced product carries, "
                         "each read from its own variables: "
                         + "; ".join(
                             f"{name} from {', '.join(block['variables'])}"
                             for name, block in sorted(
                                 (stamp.get("clear_sky_conventions") or {}).items())),
            "conventions": stamp.get("clear_sky_conventions"),
            "cre_rule": stamp.get("cre_rule"),
            "note": "a cloud radiative effect is all-sky minus clear-sky in every one of these "
                    "products, so it inherits the convention of the field it subtracts; the "
                    "bundle's convention concept conventions/ceres-clear-sky-conventions.md "
                    "states the four quantities the radiation products call clear-sky and "
                    "which one each field carries",
            "product_cre_cross_check": stamp.get("product_cre_cross_check"),
        },
        "weighting": {
            "statement": stamp.get("weights", ""),
            "weights_file": stamp.get("weights_file"),
            "weights_sha256": stamp.get("weights_sha256"),
            "weights_source": stamp.get("weights_source"),
            "weights_zones": stamp.get("weights_zones"),
            "weights_sum": stamp.get("weights_sum"),
            "loader_cross_check": stamp.get("weighting_cross_check"),
            "note": "a region is a band of whole one degree zones, so its mean is the "
                    "product's own global mean restricted to those zones",
        },
        "edition": {
            "statement": f"{stamp.get('product')}; {stamp.get('product_version')}; DOI "
                         f"{stamp.get('doi')}; file {stamp.get('file')}",
            "product_version": stamp.get("product_version"),
            "doi": stamp.get("doi"),
            "file": stamp.get("file"),
            "climatology_note": stamp.get("climatology_note"),
            "variables": stamp.get("variables"),
        },
        "uncertainty": {
            "basis": stamp.get("uncertainty_basis", ""),
            "floors": stamp.get("uncertainty_floors"),
            "published_regional_monthly": stamp.get("published_regional_monthly_uncertainty"),
        },
        "region": {
            "statement": stamp.get("mask", ""),
            "regions": stamp.get("regions"),
            "grid": stamp.get("grid"),
        },
        "months": {"cre_fluxes": stamp.get("months"),
                   "cre_fluxes_n_months": stamp.get("n_months"),
                   "skipped": stamp.get("skipped_months")},
    }


def build(root: Path, record: str):
    stamp_path, csv_path = root / "cre-fluxes-stamp.json", root / "cre-fluxes.csv"
    for p in (stamp_path, csv_path):
        if not p.is_file():
            sys.exit(f"{root} lacks {p.name}")
    stamp = json.loads(stamp_path.read_text(encoding="utf-8"))
    if stamp.get("term") != "cre-fluxes":
        sys.exit("the stamp in the root is not a cre-fluxes stamp")
    files = manifest(root)
    mh = hashlib.sha256("\n".join(f"{k} {v}" for k, v in sorted(files.items())).encode()).hexdigest()
    doc = {
        "record": record,
        "manifest": files,
        "manifest_sha256": "sha256:" + mh,
        "verified_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "terms": {"cre-fluxes": stamp},
        "coverage": coverage(csv_path),
        "bookkeeping": bookkeeping(stamp),
    }
    (root / "RECORD.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(f"RECORD.json written for {record}: manifest sha256:{mh[:16]}, cre-fluxes "
          f"{stamp['months'][0]} to {stamp['months'][1]}, {len(doc['coverage'])} region and "
          f"convention series")


def check(root: Path):
    p = root / "RECORD.json"
    if not p.is_file():
        sys.exit(f"{root} lacks RECORD.json")
    doc = json.loads(p.read_text(encoding="utf-8"))
    files = manifest(root)
    if files != doc.get("manifest"):
        sys.exit("RECORD.json manifest does not match the files")
    if "cre-fluxes" not in (doc.get("terms") or {}):
        sys.exit("RECORD.json lacks the cre-fluxes stamp")
    if coverage(root / "cre-fluxes.csv") != doc.get("coverage"):
        sys.exit("RECORD.json coverage does not match the flux file")
    for key in REQUIRED:
        if key not in (doc.get("bookkeeping") or {}):
            sys.exit(f"RECORD.json bookkeeping lacks {key}")
    print("RECORD.json matches the files")


def selftest():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        with (root / "cre-fluxes.csv").open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["region", "convention", "month", "sw_all_W_m2", "lw_all_W_m2",
                        "net_all_W_m2", "sw_clr_W_m2", "lw_clr_W_m2", "net_clr_W_m2",
                        "cre_sw_uncertainty_W_m2", "cre_lw_uncertainty_W_m2",
                        "cre_net_uncertainty_W_m2"])
            for convention, dsw, dlw in (("total-region", -45.0, 26.0),
                                         ("cloud-free-area", -46.0, 28.0)):
                for i in range(24):
                    month = f"{2010 + i // 12:04d}-{i % 12 + 1:02d}"
                    sw_all, lw_all = 99.0 + 0.01 * i, 240.0
                    sw_clr, lw_clr = sw_all + dsw, lw_all + dlw
                    w.writerow(["global", convention, month, f"{sw_all:.6f}", f"{lw_all:.6f}",
                                f"{340.0 - sw_all - lw_all:.6f}", f"{sw_clr:.6f}",
                                f"{lw_clr:.6f}", f"{340.0 - sw_clr - lw_clr:.6f}",
                                "0.400000", "0.250000", "0.400000"])
        (root / "cre-fluxes-stamp.json").write_text(json.dumps({
            "term": "cre-fluxes", "product": "toy", "product_version": "toy",
            "doi": "10.5067/TOY", "file": "toy.nc",
            "clear_sky_conventions": {
                "total-region": {"variable_suffix": "clr_t",
                                 "variables": ["toa_sw_clr_t_mon", "toa_lw_clr_t_mon",
                                               "toa_net_clr_t_mon"]},
                "cloud-free-area": {"variable_suffix": "clr_c",
                                    "variables": ["toa_sw_clr_c_mon", "toa_lw_clr_c_mon",
                                                  "toa_net_clr_c_mon"]}},
            "cre_rule": "toy rule", "weights": "toy zonal geodetic weights",
            "weights_file": "toy.txt", "weights_sha256": "sha256:toy", "weights_zones": 180,
            "weights_sum": 1.0, "weights_source": "toy",
            "months": ["2010-01", "2011-12"], "n_months": 24, "skipped_months": {},
            "uncertainty_basis": "toy floor",
            "uncertainty_floors": {"global/total-region": {"cre_net_W_m2": 0.4}},
            "mask": "toy latitude bands, no surface type mask",
            "regions": {"global": {"latitude_band": [-90.0, 90.0], "weight_share": 1.0}},
            "grid": "toy grid", "variables": {},
            "weighting_cross_check": {"fields": {}},
            "product_cre_cross_check": {"terms": {}}}) + "\n")
        (root / "SOURCES.json").write_text("{}\n")
        build(root, "toy-record")
        check(root)
        rec = json.loads((root / "RECORD.json").read_text())
        assert set(rec["manifest"]) == set(FILES)
        assert set(rec["coverage"]) == {"global/total-region", "global/cloud-free-area"}
        assert rec["coverage"]["global/total-region"]["n_months"] == 24
        assert "toa_sw_clr_t_mon" in rec["bookkeeping"]["convention"]["statement"]
        assert all(k in rec["bookkeeping"] for k in REQUIRED)
        (root / "cre-fluxes.csv").write_text(
            "region,convention,month,sw_all_W_m2,lw_all_W_m2,net_all_W_m2,sw_clr_W_m2,"
            "lw_clr_W_m2,net_clr_W_m2,cre_sw_uncertainty_W_m2,cre_lw_uncertainty_W_m2,"
            "cre_net_uncertainty_W_m2\nglobal,total-region,2010-01,99,240,1,54,266,20,"
            "0.4,0.25,0.4\n")
        try:
            check(root)
        except SystemExit as e:
            assert "manifest" in str(e), e
        else:
            raise AssertionError("an edited file passed --check")
    print("cre_data_root selftest: ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", type=Path)
    ap.add_argument("--record")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    if not a.root:
        ap.error("--root is required")
    if a.check:
        check(a.root)
        return
    if not a.record:
        ap.error("--record is required to build")
    build(a.root, a.record)


if __name__ == "__main__":
    main()
