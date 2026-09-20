#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy==2.4.6", "netCDF4==1.7.4"]
# ///
"""Loader for the radiation term of the attested energy budget closure:
the global mean net top-of-atmosphere (TOA) all-sky flux per calendar
month from CERES EBAF Edition 4.2.1, written as the data root's
toa-net.csv.

What it computes, per month of the product file:

  1. The cos-latitude weighted global mean of toa_net_all_mon (the
     monthly mean net downward TOA flux, all-sky, on the one degree
     grid) over every cell that carries a value, in watts per square
     metre, the weights the cosine of each cell's centre latitude. The
     product's own global mean, gtoa_net_all_mon, is formed with the
     project's zonal geodetic weights (the data quality summary); the
     loader reads that series too, writes it as the fourth column and
     states the difference between the two weightings in the stamp,
     so a reader can see what the choice of weights is worth.
  2. The calendar month of each time value (days since 2000-03-01, the
     mid-month day) as the row label. A month whose field carries no
     value is not a sample and is skipped; the stamp lists it.
  3. The per-month uncertainty as a stated noise floor: the standard
     deviation of adjacent-month differences of the series with its
     calendar-month means removed, divided by sqrt(2), written on
     every row and named in the stamp; the product ships no
     uncertainty field. The published random error of a global monthly
     anomaly after the satellite transitions (below 0.15 W m-2, the
     dataset concept) is written beside it for comparison. The
     sanctioned computation takes the larger of this floor's
     propagation and the sampling half width of what it fits.

The global mean net flux carries the product's anchoring: the shortwave
and longwave fluxes were adjusted once so that the July 2005 through
June 2015 mean equals an in situ heat uptake of 0.71 W m-2 (the
bundle's ebaf-imbalance-anchored-to-ocean-heating gotcha). The loader
writes the values as the product carries them and states the anchor in
the stamp; the computation is where the anomaly is formed.

The product file is read from a local path. With --fetch the file is
downloaded first when the path does not exist, from the ASDC OPeNDAP
service as a netCDF-4 subset carrying only the variables read
(toa_net_all_mon, gtoa_net_all_mon, lat, lon, time), or from any URL
given with --url; the download is tried without credentials, then once
more with the Earthdata Login bearer token in EARTHDATA_TOKEN sent as
a request header, which is never written anywhere. A download record
(URL, status, bytes, sha256, time) is written beside the file, and the
stamp copies it under sources. The product file stays where it was
downloaded, outside the data root; only the CSV and the stamp are
committed.

Usage:
  eb_ceres_ebaf.py --product FILE.nc --out toa-net.csv [--stamp-out toa-net-stamp.json]
      [--start YYYY-MM] [--end YYYY-MM] [--fetch [--url URL]]
  --selftest   three synthetic months with known means
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

import netCDF4 as nc
import numpy as np

FIELD = "toa_net_all_mon"
PRODUCT_GLOBAL = "gtoa_net_all_mon"
GRANULE = "CERES_EBAF_Edition4.2.1_200003-202605.nc"
COLLECTION = "C3880496704-LARC_CLOUD"
DEFAULT_URL = (f"https://opendap.earthdata.nasa.gov/collections/{COLLECTION}/granules/"
               f"{GRANULE}.nc4?{FIELD},{PRODUCT_GLOBAL},lat,lon,time")
FILL_BELOW = -998.0                    # the product's fill is -999.0
PUBLISHED_MONTHLY_RANDOM_ERROR_W_M2 = 0.15
ANCHOR = {"value_W_m2": 0.71, "uncertainty_W_m2": 0.10,
          "period": "2005-07 through 2015-06",
          "statement": "the global mean net TOA flux over July 2005 through June 2015 is set "
                       "to the in situ heat uptake of 0.71 W m-2 (uncertainty 0.10 at the 95 "
                       "percent level) by a one-time adjustment of the shortwave and longwave "
                       "fluxes, unchanged from Edition 4.1 into 4.2 and 4.2.1; the bundle's "
                       "ebaf-imbalance-anchored-to-ocean-heating gotcha and the Edition 4.2 "
                       "and 4.0 data quality summaries"}
IDENTITY = ("title", "institution", "Conventions", "version", "DOI", "comment")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---- the download

def fetch(target: Path, url: str) -> dict:
    """Download url to target: first without credentials, then once
    more with the Earthdata Login bearer token when the environment
    holds one and the first attempt was refused. The token is sent as
    a header and appears in no record."""
    target.parent.mkdir(parents=True, exist_ok=True)
    token = os.environ.get("EARTHDATA_TOKEN")
    attempts = []
    for with_token in (False, True):
        if with_token and not token:
            break
        req = urllib.request.Request(url)
        if with_token:
            req.add_header("Authorization", f"Bearer {token}")
        started = now_utc()
        status, nbytes, error = None, 0, None
        try:
            with urllib.request.urlopen(req, timeout=1800) as r, target.open("wb") as f:
                status = r.status
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
            nbytes = target.stat().st_size
        except urllib.error.HTTPError as e:
            status, error = e.code, f"HTTP {e.code}"
        except Exception as e:                       # noqa: BLE001
            error = f"{type(e).__name__}: {e}"
        attempts.append({"credentials": "Earthdata Login bearer token as a request header"
                         if with_token else "none", "status": status, "error": error,
                         "started_utc": started})
        if status == 200 and nbytes > 0:
            break
        if target.exists():
            target.unlink()
        if status not in (401, 403) and status is not None:
            break
    ok = target.is_file() and attempts[-1]["status"] == 200
    rec = {"file": target.name, "url": url, "status": attempts[-1]["status"],
           "bytes": target.stat().st_size if ok else 0,
           "retrieved_utc": attempts[-1]["started_utc"],
           "sha256": sha256(target) if ok else None, "attempts": attempts}
    (target.parent / (target.name + ".download.json")).write_text(
        json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    print(f"fetch: {target.name}: {rec['status']} {rec['bytes']} bytes", file=sys.stderr)
    if not ok:
        sys.exit(f"download failed: {attempts[-1]['status']} {attempts[-1]['error']}")
    return rec


# ---- the global mean

def month_label(days: float, units: str) -> str:
    base = units.split("since", 1)[1].strip().split(" ")[0]
    y, m, d = (int(x) for x in base.split("-"))
    when = dt.date(y, m, d) + dt.timedelta(days=float(days))
    return f"{when.year:04d}-{when.month:02d}"


def coslat_means(field, lat):
    """(mean, cells) per time step: cos-latitude weighted mean over the
    cells that carry a value; NaN and 0 where none does."""
    w = np.cos(np.deg2rad(np.asarray(lat, dtype=float)))[None, :, None]
    f = np.ma.masked_invalid(np.ma.asarray(field, dtype=float))
    f = np.ma.masked_where(f <= FILL_BELOW, f)
    valid = ~np.ma.getmaskarray(f)
    wsum = (w * valid).sum(axis=(1, 2))
    num = (f.filled(0.0) * w * valid).sum(axis=(1, 2))
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(wsum > 0, num / np.where(wsum > 0, wsum, 1.0), np.nan)
    return mean, valid.sum(axis=(1, 2))


def deseasonalized(labels, values):
    by = {}
    for lab, v in zip(labels, values):
        by.setdefault(lab[5:7], []).append(v)
    mean = {k: sum(v) / len(v) for k, v in by.items()}
    return [v - mean[lab[5:7]] for lab, v in zip(labels, values)]


def run(product: Path, out: Path, stamp_out: Path | None, start, end, download: dict | None):
    ds = nc.Dataset(product)
    attrs = {a: str(getattr(ds, a)).strip() for a in ds.ncattrs()}
    ident = {k: attrs.get(k) for k in IDENTITY}
    for name in (FIELD, "lat", "lon", "time"):
        if name not in ds.variables:
            sys.exit(f"{product.name} carries no variable {name}")
    var = ds.variables[FIELD]
    units = str(getattr(var, "units", ""))
    if units.replace(" ", "") not in ("Wm-2", "W/m2", "W/m^2", "W/m**2"):
        sys.exit(f"{FIELD} units are {units!r}, not W m-2")
    lat = np.asarray(ds.variables["lat"][:], dtype=float)
    lon = np.asarray(ds.variables["lon"][:], dtype=float)
    t = ds.variables["time"]
    tunits = str(t.units)
    labels = [month_label(v, tunits) for v in np.asarray(t[:], dtype=float)]
    if len(set(labels)) != len(labels):
        sys.exit("two time values fall in the same calendar month")
    means, cells = coslat_means(var[:], lat)
    product_global = None
    if PRODUCT_GLOBAL in ds.variables:
        product_global = np.ma.filled(np.ma.masked_invalid(
            np.ma.asarray(ds.variables[PRODUCT_GLOBAL][:], dtype=float)), np.nan)
    field_attrs = {a: str(getattr(var, a)) for a in var.ncattrs()}
    ds.close()

    rows, empty = [], []
    for i, lab in enumerate(labels):
        if (start and lab < start) or (end and lab > end):
            continue
        if not math.isfinite(means[i]) or cells[i] == 0:
            empty.append(lab)
            continue
        pg = float(product_global[i]) if product_global is not None and math.isfinite(product_global[i]) else None
        rows.append([lab, float(means[i]), int(cells[i]), pg])
    if len(rows) < 3:
        sys.exit("fewer than three months carry a value")
    rows.sort(key=lambda r: r[0])
    values = [r[1] for r in rows]
    des = deseasonalized([r[0] for r in rows], values)
    noise = float(np.std(np.diff(des), ddof=1) / math.sqrt(2.0))
    diffs = [r[1] - r[3] for r in rows if r[3] is not None]
    with out.open("w", encoding="utf-8", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["month", "value_W_m2", "uncertainty_W_m2", "product_global_W_m2"])
        for lab, v, _, pg in rows:
            wr.writerow([lab, f"{v:.6f}", f"{noise:.6f}", "" if pg is None else f"{pg:.6f}"])
    stamp = {
        "term": "toa-net",
        "product": ident.get("title"),
        "product_version": ident.get("version"),
        "doi": ident.get("DOI"),
        "institution": ident.get("institution"),
        "conventions": ident.get("Conventions"),
        "climatology_note": ident.get("comment"),
        "file": product.name,
        "variable": {"name": FIELD, "long_name": field_attrs.get("long_name"),
                     "standard_name": field_attrs.get("standard_name"),
                     "CF_name": field_attrs.get("CF_name"), "units": units},
        "grid": f"{len(lat)} by {len(lon)} one degree cells, latitude centres {lat.min():.1f} "
                f"to {lat.max():.1f}, longitude centres {lon.min():.1f} to {lon.max():.1f}",
        "weights": "cos-latitude at the cell centre, every cell that carries a value; the "
                   "product's own global mean (gtoa_net_all_mon, written as the fourth "
                   "column) uses the project's zonal geodetic weights, an oblate spheroid "
                   "with the solar division factor 4.0034 (the data quality summary)",
        "mask": f"none beyond the product's fill: {int(min(r[2] for r in rows))} to "
                f"{int(max(r[2] for r in rows))} of {len(lat) * len(lon)} cells carry a value",
        "aggregation": "one global mean per calendar month in W m-2, as the product carries "
                       "it: positive downward, all-sky, anchored (the anchoring block)",
        "anchoring": ANCHOR,
        "months": [rows[0][0], rows[-1][0]],
        "n_months": len(rows),
        "skipped_months": empty,
        "uncertainty_W_m2": noise,
        "uncertainty_basis": "stated noise floor: standard deviation of adjacent-month "
                             "differences of the series with its calendar-month means removed, "
                             "divided by sqrt(2); the product ships no uncertainty field",
        "published_monthly_random_error_W_m2": PUBLISHED_MONTHLY_RANDOM_ERROR_W_M2,
        "published_monthly_random_error_note": "the random error of a global monthly anomaly "
                                               "after the satellite transitions is estimated "
                                               "below 0.15 W m-2 (Loeb and others 2024, the "
                                               "dataset concept); the floor above is measured "
                                               "on this series, the published number is for "
                                               "comparison",
        "weighting_cross_check": {
            "months_compared": len(diffs),
            "mean_difference_W_m2": float(np.mean(diffs)) if diffs else None,
            "max_abs_difference_W_m2": float(np.max(np.abs(diffs))) if diffs else None,
            "rule": "cos-latitude mean minus the product's geodetic global mean, per month",
        },
        "loader": "skills/energy-budget-closure/scripts/eb_ceres_ebaf.py",
        "loader_sha256": sha256(Path(__file__).resolve()),
        "written_utc": now_utc(),
        "sources": {product.name: sha256(product)},
        "download": download,
    }
    if stamp_out:
        stamp_out.write_text(json.dumps(stamp, indent=2) + "\n", encoding="utf-8")
    print(f"toa-net.csv: {len(rows)} months {rows[0][0]} to {rows[-1][0]}, noise floor "
          f"{noise:.4f} W m-2, {len(empty)} months skipped; cos-latitude minus geodetic mean "
          f"{stamp['weighting_cross_check']['mean_difference_W_m2']} W m-2")


def selftest():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        p = d / "toy.nc"
        ds = nc.Dataset(p, "w")
        ds.title = "toy EBAF"; ds.version = "toy"; ds.DOI = "10.5067/TOY"
        ds.createDimension("time", 3); ds.createDimension("lat", 3); ds.createDimension("lon", 2)
        lat = ds.createVariable("lat", "f4", ("lat",)); lat[:] = [-60.0, 0.0, 60.0]
        lon = ds.createVariable("lon", "f4", ("lon",)); lon[:] = [0.5, 180.5]
        t = ds.createVariable("time", "f4", ("time",)); t.units = "days since 2000-03-01 00:00:00"
        t[:] = [14.0, 45.0, 75.0]
        v = ds.createVariable(FIELD, "f4", ("time", "lat", "lon")); v.units = "W m-2"
        field = np.zeros((3, 3, 2))
        field[0] = 5.0
        field[1] = np.array([[1.0], [2.0], [3.0]]) * np.ones((1, 2))
        field[2] = np.array([[1.0], [2.0], [3.0]]) * np.ones((1, 2)); field[2, 2, 0] = -999.0
        v[:] = field
        g = ds.createVariable(PRODUCT_GLOBAL, "f4", ("time",)); g.units = "W m-2"; g[:] = [5.0, 2.0, 2.1]
        ds.close()
        out = d / "toa-net.csv"
        run(p, out, d / "s.json", None, None, None)
        rows = list(csv.DictReader(out.open()))
        assert [r["month"] for r in rows] == ["2000-03", "2000-04", "2000-05"], rows
        a, b, c = (float(r["value_W_m2"]) for r in rows)
        assert abs(a - 5.0) < 1e-6, a
        assert abs(b - 2.0) < 1e-6, b                    # (0.5*1*2 + 1*2*2 + 0.5*3*2) / 4
        # one 60N cell filled: (0.5*1*2 + 1*2*2 + 0.5*3*1) / (0.5*2 + 1*2 + 0.5*1) = 6.5 / 3.5
        assert abs(c - 6.5 / 3.5) < 1e-6, c
        stamp = json.loads((d / "s.json").read_text())
        assert stamp["n_months"] == 3 and stamp["weighting_cross_check"]["months_compared"] == 3
        assert abs(stamp["weighting_cross_check"]["max_abs_difference_W_m2"] - abs(6.5 / 3.5 - 2.1)) < 1e-6
        print(f"selftest: means {a:.3f}, {b:.3f}, {c:.4f} W m-2 as planted; OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--product", type=Path); ap.add_argument("--out", type=Path)
    ap.add_argument("--stamp-out", type=Path); ap.add_argument("--start"); ap.add_argument("--end")
    ap.add_argument("--fetch", action="store_true",
                    help="download the product subset to --product when it does not exist")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest(); return
    if not (a.product and a.out):
        ap.error("--product and --out are required")
    download = None
    if a.fetch and not a.product.is_file():
        download = fetch(a.product, a.url)
    elif a.fetch:
        rec = a.product.parent / (a.product.name + ".download.json")
        download = json.loads(rec.read_text(encoding="utf-8")) if rec.is_file() else None
    if not a.product.is_file():
        sys.exit(f"{a.product} does not exist (give --fetch to download it)")
    run(a.product, a.out, a.stamp_out, a.start, a.end, download)


if __name__ == "__main__":
    main()
