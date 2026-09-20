#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy==2.4.6", "netCDF4==1.7.4"]
# ///
"""Loader for the flux terms of the attested cloud radiative effect at
the top of the atmosphere: the all-sky and clear-sky shortwave,
longwave and net fluxes of CERES EBAF Edition 4.2.1, area weighted
over each region the computation can resolve and under each clear-sky
convention the product carries, written as the data root's
cre-fluxes.csv.

What it computes, per calendar month of the product file, per region
and per clear-sky convention:

  1. The area weighted regional mean of six fields, three all-sky
     (toa_sw_all_mon, toa_lw_all_mon, toa_net_all_mon) and three
     clear-sky (the _clr_t_ triple for the total-region convention,
     the _clr_c_ triple for the cloud-free-area one). The weights are
     the CERES one degree zonal geodetic weights, the weights the
     product's own global means are formed with: an oblate spheroid
     with the equatorial radius 6378.137 km and the polar radius
     6356.752 km, the solar division factor 4.0034 rather than 4. A
     region is a band of whole one degree zones, so its mean is the
     same weighted mean restricted to those zones, which is what
     "weighted the way the product's own global mean is defined"
     means here. The loader checks itself: the weights applied to the
     global band reproduce the product's own gtoa_ global means, and
     the difference is written in the stamp.
  2. The calendar month of each time value (days since 2000-03-01,
     the mid-month day) as the row label. A month whose fields carry
     no value in a region is not a sample and is skipped; the stamp
     lists it.
  3. A per-month uncertainty floor for each of the three cloud
     radiative effect terms, per region and convention: the standard
     deviation of adjacent-month differences of that term's series
     with its calendar-month means removed, divided by sqrt(2). The
     product ships no uncertainty field, so the floor is measured on
     the series and named in the stamp; the published regional monthly
     clear-sky flux uncertainties are written beside it for
     comparison, never mixed into it.

The shortwave and longwave fields are outgoing fluxes and the net
field is downward minus upward, so the cloud radiative effect the
computation forms from these columns is clear-sky minus all-sky in
the shortwave and the longwave and all-sky minus clear-sky in the
net, which is the product's own arithmetic; the loader checks its
total-region global columns against the product's own gtoa_cre_
variables and writes that difference in the stamp too.

Which clear-sky field a convention names is the bundle's convention
concept, conventions/ceres-clear-sky-conventions.md; the loader binds
the two the energy balanced product carries and refuses to invent a
third.

The product file is read from a local path. With --fetch the file is
downloaded first when the path does not exist, from the ASDC OPeNDAP
service as a netCDF-4 subset carrying only the variables read, or
from any URL given with --url; the download is tried without
credentials, then once more with the Earthdata Login bearer token in
EARTHDATA_TOKEN sent as a request header, which is never written
anywhere. The zonal geodetic weights are read from --weights, and
with --fetch downloaded from the CERES general product information
page's weights file when that path does not exist. A download record
(URL, status, bytes, sha256, time) is written beside each file, and
the stamp copies it under sources. The product file stays where it
was downloaded, outside the data root; only the CSV and the stamp are
committed.

Usage:
  cre_ceres_fluxes.py --product FILE.nc --weights zone_weights.txt
      --out cre-fluxes.csv [--stamp-out cre-fluxes-stamp.json]
      [--start YYYY-MM] [--end YYYY-MM] [--fetch [--url URL]
      [--weights-url URL]]
  --selftest   a synthetic grid with known regional means
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

import netCDF4 as nc
import numpy as np

# The two clear-sky conventions the energy balanced product carries,
# and the variable suffix each one names. The bundle's convention
# concept states what each is and why a cloud radiative effect
# inherits the convention of the field it subtracts.
CONVENTIONS = {"total-region": "clr_t", "cloud-free-area": "clr_c"}
# The regions the computation can resolve, as bands of whole one
# degree zones, each an inclusive lower and an exclusive upper
# latitude (the northern pole zone is included in the band that ends
# at 90).
REGIONS = {
    "global": (-90.0, 90.0),
    "tropics": (-20.0, 20.0),
    "northern-extratropics": (20.0, 90.0),
    "southern-extratropics": (-90.0, -20.0),
    "northern-midlatitudes": (30.0, 60.0),
    "southern-midlatitudes": (-60.0, -30.0),
    "arctic": (60.0, 90.0),
    "antarctic": (-90.0, -60.0),
}
BANDS = ("sw", "lw", "net")
GRANULE = "CERES_EBAF_Edition4.2.1_200003-202605.nc"
COLLECTION = "C3880496704-LARC_CLOUD"
VARIABLES = ([f"toa_{b}_all_mon" for b in BANDS]
             + [f"toa_{b}_{s}_mon" for s in CONVENTIONS.values() for b in BANDS]
             + [f"toa_cre_{b}_mon" for b in BANDS]
             + [f"gtoa_{b}_all_mon" for b in BANDS]
             + [f"gtoa_{b}_{s}_mon" for s in CONVENTIONS.values() for b in BANDS]
             + [f"gtoa_cre_{b}_mon" for b in BANDS]
             + ["lat", "lon", "time"])
DEFAULT_URL = (f"https://opendap.earthdata.nasa.gov/collections/{COLLECTION}/granules/"
               f"{GRANULE}.nc4?" + ",".join(VARIABLES))
DEFAULT_WEIGHTS_URL = "https://ceres.larc.nasa.gov/documents/GZWdata/zone_weights_lou.txt"
FILL_BELOW = -998.0                    # the product's fill is -999.0
PUBLISHED_REGIONAL_MONTHLY = {
    "all_sky_W_m2": {"terra_only": 3.0, "terra_aqua": 2.5},
    "clear_sky_shortwave_W_m2": {"terra_only": 6.0, "terra_aqua": 5.0},
    "clear_sky_longwave_W_m2": {"terra_only": 5.0, "terra_aqua": 4.5},
    "note": "the one standard deviation uncertainty in a one degree regional monthly TOA flux "
            "for the Terra-only and the Terra plus Aqua periods, from Loeb and others 2018 as "
            "the bundle's EBAF dataset concept carries them; these are regional monthly "
            "uncertainties on the fluxes, not on a regional mean of a cloud radiative effect, "
            "and they are written here for comparison only, never mixed into the floor above",
}
CRE_RULE = ("the shortwave and longwave fields are outgoing fluxes and the net field is "
            "downward minus upward, so the cloud radiative effect is the clear-sky minus the "
            "all-sky flux in the shortwave and the longwave and the all-sky minus the "
            "clear-sky flux in the net, which is the product's own arithmetic (the data "
            "quality summary: cloud radiative effects are computed as all-sky flux minus "
            "clear-sky flux, the net being downward minus upward)")
COLUMNS = ["region", "convention", "month", "sw_all_W_m2", "lw_all_W_m2", "net_all_W_m2",
           "sw_clr_W_m2", "lw_clr_W_m2", "net_clr_W_m2", "cre_sw_uncertainty_W_m2",
           "cre_lw_uncertainty_W_m2", "cre_net_uncertainty_W_m2"]
IDENTITY = ("title", "institution", "Conventions", "version", "DOI", "comment")
WEIGHT_LINE = re.compile(r"^\s*(-?\d+\.\d+)\s+(\d+\.\d+)\s*$")


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
            with urllib.request.urlopen(req, timeout=3600) as r, target.open("wb") as f:
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


# ---- the weights

def read_weights(path: Path) -> dict:
    """The CERES one degree zonal geodetic weights, keyed by the zone's
    centre latitude rounded to two decimals."""
    table = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = WEIGHT_LINE.match(line)
        if m:
            table[round(float(m.group(1)), 2)] = float(m.group(2))
    if len(table) != 180:
        sys.exit(f"{path.name}: {len(table)} one degree zonal weights read, expected 180")
    total = sum(table.values())
    if abs(total - 1.0) > 1e-3:
        sys.exit(f"{path.name}: the zonal weights sum to {total}, not 1")
    return table


def weight_vector(table: dict, lat) -> np.ndarray:
    try:
        return np.array([table[round(float(x), 2)] for x in lat], dtype=float)
    except KeyError as e:
        sys.exit(f"the weights file carries no zone for latitude {e}")


# ---- the regional means

def month_label(days: float, units: str) -> str:
    base = units.split("since", 1)[1].strip().split(" ")[0]
    y, m, d = (int(x) for x in base.split("-"))
    when = dt.date(y, m, d) + dt.timedelta(days=float(days))
    return f"{when.year:04d}-{when.month:02d}"


def band_mask(lat, lo: float, hi: float) -> np.ndarray:
    """The zones of a region: centres at or above lo and below hi, the
    zone that ends at the north pole included."""
    lat = np.asarray(lat, dtype=float)
    return (lat >= lo) & ((lat < hi) | (hi >= 90.0))


def regional_means(field, w: np.ndarray, sel: np.ndarray):
    """(mean, cells) per time step over the selected zones: the zonal
    geodetic weight of each zone spread evenly over its cells, every
    cell that carries a value; NaN and 0 where none does."""
    f = np.ma.masked_invalid(np.ma.asarray(field, dtype=float))
    f = np.ma.masked_where(f <= FILL_BELOW, f)
    valid = (~np.ma.getmaskarray(f))[:, sel, :]
    ncol = f.shape[2]
    ww = (w[sel][None, :, None] / float(ncol)) * valid
    wsum = ww.sum(axis=(1, 2))
    num = (f.filled(0.0)[:, sel, :] * ww).sum(axis=(1, 2))
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(wsum > 0, num / np.where(wsum > 0, wsum, 1.0), np.nan)
    return mean, valid.sum(axis=(1, 2))


def deseasonalized(labels, values):
    by = {}
    for lab, v in zip(labels, values):
        by.setdefault(lab[5:7], []).append(v)
    mean = {k: sum(v) / len(v) for k, v in by.items()}
    return [v - mean[lab[5:7]] for lab, v in zip(labels, values)]


def noise_floor(labels, values) -> float:
    """The stated per-month floor: the standard deviation of
    adjacent-month differences of the deseasonalized series over
    sqrt(2)."""
    des = deseasonalized(labels, values)
    if len(des) < 3:
        return float("nan")
    return float(np.std(np.diff(des), ddof=1) / math.sqrt(2.0))


def run(product: Path, weights_path: Path, out: Path, stamp_out, start, end,
        download, weights_download):
    ds = nc.Dataset(product)
    attrs = {a: str(getattr(ds, a)).strip() for a in ds.ncattrs()}
    ident = {k: attrs.get(k) for k in IDENTITY}
    needed = ([f"toa_{b}_all_mon" for b in BANDS]
              + [f"toa_{b}_{s}_mon" for s in CONVENTIONS.values() for b in BANDS]
              + ["lat", "lon", "time"])
    for name in needed:
        if name not in ds.variables:
            sys.exit(f"{product.name} carries no variable {name}")
    for name in needed:
        if name in ("lat", "lon", "time"):
            continue
        units = str(getattr(ds.variables[name], "units", ""))
        if units.replace(" ", "") not in ("Wm-2", "W/m2", "W/m^2", "W/m**2"):
            sys.exit(f"{name} units are {units!r}, not W m-2")
    lat = np.asarray(ds.variables["lat"][:], dtype=float)
    lon = np.asarray(ds.variables["lon"][:], dtype=float)
    t = ds.variables["time"]
    labels = [month_label(v, str(t.units)) for v in np.asarray(t[:], dtype=float)]
    if len(set(labels)) != len(labels):
        sys.exit("two time values fall in the same calendar month")
    table = read_weights(weights_path)
    w = weight_vector(table, lat)

    fields = {name: ds.variables[name][:] for name in needed
              if name not in ("lat", "lon", "time")}
    product_global = {name: np.ma.filled(np.ma.masked_invalid(
        np.ma.asarray(ds.variables[name][:], dtype=float)), np.nan)
        for name in ds.variables if name.startswith("gtoa_")}
    field_attrs = {name: {a: str(getattr(ds.variables[name], a))
                          for a in ds.variables[name].ncattrs()}
                   for name in needed if name not in ("lat", "lon", "time")}
    ds.close()

    keep = [i for i, lab in enumerate(labels)
            if not ((start and lab < start) or (end and lab > end))]
    if len(keep) < 3:
        sys.exit("fewer than three months lie in the range asked for")
    rows, skipped, floors, cells_seen = [], {}, {}, {}
    for region, (lo, hi) in REGIONS.items():
        sel = band_mask(lat, lo, hi)
        if not sel.any():
            sys.exit(f"the region {region} selects no zone of this grid")
        means = {name: regional_means(fields[name], w, sel) for name in fields}
        cells_seen[region] = [int(min(means[n][1][i] for n in fields for i in keep)),
                              int(max(means[n][1][i] for n in fields for i in keep))]
        for convention, suffix in CONVENTIONS.items():
            use, empty = [], []
            for i in keep:
                vals = {}
                ok = True
                for b in BANDS:
                    a_i, c_i = means[f"toa_{b}_all_mon"][0][i], means[f"toa_{b}_{suffix}_mon"][0][i]
                    if not (math.isfinite(a_i) and math.isfinite(c_i)):
                        ok = False
                        break
                    vals[f"{b}_all"], vals[f"{b}_clr"] = float(a_i), float(c_i)
                if ok:
                    use.append((labels[i], vals))
                else:
                    empty.append(labels[i])
            if len(use) < 3:
                sys.exit(f"{region}/{convention}: fewer than three months carry a value")
            labs = [u[0] for u in use]
            cre = {"sw": [v["sw_clr"] - v["sw_all"] for _, v in use],
                   "lw": [v["lw_clr"] - v["lw_all"] for _, v in use],
                   "net": [v["net_all"] - v["net_clr"] for _, v in use]}
            floor = {b: noise_floor(labs, cre[b]) for b in BANDS}
            floors[f"{region}/{convention}"] = {
                "cre_sw_W_m2": floor["sw"], "cre_lw_W_m2": floor["lw"],
                "cre_net_W_m2": floor["net"], "n_months": len(use),
                "window_mean_cre_sw_W_m2": float(np.mean(cre["sw"])),
                "window_mean_cre_lw_W_m2": float(np.mean(cre["lw"])),
                "window_mean_cre_net_W_m2": float(np.mean(cre["net"])),
                "decomposition_max_abs_W_m2": float(np.max(np.abs(
                    np.array(cre["net"]) - np.array(cre["sw"]) - np.array(cre["lw"])))),
            }
            if empty:
                skipped[f"{region}/{convention}"] = empty
            for lab, v in use:
                rows.append([region, convention, lab,
                             f"{v['sw_all']:.6f}", f"{v['lw_all']:.6f}", f"{v['net_all']:.6f}",
                             f"{v['sw_clr']:.6f}", f"{v['lw_clr']:.6f}", f"{v['net_clr']:.6f}",
                             f"{floor['sw']:.6f}", f"{floor['lw']:.6f}", f"{floor['net']:.6f}"])
    rows.sort(key=lambda r: (r[0], r[1], r[2]))
    with out.open("w", encoding="utf-8", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(COLUMNS)
        wr.writerows(rows)

    # the loader checks itself against the product's own global means
    sel_global = band_mask(lat, *REGIONS["global"])
    weighting_check, cre_check = {}, {}
    for name in fields:
        g = product_global.get("g" + name)
        if g is None:
            continue
        mine = regional_means(fields[name], w, sel_global)[0]
        d = [abs(mine[i] - g[i]) for i in keep if math.isfinite(g[i]) and math.isfinite(mine[i])]
        weighting_check[name] = {"months_compared": len(d),
                                 "max_abs_difference_W_m2": max(d) if d else None}
    for b in BANDS:
        g = product_global.get(f"gtoa_cre_{b}_mon")
        if g is None:
            continue
        allm = regional_means(fields[f"toa_{b}_all_mon"], w, sel_global)[0]
        clrm = regional_means(fields[f"toa_{b}_clr_t_mon"], w, sel_global)[0]
        mine = (allm - clrm) if b == "net" else (clrm - allm)
        d = [abs(mine[i] - g[i]) for i in keep if math.isfinite(g[i]) and math.isfinite(mine[i])]
        cre_check[f"cre_{b}"] = {"months_compared": len(d),
                                 "max_abs_difference_W_m2": max(d) if d else None}

    months = sorted({r[2] for r in rows})
    stamp = {
        "term": "cre-fluxes",
        "product": ident.get("title"),
        "product_version": ident.get("version"),
        "doi": ident.get("DOI"),
        "institution": ident.get("institution"),
        "conventions_attribute": ident.get("Conventions"),
        "climatology_note": ident.get("comment"),
        "file": product.name,
        "variables": {name: {"long_name": field_attrs[name].get("long_name"),
                             "standard_name": field_attrs[name].get("standard_name"),
                             "CF_name": field_attrs[name].get("CF_name"),
                             "units": field_attrs[name].get("units")}
                      for name in sorted(fields)},
        "clear_sky_conventions": {
            name: {"variable_suffix": suffix,
                   "variables": [f"toa_{b}_{suffix}_mon" for b in BANDS],
                   "long_name": field_attrs[f"toa_net_{suffix}_mon"].get("long_name")}
            for name, suffix in CONVENTIONS.items()},
        "cre_rule": CRE_RULE,
        "grid": f"{len(lat)} by {len(lon)} one degree cells, latitude centres {lat.min():.1f} "
                f"to {lat.max():.1f}, longitude centres {lon.min():.1f} to {lon.max():.1f}",
        "weights": "the CERES one degree zonal geodetic weights, the weights the product's own "
                   "global means are formed with (an oblate spheroid, the equatorial radius "
                   "6378.137 km and the polar radius 6356.752 km, the solar division factor "
                   "4.0034 rather than 4); each zone's weight spread evenly over the cells of "
                   "that zone that carry a value",
        "weights_file": weights_path.name,
        "weights_sha256": sha256(weights_path),
        "weights_zones": len(table),
        "weights_sum": sum(table.values()),
        "weights_source": DEFAULT_WEIGHTS_URL,
        "regions": {name: {"latitude_band": [lo, hi],
                           "weight_share": sum(v for k, v in table.items()
                                               if band_mask(np.array([k]), lo, hi)[0]),
                           "zones": int(band_mask(lat, lo, hi).sum()),
                           "cells_with_a_value": cells_seen[name]}
                    for name, (lo, hi) in REGIONS.items()},
        "mask": "latitude bands of whole one degree zones; no surface type mask, since the "
                "subset read carries no surface type field, so a land or ocean region is not "
                "resolvable here and the computation refuses one",
        "aggregation": "one area weighted regional mean per calendar month per field in W m-2, "
                       "as the product carries them; the cloud radiative effect terms are "
                       "formed by the computation from these columns",
        "months": [months[0], months[-1]],
        "n_months": len(months),
        "skipped_months": skipped,
        "uncertainty_basis": "stated noise floor, per region and convention: standard deviation "
                             "of adjacent-month differences of that cloud radiative effect "
                             "term's series with its calendar-month means removed, divided by "
                             "sqrt(2); the product ships no uncertainty field",
        "uncertainty_floors": floors,
        "published_regional_monthly_uncertainty": PUBLISHED_REGIONAL_MONTHLY,
        "weighting_cross_check": {
            "rule": "the zonal geodetic weights applied here over the global band against the "
                    "product's own gtoa_ global means, per month",
            "fields": weighting_check},
        "product_cre_cross_check": {
            "rule": "the total-region cloud radiative effect formed here over the global band "
                    "against the product's own gtoa_cre_ variables, per month; the product's "
                    "cloud radiative effect variables are the total-region convention alone, "
                    "as their long names state, so the cloud-free-area convention has no such "
                    "cross-check",
            "terms": cre_check},
        "loader": "skills/cloud-radiative-effect/scripts/cre_ceres_fluxes.py",
        "loader_sha256": sha256(Path(__file__).resolve()),
        "written_utc": now_utc(),
        "sources": {product.name: sha256(product), weights_path.name: sha256(weights_path)},
        "download": download,
        "weights_download": weights_download,
    }
    if stamp_out:
        Path(stamp_out).write_text(json.dumps(stamp, indent=2) + "\n", encoding="utf-8")
    g = floors["global/total-region"]
    c = floors["global/cloud-free-area"]
    seen = [v["max_abs_difference_W_m2"] for v in weighting_check.values()
            if v["max_abs_difference_W_m2"] is not None]
    cross = f"{max(seen):.2e} W m-2" if seen else "not available (no gtoa_ global means in the file)"
    print(f"cre-fluxes.csv: {len(rows)} rows, {len(REGIONS)} regions by "
          f"{len(CONVENTIONS)} conventions by {len(months)} months {months[0]} to {months[-1]}; "
          f"global net cloud radiative effect {g['window_mean_cre_net_W_m2']:+.3f} "
          f"(total-region) against {c['window_mean_cre_net_W_m2']:+.3f} (cloud-free-area) "
          f"W m-2 over the months read; weighting cross-check max {cross}")


def selftest():
    """A three month, three zone grid whose regional means are known by
    hand, so the weighting, the conventions and the sign rule are
    checked without a product file."""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        weights = d / "weights.txt"
        lats = [round(-89.5 + i, 2) for i in range(180)]
        lines = ["lat     weight"]
        for k in lats:
            lines.append(f" {k:6.2f}  {1.0 / 180.0:.6f}")
        weights.write_text("\n".join(lines) + "\n", encoding="utf-8")
        p = d / "toy.nc"
        ds = nc.Dataset(p, "w")
        ds.title = "toy EBAF"
        ds.version = "toy"
        ds.DOI = "10.5067/TOY"
        ds.createDimension("time", 3)
        ds.createDimension("lat", 180)
        ds.createDimension("lon", 2)
        lat = ds.createVariable("lat", "f4", ("lat",))
        lat[:] = lats
        lon = ds.createVariable("lon", "f4", ("lon",))
        lon[:] = [0.5, 180.5]
        t = ds.createVariable("time", "f4", ("time",))
        t.units = "days since 2000-03-01 00:00:00"
        t[:] = [14.0, 45.0, 75.0]
        # a planted all-sky field with a planted cloud radiative effect
        # of the order of the real one: the shortwave clear-sky field
        # sits 45 (total-region) and 46 (cloud-free-area) below the
        # all-sky one, the longwave clear-sky field 26 and 28 above it.
        planted = {"sw": (99.0, -45.0, -46.0), "lw": (240.0, 26.0, 28.0)}
        for b in ("sw", "lw"):
            base, dt_, dc = planted[b]
            for suffix, off in (("all", 0.0), ("clr_t", dt_), ("clr_c", dc)):
                v = ds.createVariable(f"toa_{b}_{suffix}_mon", "f4", ("time", "lat", "lon"))
                v.units = "W m-2"
                v[:] = np.full((3, 180, 2), base + off)
        for suffix in ("all", "clr_t", "clr_c"):
            v = ds.createVariable(f"toa_net_{suffix}_mon", "f4", ("time", "lat", "lon"))
            v.units = "W m-2"
            sw = planted["sw"][0] + (0.0 if suffix == "all" else
                                     planted["sw"][1] if suffix == "clr_t" else planted["sw"][2])
            lw = planted["lw"][0] + (0.0 if suffix == "all" else
                                     planted["lw"][1] if suffix == "clr_t" else planted["lw"][2])
            v[:] = np.full((3, 180, 2), 340.0 - sw - lw)
        for b in ("sw", "lw", "net"):
            for suffix in ("all", "clr_t", "clr_c"):
                gv = ds.createVariable(f"gtoa_{b}_{suffix}_mon", "f4", ("time",))
                gv.units = "W m-2"
                gv[:] = np.asarray(ds.variables[f"toa_{b}_{suffix}_mon"][:]).mean(axis=(1, 2))
        for b, off in (("sw", -45.0), ("lw", 26.0), ("net", -19.0)):
            gv = ds.createVariable(f"gtoa_cre_{b}_mon", "f4", ("time",))
            gv.units = "W m-2"
            gv[:] = np.full(3, off)
        # one filled cell in the last month of the northernmost zone
        arr = ds.variables["toa_sw_all_mon"][:]
        arr[2, 179, 0] = -999.0
        ds.variables["toa_sw_all_mon"][:] = arr
        ds.close()
        out, stamp_out = d / "cre-fluxes.csv", d / "s.json"
        run(p, weights, out, stamp_out, None, None, None, None)
        rows = list(csv.DictReader(out.open()))
        assert len(rows) == len(REGIONS) * len(CONVENTIONS) * 3, len(rows)
        got = {(r["region"], r["convention"], r["month"]): r for r in rows}
        g = got[("global", "total-region", "2000-03")]
        assert abs(float(g["sw_all_W_m2"]) - 99.0) < 1e-6, g
        assert abs(float(g["sw_clr_W_m2"]) - 54.0) < 1e-6, g
        assert abs(float(g["lw_clr_W_m2"]) - 266.0) < 1e-6, g
        # the sign rule: shortwave and longwave cloud effects from the
        # outgoing fields, the net from the net field, and the three agree
        for conv, (dsw, dlw) in (("total-region", (-45.0, 26.0)),
                                 ("cloud-free-area", (-46.0, 28.0))):
            r = got[("tropics", conv, "2000-04")]
            cre_sw = float(r["sw_clr_W_m2"]) - float(r["sw_all_W_m2"])
            cre_lw = float(r["lw_clr_W_m2"]) - float(r["lw_all_W_m2"])
            cre_net = float(r["net_all_W_m2"]) - float(r["net_clr_W_m2"])
            assert abs(cre_sw - dsw) < 1e-4 and abs(cre_lw - dlw) < 1e-4, r
            assert abs(cre_net - (cre_sw + cre_lw)) < 1e-4, (cre_net, cre_sw, cre_lw)
        stamp = json.loads(stamp_out.read_text())
        assert stamp["n_months"] == 3
        assert set(stamp["regions"]) == set(REGIONS)
        assert abs(stamp["regions"]["global"]["weight_share"] - 1.0) < 1e-3
        assert abs(stamp["regions"]["tropics"]["weight_share"] - 40.0 / 180.0) < 1e-3
        assert stamp["regions"]["arctic"]["zones"] == 30
        # the filled cell is dropped from the mean, not interpolated
        assert stamp["regions"]["arctic"]["cells_with_a_value"][0] == 59, stamp["regions"]["arctic"]
        # the loader's own global means reproduce the planted gtoa_ series, and
        # its total-region cloud effect reproduces the planted gtoa_cre_ series
        wc = stamp["weighting_cross_check"]["fields"]
        assert len(wc) == 9 and all(v["max_abs_difference_W_m2"] < 1e-4 for v in wc.values()), wc
        cc = stamp["product_cre_cross_check"]["terms"]
        assert set(cc) == {"cre_sw", "cre_lw", "cre_net"}, cc
        assert all(v["max_abs_difference_W_m2"] < 1e-4 for v in cc.values()), cc
        print(f"cre_ceres_fluxes selftest: {len(rows)} rows, global shortwave cloud effect "
              f"-45.000 and longwave +26.000 W m-2 as planted, net -19.000; OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--product", type=Path)
    ap.add_argument("--weights", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--stamp-out", type=Path)
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--fetch", action="store_true",
                    help="download the product subset and the weights when they do not exist")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--weights-url", default=DEFAULT_WEIGHTS_URL)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    if not (a.product and a.out and a.weights):
        ap.error("--product, --weights and --out are required")
    download, weights_download = None, None
    for path, url, slot in ((a.product, a.url, "product"), (a.weights, a.weights_url, "weights")):
        rec = None
        if a.fetch and not path.is_file():
            rec = fetch(path, url)
        elif a.fetch:
            side = path.parent / (path.name + ".download.json")
            rec = json.loads(side.read_text(encoding="utf-8")) if side.is_file() else None
        if not path.is_file():
            sys.exit(f"{path} does not exist (give --fetch to download it)")
        if slot == "product":
            download = rec
        else:
            weights_download = rec
    run(a.product, a.weights, a.out, a.stamp_out, a.start, a.end, download, weights_download)


if __name__ == "__main__":
    main()
