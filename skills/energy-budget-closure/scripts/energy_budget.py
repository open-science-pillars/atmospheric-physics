#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Sanctioned computation for the attested energy budget closure: the
CERES EBAF net top-of-atmosphere flux against the Argo ocean heat
content change over one stated window.

Contract: knowledge/computations/energy-budget.md. Over one window of
calendar months, the receipt carries four rate terms in watts per
square metre of the Earth's surface, each with an uncertainty and the
stamp it came from:

  toa_net       the window mean of the EBAF global mean net TOA flux
                (all-sky, positive downward) as the product's own
                geodetically weighted global mean carries it, since the
                product's anchor is defined on that mean; the
                uncertainty is the anchor's in situ uncertainty (0.10
                W m-2, 95 percent) in quadrature with the larger of
                the sampling half width of the window mean under a
                lag-1 autocorrelated residual and the formal error the
                per-month floor propagates;
  ohc_0_2000    the 0 to 2000 dbar ocean heat content rate over the
                same window, read from the ocean-science Argo
                computation's receipt (terms.trend, ZJ per year with
                its uncertainty) and converted with the Earth's surface
                area; the receipt's own per-area rate must agree;
  deep_ocean    the ocean below 2000 m, which the Argo receipt states
                as an omission: the published rate, with its source,
                as a term here;
  non_ocean     land, cryosphere and atmosphere, published rates with
                their sources.

The residual is toa_net minus the sum of the three ocean-side terms;
the combined uncertainty is the four in quadrature; the verdict
closed_within_uncertainty says whether the radiation and the heat
inventory agree over the window. The same four terms are also stated
as energy over the window in zettajoules (rate times the window length
times the Earth's area), beside the Argo receipt's own fitted and
endpoint changes.

The anchoring caveat (the bundle's gotcha): the EBAF global mean net
flux was set once to an in situ heat uptake over July 2005 through
June 2015, so the toa_net term is not independent of ocean heating
over the months the window shares with that decade; the receipt
counts those months. What the ocean data did not set is the
variation, so the receipt also carries the EBAF net flux anomaly
against the window's own mean, formed from the cos-latitude weighted
global mean of the one degree grid, with its linear trend over the
window (W m-2 per decade, a 95 percent interval under the AR(1)
residual model) and the distance of that trend from the published
satellite and in situ trend of the Earth's energy imbalance; the
anchor cancels in the anomaly and in its trend.

Two input modes. --data-root DIR reads toa-net.csv (month, value_W_m2
the cos-latitude mean, uncertainty_W_m2, product_global_W_m2 the
product's geodetic mean), the loader's stamp, the RECORD.json the
data-root tool wrote (every file checked against its manifest), and
the Argo receipt (--ohc-receipt PATH, default DIR/ohc-2000-receipt.json).
--fixture [--seed N] generates a synthetic record deterministically (a
hash-based Gaussian stream): a monthly net flux 2000-03 through
2026-05 with a planted level and a planted trend, an annual cycle, an
interannual AR(1) component and noise at the stated per-month
uncertainty, a planted geodetic offset, and a planted ocean-side
receipt whose rate closes the budget by construction, so the receipt
shows the planted level, trend and closure recovered.

Refusals, exit 3 with a refusal receipt and never a number: a window
outside the radiation record (window-outside-record); an Argo receipt
whose window is not the window asked for (ohc-window-mismatch), since
its rate is a whole-window quantity; an Argo receipt that is itself a
refusal (ohc-receipt-refused); fewer than 24 months in the window
(too-few-months); a trend whose interval cannot be stated
(interval-not-stated).

The receipt's run_id digests the receipt without its timestamp; the
data root and the receipt path are recorded package-relative when they
sit under this package, so a record run reproduces its id on any
machine. Consumers bind values for the declared parameters and MUST
NOT edit this file; the attester hashes it, regenerates the fixture at
the receipt's seed, and recomputes every number from the receipt.

  energy_budget.py --window YYYY-MM:YYYY-MM --runtime NAME
      (--fixture [--seed N] | --data-root DIR [--ohc-receipt PATH])
      [--runtime-version V] [--receipt PATH] [--capability-root DIR]
"""

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMPUTATION = "skills/energy-budget-closure/scripts/energy_budget.py"
OHC_COMPUTATION = "references/computations/argo_ohc.py"
OHC_DEPTH = 2000

FIXTURE_SPAN = ("2000-03", "2026-05")
MIN_MONTHS = 24
CONFIDENCE = 0.95
MIN_DOF = 1.0
Z95 = 1.959963984540054              # two-sided 95 percent normal quantile
SECONDS_PER_YEAR = 365.25 * 86400.0
EARTH_RADIUS_M = 6371000.0           # the mean radius, the Argo receipt's convention
EARTH_AREA_M2 = 4.0 * math.pi * EARTH_RADIUS_M ** 2
ZJ = 1.0e21
REL_TOL = 1e-6                       # agreement demanded of the Argo receipt's own per-area rate

ANCHOR = {
    "value_W_m2": 0.71, "uncertainty_W_m2": 0.10, "period": ["2005-07", "2015-06"],
    "editions": "Edition 4.0 through 4.2.1",
    "statement": "the EBAF global mean net TOA flux over July 2005 through June 2015 is set "
                 "to the in situ heat uptake of 0.71 W m-2 (0.10 at the 95 percent level) by a "
                 "one-time adjustment of the shortwave and longwave fluxes; the mean over any "
                 "window therefore carries that anchor and its uncertainty, and over the months "
                 "a window shares with the decade it is the in situ estimate, not a radiometric "
                 "one",
    "source": "the bundle's gotcha ebaf-imbalance-anchored-to-ocean-heating; the CERES_EBAF "
              "Ed4.2 Data Quality Summary version 7 (2026-07-01) and the Ed4.0 summary "
              "(2018-01-12); Loeb and others (2018), doi:10.1175/JCLI-D-17-0208.1; Johnson, "
              "Lyman and Loeb (2016), doi:10.1038/nclimate3043",
}
DEEP_OCEAN = {
    "layer": "below 2000 m",
    "value_W_m2": 0.06, "uncertainty_W_m2": 0.03,
    "value_ZJ_yr": 0.97, "uncertainty_ZJ_yr": 0.48,
    "period": "1992 to 2020, a constant linear trend",
    "statement": "the ocean below 2000 dbar is not sampled by the Argo core array or the "
                 "Roemmich and Gilson product and is not in the Argo receipt's terms; the "
                 "published rate enters this budget as a term of its own, with its source",
    "source": "von Schuckmann and others (2023), Heat stored in the Earth system 1960 to "
              "2020: where does the energy go?, Earth System Science Data 15, 1675 to 1709, "
              "doi:10.5194/essd-15-1675-2023, section 2 (the deep ocean below 2000 m, updating "
              "Purkey and Johnson 2010, doi:10.1175/2010JCLI3682.1)",
}
NON_OCEAN = {
    "components": {
        "land": {"value_W_m2": 0.038, "uncertainty_W_m2": 0.013,
                 "basis": "about 5 percent of the 0.76 plus or minus 0.2 W m-2 Earth energy "
                          "imbalance the inventory states for 2006 to 2020 (section 6 and "
                          "figure 9); the uncertainty is the one percentage point the fraction "
                          "is rounded to and the fraction of the total's uncertainty, in "
                          "quadrature"},
        "cryosphere": {"value_W_m2": 0.030, "uncertainty_W_m2": 0.011,
                       "basis": "about 4 percent of the same 0.76 plus or minus 0.2 W m-2 "
                                "(section 6 and figure 9), the uncertainty formed the same way"},
        "atmosphere": {"value_W_m2": 0.0142, "uncertainty_W_m2": 0.0040,
                       "basis": "the global atmospheric heat content gain of 7.25 plus or minus "
                                "1.72 TW over 2006 to 2020 (Table 2, a 90 percent range, scaled "
                                "to 95 percent by 1.960 over 1.645 to 2.05 TW) over the Earth's "
                                "surface area of 5.10e14 m2"},
    },
    "period": "2006 to 2020",
    "source": "von Schuckmann and others (2023), Earth System Science Data 15, 1675 to 1709, "
              "doi:10.5194/essd-15-1675-2023: section 6 (the fractions of the inventory since "
              "2006: ocean about 89 percent, land about 5, cryosphere about 4, atmosphere "
              "about 2) and Table 2 (the atmospheric heat content gain)",
    "rule": "the three components summed; their uncertainties in quadrature",
}
PUBLISHED_EEI = {
    "value_W_m2": 0.76, "uncertainty_W_m2": 0.2, "period": "2006 to 2020",
    "statement": "the Earth energy imbalance the heat inventory states for 2006 to 2020, the "
                 "sum of every component's heat gain over the Earth's surface",
    "source": "von Schuckmann and others (2023), doi:10.5194/essd-15-1675-2023, section 6 "
              "and figure 8",
}
PUBLISHED_TREND = {
    "value_W_m2_per_decade": 0.50, "uncertainty_W_m2_per_decade": 0.47,
    "period": "mid-2005 to mid-2019", "confidence": "5 to 95 percent",
    "statement": "independent satellite (CERES) and in situ observations each yield "
                 "statistically indistinguishable decadal increases in the Earth's energy "
                 "imbalance of 0.50 plus or minus 0.47 W m-2 per decade",
    "source": "Loeb and others (2021), Satellite and Ocean Data Reveal Marked Increase in "
              "Earth's Heating Rate, Geophysical Research Letters 48, e2021GL093047, "
              "doi:10.1029/2021GL093047 (the abstract on the Crossref registry record; the "
              "journal page sits behind a bot check)",
}
TRUTH = {                             # what the fixture imposes
    "level_W_m2_coslat_at_2010_07": 0.95,
    "trend_W_m2_per_decade": 0.50,
    "annual_amplitude_W_m2": 8.5, "annual_peak_month": 1,
    "noise_sigma_W_m2": 0.25,
    "interannual_ar1": {"phi": 0.8, "sigma_W_m2": 0.35},
    "geodetic_offset_W_m2": -0.218, "geodetic_offset_seasonal_W_m2": 0.05,
    "ohc_uncertainty_ZJ_yr": 1.2,
    "fixture_domain_area_m2": 3.06e14,
    "basis": "the level is the order of the cos-latitude mean of the real record over the "
             "anchor decade, the trend the published 0.50 W m-2 per decade, the annual cycle "
             "the order of the product's global net flux cycle, the geodetic offset the "
             "order the loader measured between the two weightings; the planted ocean rate "
             "is the planted geodetic window mean minus the deep and non-ocean terms, so the "
             "budget closes by construction up to the noise",
}
FIXTURE_BOOKKEEPING = {
    "anchoring": {"statement": "synthetic: the planted level stands in for the anchored mean; "
                               "the anchor's uncertainty is still carried on the toa_net term "
                               "so the fixture bar is the real bar's shape"},
    "weighting": {"statement": "synthetic: a planted offset between the cos-latitude mean and "
                               "the product's geodetic mean, constant plus a seasonal part"},
    "edition": {"statement": "synthetic: no product; a real run names the edition, the release "
                             "date and the file"},
    "uncertainty": {"basis": "synthetic: the per-month uncertainty is the noise sigma the "
                             "fixture generated the series with"},
    "ocean_input": {"statement": "synthetic: a planted Argo-shaped receipt block whose rate "
                                 "closes the budget by construction"},
}
REQUIRED_BOOKKEEPING = (
    ("anchoring", "statement"), ("weighting", "statement"), ("edition", "statement"),
    ("uncertainty", "basis"), ("ocean_input", "statement"),
)
REASONS = ("window-outside-record", "ohc-window-mismatch", "ohc-receipt-refused",
           "too-few-months", "interval-not-stated")


# ---- months

def ym(date: str) -> int:
    return int(date[:4]) * 12 + int(date[5:7]) - 1


def label(k: int) -> str:
    return f"{k // 12:04d}-{k % 12 + 1:02d}"


def parse_window(window: str):
    m = re.fullmatch(r"(\d{4}-\d{2}):(\d{4}-\d{2})", window or "")
    if not m or not (1 <= int(m.group(1)[5:]) <= 12 and 1 <= int(m.group(2)[5:]) <= 12) \
            or ym(m.group(1)) > ym(m.group(2)):
        raise SystemExit(f"window must be YYYY-MM:YYYY-MM, got {window!r}")
    return m.group(1), m.group(2)


def overlap_months(start: str, end: str, period) -> int:
    lo, hi = max(ym(start), ym(period[0])), min(ym(end), ym(period[1]))
    return max(0, hi - lo + 1)


# ---- the fixture

def normals(seed: int, stream: str, n: int):
    """A deterministic standard-normal stream: SHA-256 in counter mode
    for the uniforms, Box-Muller for the pair. Stdlib only, so the
    fixture digest is the same on every platform and library release."""
    out, counter = [], 0
    scale = 2.0 ** 64 + 2.0
    while len(out) < n:
        h = hashlib.sha256(f"{seed}:{stream}:{counter}".encode()).digest()
        u1 = (int.from_bytes(h[:8], "big") + 1) / scale
        u2 = (int.from_bytes(h[8:16], "big") + 1) / scale
        r = math.sqrt(-2.0 * math.log(u1))
        out.append(r * math.cos(2.0 * math.pi * u2))
        out.append(r * math.sin(2.0 * math.pi * u2))
        counter += 1
    return out[:n]


def ar1(seed: int, stream: str, n: int, phi: float, sigma: float):
    e = normals(seed, stream, n)
    x = [e[0] * sigma / math.sqrt(1.0 - phi * phi)]
    for i in range(1, n):
        x.append(phi * x[-1] + sigma * e[i])
    return x


def fixture_deterministic(i: int, month: int):
    """The noise-free cos-latitude net flux at month index i (from the
    fixture's first month) and the geodetic offset that month."""
    t = TRUTH
    years_from_ref = (i - (ym("2010-07") - ym(FIXTURE_SPAN[0]))) / 12.0
    coslat = (t["level_W_m2_coslat_at_2010_07"] + t["trend_W_m2_per_decade"] / 10.0 * years_from_ref
              + t["annual_amplitude_W_m2"]
              * math.cos(2.0 * math.pi * (month - t["annual_peak_month"]) / 12.0))
    offset = (t["geodetic_offset_W_m2"]
              + t["geodetic_offset_seasonal_W_m2"] * math.cos(2.0 * math.pi * (month - 4) / 12.0))
    return coslat, offset


def make_fixture(seed: int) -> dict:
    t = TRUTH
    k0, k1 = ym(FIXTURE_SPAN[0]), ym(FIXTURE_SPAN[1])
    n = k1 - k0 + 1
    dates = [label(k) for k in range(k0, k1 + 1)]
    e = normals(seed, "toa-net", n)
    inter = ar1(seed, "toa-net-interannual", n, t["interannual_ar1"]["phi"],
                t["interannual_ar1"]["sigma_W_m2"])
    coslat, product, uncs = [], [], []
    for i, d in enumerate(dates):
        base, offset = fixture_deterministic(i, int(d[5:7]))
        v = base + inter[i] + t["noise_sigma_W_m2"] * e[i]
        coslat.append(v)
        product.append(v + offset)
        uncs.append(t["noise_sigma_W_m2"])
    return {"seed": seed, "span": list(FIXTURE_SPAN),
            "series": {"dates": dates, "value_W_m2": coslat, "uncertainty_W_m2": uncs,
                       "product_global_W_m2": product}}


def fixture_digest(fx: dict) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(fx, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def fixture_truth_window(start: str, end: str) -> dict:
    """The planted values for a window: the noise-free geodetic window
    mean, the planted trend, and the planted ocean rate that closes the
    budget by construction."""
    k0, kf = ym(start), ym(FIXTURE_SPAN[0])
    n = ym(end) - k0 + 1
    means = [sum(fixture_deterministic(k0 - kf + j, (k0 + j) % 12 + 1)) for j in range(n)]
    geodetic_mean = sum(means) / n
    ocean_rate = geodetic_mean - DEEP_OCEAN["value_W_m2"] - non_ocean_total()["value_W_m2"]
    return {"geodetic_window_mean_W_m2": geodetic_mean,
            "trend_W_m2_per_decade": TRUTH["trend_W_m2_per_decade"],
            "ohc_rate_W_m2": ocean_rate,
            "ohc_rate_ZJ_yr": w_m2_to_zj_yr(ocean_rate)}


def fixture_ohc_receipt(start: str, end: str) -> dict:
    """The planted ocean-side input in the shape the executor reads from
    an Argo receipt: the trend term with its uncertainty and per-area
    rate, the fitted change, and the identity fields."""
    truth = fixture_truth_window(start, end)
    n_cal = ym(end) - ym(start) + 1
    span_years = (n_cal - 12) / 12.0
    rate = truth["ohc_rate_ZJ_yr"]
    unc = TRUTH["ohc_uncertainty_ZJ_yr"]
    area = TRUTH["fixture_domain_area_m2"]
    return {
        "computation": "fixture (an Argo-shaped receipt planted by " + COMPUTATION + ")",
        "code_sha256": None, "run_id": None, "refused": False,
        "bound_parameters": {"window": f"{start}:{end}", "depth": OHC_DEPTH},
        "data": {"mode": "fixture", "record": "fixture", "data_root": "fixture"},
        "terms": {
            "trend": {"value": rate, "units": "ZJ/year", "uncertainty": unc,
                      "per_area": {"W_m2_of_earth_surface": zj_yr_to_w_m2(rate),
                                   "W_m2_of_domain": rate * ZJ / SECONDS_PER_YEAR / area,
                                   "domain_area_m2": area,
                                   "earth_surface_area_m2": EARTH_AREA_M2},
                      "stamp": "fixture"},
            "change": {"value": rate * span_years, "units": "ZJ", "uncertainty": unc * span_years,
                       "span_years": span_years, "stamp": "fixture"},
            "endpoint_change": {"value": rate * span_years, "units": "ZJ",
                                "uncertainty": unc * span_years, "stamp": "fixture"},
            "deep_omission": {"omitted": True, "published": {
                "published_rate_W_m2": DEEP_OCEAN["value_W_m2"],
                "published_uncertainty_W_m2": DEEP_OCEAN["uncertainty_W_m2"],
                "published_rate_ZJ_yr": DEEP_OCEAN["value_ZJ_yr"],
                "published_uncertainty_ZJ_yr": DEEP_OCEAN["uncertainty_ZJ_yr"],
                "period": DEEP_OCEAN["period"], "source": DEEP_OCEAN["source"]}},
        },
        "bookkeeping": {"coverage": {"statement": "synthetic: one fixture domain",
                                     "domain_area_m2": area}},
    }


# ---- a data root

def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def value_digest(value) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def package_root(start: Path):
    for p in (start, *start.parents):
        if (p / ".osp" / "package.yaml").is_file():
            return p
    return None


def package_identity(root) -> dict:
    """name, version and release lock digest of a package tree; null
    throughout where no package tree is found."""
    if root is None:
        return {"name": None, "version": None, "release_lock": None}
    text = (root / ".osp" / "package.yaml").read_text(encoding="utf-8")
    block = text.split("package:", 1)[1]
    name = re.search(r"^\s+name:\s*['\"]?([A-Za-z0-9._-]+)", block, re.M)
    version = re.search(r"^\s+version:\s*['\"]?([0-9][0-9.]*)", block, re.M)
    lock_path = root / ".osp" / "release-lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8")) if lock_path.is_file() else None
    return {"name": name.group(1) if name else None,
            "version": version.group(1) if version else None,
            "release_lock": value_digest(lock) if lock is not None else None}


def tree_label(path: Path) -> str:
    """A path as the receipt records it: relative to the package this
    executor ships in when it sits under it (so the run id reproduces
    on any machine), else absolute."""
    pkg = package_root(HERE)
    try:
        return path.resolve().relative_to(pkg.resolve()).as_posix() if pkg else str(path)
    except ValueError:
        return str(path)


def read_csv_series(path: Path):
    dates, values, uncs, product = [], [], [], []
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            dates.append(row["month"].strip())
            values.append(float(row["value_W_m2"]))
            uncs.append(float(row["uncertainty_W_m2"]))
            pg = (row.get("product_global_W_m2") or "").strip()
            product.append(float(pg) if pg else None)
    if dates != sorted(dates) or len(set(dates)) != len(dates):
        raise SystemExit(f"{path.name}: months must be unique and in order")
    return {"dates": dates, "value_W_m2": values, "uncertainty_W_m2": uncs,
            "product_global_W_m2": product}


def read_ohc_receipt(path: Path) -> dict:
    try:
        r = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise SystemExit(f"{path}: not a readable JSON receipt ({e})")
    if not isinstance(r, dict) or not str(r.get("computation", "")).endswith("argo_ohc.py"):
        raise SystemExit(f"{path} is not a receipt of {OHC_COMPUTATION}")
    return r


def read_data_root(root: Path, ohc_path) -> dict:
    root = root.expanduser().resolve()
    record_path = root / "RECORD.json"
    if not record_path.is_file():
        raise SystemExit(f"{root} carries no RECORD.json; nothing is computed on an unrecorded tree")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    book = record.get("bookkeeping")
    if not isinstance(book, dict):
        raise SystemExit("RECORD.json carries no bookkeeping table")
    for section, key in REQUIRED_BOOKKEEPING:
        if not (isinstance(book.get(section), dict) and book[section].get(key) not in (None, "")):
            raise SystemExit(f"RECORD.json bookkeeping lacks {section}.{key}")
    manifest = record.get("manifest") or {}
    files = {}
    for name, digest in manifest.items():
        p = root / name
        if not p.is_file():
            raise SystemExit(f"{root} lacks {name}, which RECORD.json lists")
        if sha256_file(p) != digest:
            raise SystemExit(f"{name} does not match the RECORD.json manifest; the tree was "
                             "edited after it was recorded")
        files[name] = digest
    for name in ("toa-net.csv", "toa-net-stamp.json"):
        if name not in files:
            raise SystemExit(f"RECORD.json manifest lacks {name}")
    ohc_path = Path(ohc_path).expanduser().resolve() if ohc_path else root / "ohc-2000-receipt.json"
    if not ohc_path.is_file():
        raise SystemExit(f"no Argo receipt at {ohc_path} (give --ohc-receipt)")
    stamp = json.loads((root / "toa-net-stamp.json").read_text(encoding="utf-8"))
    return {"series": read_csv_series(root / "toa-net.csv"), "record": record, "stamp": stamp,
            "files": files, "record_sha256": sha256_file(record_path),
            "data_root": tree_label(root),
            "ohc": read_ohc_receipt(ohc_path), "ohc_path": tree_label(ohc_path),
            "ohc_sha256": sha256_file(ohc_path),
            "ohc_in_manifest": (ohc_path.parent == root and ohc_path.name in files)}


# ---- Student's t, written from the definition

def _betacf(a, b, x):
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 600):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        dd = 1.0 + aa * d
        d = 1.0 / (dd if abs(dd) > tiny else tiny)
        c = 1.0 + aa / (c if abs(c) > tiny else tiny)
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        dd = 1.0 + aa * d
        d = 1.0 / (dd if abs(dd) > tiny else tiny)
        c = 1.0 + aa / (c if abs(c) > tiny else tiny)
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-15:
            return h
    raise ArithmeticError("incomplete beta did not converge")


def betainc(a, b, x):
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    front = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                     + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def t_cdf(t, df):
    x = df / (df + t * t)
    tail = 0.5 * betainc(df / 2.0, 0.5, x)
    return 1.0 - tail if t >= 0 else tail


def t_quantile(p, df):
    lo, hi = 0.0, 1.0
    while t_cdf(hi, df) < p:
        hi *= 2.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if t_cdf(mid, df) < p:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-13 * max(1.0, hi):
            break
    return 0.5 * (lo + hi)


# ---- the statistics on calendar epochs

def group_means_removed(t_cal, y):
    """The series and the time index with calendar-month group means
    removed (the annual cycle taken out jointly with what is fitted)."""
    t = [float(v) for v in t_cal]
    yy = [float(v) for v in y]
    groups = {}
    for i, k in enumerate(t_cal):
        groups.setdefault(k % 12, []).append(i)
    for idx in groups.values():
        ybar_g = sum(yy[i] for i in idx) / len(idx)
        tbar_g = sum(t[i] for i in idx) / len(idx)
        for i in idx:
            yy[i] -= ybar_g
            t[i] -= tbar_g
    return t, yy


def lag1(t_cal, e):
    ss = sum(v * v for v in e)
    num = sum(e[i] * e[i + 1] for i in range(len(e) - 1) if t_cal[i + 1] - t_cal[i] == 1)
    return (num / ss if ss > 0 else 0.0), ss


def trend_block(t_cal, y, uncertainty) -> dict:
    """Least squares on calendar epochs with the annual cycle removed as
    calendar-month group means, lag-1 autocorrelation over adjacent
    epochs, the effective sample size capped at n, Student's t on
    n_eff minus 2; the slope's weights carry the per-month
    uncertainties into a formal error. Units: W m-2 per year, and per
    decade beside it."""
    n = len(y)
    t, yy = group_means_removed(t_cal, y)
    tbar, ybar = sum(t) / n, sum(yy) / n
    sxx = sum((a - tbar) ** 2 for a in t)
    sxy = sum((a - tbar) * (b - ybar) for a, b in zip(t, yy))
    slope = sxy / sxx
    icpt = ybar - slope * tbar
    e = [b - (icpt + slope * a) for a, b in zip(t, yy)]
    r1, ss = lag1(t_cal, e)
    weights = [(a - tbar) / sxx for a in t]
    formal_se = math.sqrt(sum((w * s) ** 2 for w, s in zip(weights, uncertainty)))
    block = {"method": "least squares on calendar epochs, the annual cycle removed as "
                       "calendar-month group means, lag-1 autocorrelation over adjacent "
                       "epochs, effective sample size capped at n, Student's t on n_eff - 2",
             "confidence": CONFIDENCE, "units": "W m-2 per year", "n": n,
             "deseasonalize": "climatology", "trend": slope * 12.0,
             "trend_per_decade": slope * 120.0,
             "formal_95": Z95 * formal_se * 12.0}
    n_eff = min(float(n), n * (1.0 - r1) / (1.0 + r1))
    dof = n_eff - 2.0
    block.update({"r1": r1, "n_eff": n_eff, "dof": dof})
    if dof < MIN_DOF:
        block.update({"stated": False,
                      "reason": f"effective sample size {n_eff:.2f} leaves {dof:.2f} degrees of "
                                f"freedom, below {MIN_DOF}; no interval is stated"})
        return block
    se = math.sqrt(ss / dof / sxx)
    tq = t_quantile(0.5 + CONFIDENCE / 2.0, dof)
    half = tq * se * 12.0
    trend = block["trend"]
    block.update({"stated": True, "se": se * 12.0, "t_quantile": tq, "half_width": half,
                  "half_width_per_decade": half * 10.0,
                  "ci_low": trend - half, "ci_high": trend + half,
                  "significant_at_confidence": bool((trend - half) * (trend + half) > 0)})
    return block


def mean_block(t_cal, y, uncertainty) -> dict:
    """The window mean of a monthly series with the sampling half width
    of that mean under a lag-1 autocorrelated residual about the
    calendar-month means (Student's t on n_eff minus 1), and the formal
    error the per-month uncertainties propagate to the mean."""
    n = len(y)
    mean = sum(y) / n
    _, yy = group_means_removed(t_cal, y)
    r1, ss = lag1(t_cal, yy)
    n_eff = min(float(n), n * (1.0 - r1) / (1.0 + r1))
    dof = n_eff - 1.0
    formal = Z95 * math.sqrt(sum(u * u for u in uncertainty)) / n
    block = {"method": "the arithmetic mean over the months used; the sampling half width "
                       "from the residual about the calendar-month means under a lag-1 "
                       "autocorrelated model, the variance scaled by n - 1, the effective "
                       "sample size capped at n, Student's t on n_eff - 1",
             "confidence": CONFIDENCE, "units": "W m-2", "n": n, "mean": mean,
             "r1": r1, "n_eff": n_eff, "dof": dof, "formal_95": formal,
             "whole_years": n % 12 == 0}
    if dof < MIN_DOF or n < 2:
        block.update({"stated": False,
                      "reason": f"effective sample size {n_eff:.2f} leaves {dof:.2f} degrees of "
                                f"freedom, below {MIN_DOF}; no half width is stated"})
        return block
    sd = math.sqrt(ss / (n - 1.0))
    tq = t_quantile(0.5 + CONFIDENCE / 2.0, dof)
    half = tq * sd / math.sqrt(n_eff)
    block.update({"stated": True, "sd": sd, "t_quantile": tq, "half_width": half})
    return block


# ---- units and published terms

def zj_yr_to_w_m2(rate_zj_yr: float) -> float:
    return rate_zj_yr * ZJ / SECONDS_PER_YEAR / EARTH_AREA_M2


def w_m2_to_zj_yr(rate_w_m2: float) -> float:
    return rate_w_m2 * EARTH_AREA_M2 * SECONDS_PER_YEAR / ZJ


def non_ocean_total() -> dict:
    comps = NON_OCEAN["components"]
    return {"value_W_m2": sum(c["value_W_m2"] for c in comps.values()),
            "uncertainty_W_m2": math.sqrt(sum(c["uncertainty_W_m2"] ** 2 for c in comps.values()))}


def energy_over_window(rate_w_m2: float, n_calendar: int) -> float:
    """Rate times the window length times the Earth's area, in ZJ."""
    return rate_w_m2 * EARTH_AREA_M2 * (n_calendar / 12.0) * SECONDS_PER_YEAR / ZJ


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


# ---- the computation

def ocean_side(ohc: dict, start: str, end: str):
    """The Argo receipt's rate as a term, or a refusal."""
    if ohc.get("refused") is True:
        return None, ("ohc-receipt-refused",
                      f"the Argo receipt is a refusal ({ohc.get('reason_code')}: "
                      f"{ohc.get('reason')}); no ocean rate is stated")
    bound = ohc.get("bound_parameters") or {}
    if bound.get("window") != f"{start}:{end}":
        return None, ("ohc-window-mismatch",
                      f"the Argo receipt's window {bound.get('window')} is not the window "
                      f"{start}:{end}; its rate is a whole-window quantity and cannot be "
                      "compared over another window")
    if bound.get("depth") != OHC_DEPTH:
        raise SystemExit(f"the Argo receipt is for the 0 to {bound.get('depth')} dbar layer; "
                         f"this budget reads the 0 to {OHC_DEPTH} dbar one")
    terms = ohc.get("terms") or {}
    trend = terms.get("trend") or {}
    if not isinstance(trend.get("value"), (int, float)) or trend.get("units") != "ZJ/year" \
            or not isinstance(trend.get("uncertainty"), (int, float)):
        raise SystemExit("the Argo receipt's terms.trend lacks value, units ZJ/year or uncertainty")
    rate_w = zj_yr_to_w_m2(trend["value"])
    unc_w = zj_yr_to_w_m2(trend["uncertainty"])
    stated = (trend.get("per_area") or {}).get("W_m2_of_earth_surface")
    if not isinstance(stated, (int, float)) or abs(stated - rate_w) > REL_TOL * max(1e-12, abs(rate_w)):
        raise SystemExit(f"the Argo receipt's own per-area rate {stated} disagrees with the "
                         f"conversion here {rate_w} (the Earth area convention differs)")
    change = terms.get("change") or {}
    endpoint = terms.get("endpoint_change") or {}
    cov = ((ohc.get("bookkeeping") or {}).get("coverage") or {})
    return {
        "value": rate_w, "units": "W m-2 of the Earth's surface", "uncertainty": unc_w,
        "rate_ZJ_yr": trend["value"], "uncertainty_ZJ_yr": trend["uncertainty"],
        "uncertainty_basis": trend.get("uncertainty_basis"),
        "domain_area_m2": (trend.get("per_area") or {}).get("domain_area_m2"),
        "domain_statement": cov.get("statement"),
        "receipt_changes": {"change_ZJ": change.get("value"),
                            "change_uncertainty_ZJ": change.get("uncertainty"),
                            "span_years": change.get("span_years"),
                            "endpoint_change_ZJ": endpoint.get("value"),
                            "endpoint_change_uncertainty_ZJ": endpoint.get("uncertainty")},
        "receipt_deep_omission": (terms.get("deep_omission") or {}).get("published"),
        "stamp": ohc.get("run_id") and f"argo receipt {ohc.get('run_id')}" or "fixture",
    }, None


def compute(series: dict, ohc: dict, start: str, end: str, bookkeeping: dict, stamp_name: str):
    """(receipt body, None) or (None, (reason_code, reason))."""
    k0, k1 = ym(start), ym(end)
    calendar = [label(k) for k in range(k0, k1 + 1)]
    n_calendar = len(calendar)
    by = {d: (v, u, p) for d, v, u, p in zip(series["dates"], series["value_W_m2"],
                                             series["uncertainty_W_m2"], series["product_global_W_m2"])}
    used = [d for d in calendar if d in by]
    missing = [d for d in calendar if d not in by]
    if n_calendar < MIN_MONTHS or len(used) < MIN_MONTHS:
        return None, ("too-few-months",
                      f"{len(used)} of {n_calendar} months of {start}:{end} carry a value; the "
                      f"budget needs at least {MIN_MONTHS}")
    if any(by[d][2] is None for d in used):
        raise SystemExit("a month in the window lacks the product's global mean column")
    ocean, refusal = ocean_side(ohc, start, end)
    if refusal:
        return None, refusal
    t_cal = [ym(d) - k0 for d in used]
    coslat = [by[d][0] for d in used]
    unc = [by[d][1] for d in used]
    product = [by[d][2] for d in used]
    coslat_mean = sum(coslat) / len(coslat)
    anomaly = [v - coslat_mean for v in coslat]
    offsets = [c - p for c, p in zip(coslat, product)]
    mean = mean_block(t_cal, product, unc)
    if not mean["stated"]:
        return None, ("interval-not-stated",
                      f"the window mean carries no half width ({mean['reason']}); no "
                      "uncertainty can be stated")
    trend = trend_block(t_cal, anomaly, unc)
    if not trend["stated"]:
        return None, ("interval-not-stated",
                      f"the anomaly trend carries no interval ({trend['reason']}); no "
                      "interval is stated")
    sampling = max(mean["half_width"], mean["formal_95"])
    toa_unc = math.sqrt(ANCHOR["uncertainty_W_m2"] ** 2 + sampling ** 2)
    deep = {"value": DEEP_OCEAN["value_W_m2"], "units": "W m-2 of the Earth's surface",
            "uncertainty": DEEP_OCEAN["uncertainty_W_m2"], "published": dict(DEEP_OCEAN),
            "agrees_with_receipt": bool(
                isinstance(ocean["receipt_deep_omission"], dict)
                and ocean["receipt_deep_omission"].get("published_rate_W_m2") == DEEP_OCEAN["value_W_m2"]
                and ocean["receipt_deep_omission"].get("published_uncertainty_W_m2") == DEEP_OCEAN["uncertainty_W_m2"]),
            "stamp": "published: not measured here; the Argo receipt states the omission"}
    non = non_ocean_total()
    non_ocean = {"value": non["value_W_m2"], "units": "W m-2 of the Earth's surface",
                 "uncertainty": non["uncertainty_W_m2"], "published": json.loads(json.dumps(NON_OCEAN)),
                 "stamp": "published: not measured here"}
    toa = {"value": mean["mean"], "units": "W m-2 of the Earth's surface", "uncertainty": toa_unc,
           "uncertainty_basis": "the anchor's in situ uncertainty (0.10 W m-2, 95 percent) in "
                                "quadrature with the larger of the sampling half width of the "
                                "window mean and the formal error the per-month floor propagates",
           "anchor_uncertainty_W_m2": ANCHOR["uncertainty_W_m2"],
           "sampling_uncertainty_W_m2": sampling,
           "weighting": "the product's geodetic global mean, on which the anchor is defined; the "
                        "cos-latitude mean and the offset between them are stated beside it",
           "coslat_window_mean_W_m2": coslat_mean,
           "weighting_offset_W_m2": {"mean": sum(offsets) / len(offsets),
                                     "max_abs": max(abs(o) for o in offsets),
                                     "rule": "cos-latitude mean minus the product's geodetic mean, "
                                             "over the months used"},
           "mean_block": mean, "stamp": stamp_name}
    ohc_term = {k: v for k, v in ocean.items() if k != "receipt_deep_omission"}
    residual = toa["value"] - (ohc_term["value"] + deep["value"] + non_ocean["value"])
    combined = math.sqrt(toa_unc ** 2 + ohc_term["uncertainty"] ** 2
                         + deep["uncertainty"] ** 2 + non_ocean["uncertainty"] ** 2)
    closed = abs(residual) <= combined
    ocean_sum = ohc_term["value"] + deep["value"] + non_ocean["value"]
    ocean_sum_unc = math.sqrt(ohc_term["uncertainty"] ** 2 + deep["uncertainty"] ** 2
                              + non_ocean["uncertainty"] ** 2)
    anomaly_term = {
        "value": trend["trend_per_decade"], "units": "W m-2 per decade",
        "uncertainty": max(trend["half_width_per_decade"], trend["formal_95"] * 10.0),
        "uncertainty_basis": "the larger of the 95 percent sampling half width under the AR(1) "
                             "residual model and the formal error the per-month floor "
                             "propagates, per decade",
        "series_rule": "the cos-latitude global mean minus its own mean over the months used; "
                       "the product's anchor and the weighting offset cancel in the anomaly and "
                       "in its trend",
        "interval": trend,
        "published": dict(PUBLISHED_TREND),
        "distance_W_m2_per_decade": trend["trend_per_decade"] - PUBLISHED_TREND["value_W_m2_per_decade"],
        "distance_over_published_uncertainty": (trend["trend_per_decade"] - PUBLISHED_TREND["value_W_m2_per_decade"])
        / PUBLISHED_TREND["uncertainty_W_m2_per_decade"],
        "stamp": stamp_name,
    }
    book = json.loads(json.dumps(bookkeeping))
    book["anchoring"].update({
        "anchor": dict(ANCHOR),
        "months_shared_with_anchor_decade": overlap_months(start, end, ANCHOR["period"]),
        "months_in_window": n_calendar,
        "independence": "over the months the window shares with the anchor decade the toa_net "
                        "term is the in situ heat uptake the product was set to, not a "
                        "radiometric measurement; the anomaly term and its trend are "
                        "radiometric throughout",
    })
    book["weighting"].update({"offset_W_m2": toa["weighting_offset_W_m2"]})
    book["ocean_input"].update({"domain": ohc_term.get("domain_statement"),
                                "domain_area_m2": ohc_term.get("domain_area_m2"),
                                "scaling": "the Argo rate is over the product's mapped domain and "
                                           "is never scaled to the global ocean; divided by the "
                                           "Earth's area it understates the global ocean by "
                                           "construction"})
    book["deep_ocean"] = {"statement": DEEP_OCEAN["statement"],
                          "agrees_with_receipt": deep["agrees_with_receipt"]}
    book["non_ocean"] = {"statement": "land, cryosphere and atmosphere as published rates, "
                                      "never measured here", "period": NON_OCEAN["period"]}
    book["published_eei"] = dict(PUBLISHED_EEI)
    book["area_convention"] = {"earth_surface_area_m2": EARTH_AREA_M2,
                               "rule": "4 pi R squared, R the 6371 km mean radius, the Argo "
                                       "receipt's and the published inventories' convention; "
                                       "every rate here is per unit Earth surface"}
    book["window_handling"] = {
        "rule": "a calendar month of the window with no radiation value is a hole, dropped from "
                "the mean and the fit and never interpolated; the Argo receipt's window must "
                "equal the window asked for",
        "months_missing": missing,
        "whole_years": n_calendar % 12 == 0,
        "note": "a window that is not whole years leaves part of the annual cycle in the mean; "
                "the mean is the arithmetic mean over the months used, as stated",
    }
    body = {
        "months": {"window": [start, end], "n_calendar": n_calendar, "n_used": len(used),
                   "used": used, "missing": missing},
        "series": {"dates": used, "toa_net_coslat_W_m2": coslat, "toa_net_product_W_m2": product,
                   "uncertainty_W_m2": unc, "toa_net_anomaly_W_m2": anomaly},
        "terms": {"toa_net": toa, "ohc_0_2000": ohc_term, "deep_ocean": deep,
                  "non_ocean": non_ocean, "toa_net_anomaly_trend": anomaly_term},
        "toa_net_W_m2": round(toa["value"], 4),
        "ocean_side_W_m2": round(ocean_sum, 4),
        "residual_W_m2": round(residual, 4),
        "toa_net_anomaly_trend_W_m2_per_decade": round(anomaly_term["value"], 4),
        "residual": {"value": residual, "units": "W m-2 of the Earth's surface",
                     "rule": "toa_net minus (ohc_0_2000 plus deep_ocean plus non_ocean)",
                     "ocean_side_sum": ocean_sum, "ocean_side_uncertainty": ocean_sum_unc},
        "combined_uncertainty": {"value": combined, "units": "W m-2 of the Earth's surface",
                                 "rule": "the four term uncertainties in quadrature; the anchor's "
                                         "uncertainty sits inside the toa_net term"},
        "verdict": {"closed_within_uncertainty": closed,
                    "rule": "closed when the residual lies within the combined uncertainty",
                    "residual_W_m2": residual, "bar_W_m2": combined},
        "energy_over_window_ZJ": {
            "rule": "each rate times the window length in seconds times the Earth's area",
            "window_years": n_calendar / 12.0,
            "toa_net": energy_over_window(toa["value"], n_calendar),
            "toa_net_uncertainty": energy_over_window(toa_unc, n_calendar),
            "ohc_0_2000": energy_over_window(ohc_term["value"], n_calendar),
            "ohc_0_2000_uncertainty": energy_over_window(ohc_term["uncertainty"], n_calendar),
            "deep_ocean": energy_over_window(deep["value"], n_calendar),
            "non_ocean": energy_over_window(non_ocean["value"], n_calendar),
            "residual": energy_over_window(residual, n_calendar),
            "bar": energy_over_window(combined, n_calendar),
            "argo_receipt_changes": ohc_term["receipt_changes"],
            "note": "the Argo receipt's own change is its rate times the span between its first "
                    "and last year centres, a shorter span than the window; it is copied for the "
                    "reader and not compared",
        },
        "published_eei": {"published": dict(PUBLISHED_EEI),
                          "toa_net_minus_published_W_m2": toa["value"] - PUBLISHED_EEI["value_W_m2"],
                          "ocean_side_minus_published_W_m2": ocean_sum - PUBLISHED_EEI["value_W_m2"]},
        "bookkeeping": book,
    }
    return body, None


def receipt_head(args, capability, bundle, data) -> dict:
    return {
        "computation": COMPUTATION,
        "code_sha256": sha256_file(Path(__file__).resolve()),
        "capability": capability,
        "bundle": bundle,
        "runtime": {"name": args.runtime, "version": args.runtime_version},
        "generated_utc": now_utc(),
        "data": data,
        "bound_parameters": {"window": args.window},
    }


def finish(receipt: dict) -> dict:
    receipt["run_id"] = value_digest({k: v for k, v in receipt.items()
                                      if k != "generated_utc"})[:23]
    return receipt


def write(receipt: dict, path) -> None:
    text = json.dumps(receipt, indent=2) + "\n"
    if path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"receipt written: {path}", file=sys.stderr)
    else:
        print(text)


def ohc_identity(ohc: dict, path_label, digest, in_manifest) -> dict:
    d = ohc.get("data") or {}
    return {"path": path_label, "sha256": digest, "in_data_root_manifest": in_manifest,
            "computation": ohc.get("computation"), "code_sha256": ohc.get("code_sha256"),
            "run_id": ohc.get("run_id"), "refused": ohc.get("refused"),
            "reason_code": ohc.get("reason_code"),
            "bound_parameters": ohc.get("bound_parameters"),
            "bundle": ohc.get("bundle"), "capability": ohc.get("capability"),
            "runtime": ohc.get("runtime"), "generated_utc": ohc.get("generated_utc"),
            "record": d.get("record"), "record_sha256": d.get("record_sha256"),
            "data_root": d.get("data_root"), "stamp": d.get("stamp") and (d["stamp"].get("term"))}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--window", required=True, help="YYYY-MM:YYYY-MM (declared parameter)")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--fixture", action="store_true", help="the synthetic record")
    mode.add_argument("--data-root", type=Path, help="a recorded tree (execution plumbing)")
    ap.add_argument("--ohc-receipt", type=Path, default=None,
                    help="the Argo ocean heat content receipt (default DIR/ohc-2000-receipt.json)")
    ap.add_argument("--seed", type=int, default=7, help="fixture seed (default 7)")
    ap.add_argument("--runtime", required=True,
                    help="the runtime that ran this (claude-code, claude-cowork, a gate's name, ...)")
    ap.add_argument("--runtime-version", default=None)
    ap.add_argument("--receipt", type=Path, default=None)
    ap.add_argument("--capability-root", type=Path, default=None,
                    help="the package tree this run is evidence for (default: the tree this "
                         "executor ships in)")
    args = ap.parse_args(argv)

    start, end = parse_window(args.window)
    bundle = package_identity(package_root(HERE))
    capability = (package_identity(package_root(args.capability_root.expanduser().resolve()))
                  if args.capability_root else bundle)
    if args.fixture:
        if args.ohc_receipt:
            ap.error("--ohc-receipt goes with --data-root; the fixture plants its own")
        fx = make_fixture(args.seed)
        data = {"mode": "fixture", "seed": args.seed, "span": list(FIXTURE_SPAN),
                "digest": fixture_digest(fx),
                "generator": COMPUTATION + " (make_fixture)",
                "generator_sha256": sha256_file(Path(__file__).resolve()),
                "truth": json.loads(json.dumps(TRUTH))}
        series, bookkeeping, span = fx["series"], FIXTURE_BOOKKEEPING, FIXTURE_SPAN
        ohc = fixture_ohc_receipt(start, end) if ym(FIXTURE_SPAN[0]) <= ym(start) <= ym(end) <= ym(FIXTURE_SPAN[1]) else {}
        stamp_name = "fixture"
    else:
        tree = read_data_root(args.data_root, args.ohc_receipt)
        data = {"mode": "data-root", "data_root": tree["data_root"],
                "record": tree["record"].get("record"),
                "record_sha256": tree["record_sha256"],
                "manifest_sha256": tree["record"].get("manifest_sha256"),
                "files": tree["files"], "stamp": tree["stamp"],
                "ohc_receipt": ohc_identity(tree["ohc"], tree["ohc_path"], tree["ohc_sha256"],
                                            tree["ohc_in_manifest"])}
        series, bookkeeping, ohc = tree["series"], tree["record"]["bookkeeping"], tree["ohc"]
        span = (series["dates"][0], series["dates"][-1])
        stamp_name = "toa-net-stamp.json"
    head = receipt_head(args, capability, bundle, data)

    refusal = None
    if not (ym(span[0]) <= ym(start) and ym(end) <= ym(span[1])):
        refusal = ("window-outside-record",
                   f"the window {start}:{end} lies outside the radiation record "
                   f"{span[0]} through {span[1]}")
    else:
        body, refusal = compute(series, ohc, start, end, bookkeeping, stamp_name)
    if refusal:
        receipt = finish({**head, "refused": True, "reason_code": refusal[0],
                          "reason": refusal[1]})
        print(f"REFUSED ({refusal[0]}): {refusal[1]}")
        write(receipt, args.receipt)
        return 3

    if args.fixture:
        truth = fixture_truth_window(start, end)
        tb = body["terms"]["toa_net_anomaly_trend"]["interval"]
        body["known_truth"] = {
            "planted_geodetic_window_mean_W_m2": truth["geodetic_window_mean_W_m2"],
            "recovered_toa_net_W_m2": body["terms"]["toa_net"]["value"],
            "planted_trend_W_m2_per_decade": truth["trend_W_m2_per_decade"],
            "recovered_trend_W_m2_per_decade": tb["trend_per_decade"],
            "trend_inside_interval": bool(tb["ci_low"] * 10.0 <= truth["trend_W_m2_per_decade"] <= tb["ci_high"] * 10.0),
            "planted_ohc_rate_W_m2": truth["ohc_rate_W_m2"],
            "planted_closure": "the planted ocean rate is the planted geodetic window mean minus "
                               "the deep and non-ocean terms, so the residual is the noise of "
                               "the window mean alone",
            "residual_within_bar": body["verdict"]["closed_within_uncertainty"],
        }
    else:
        body["known_truth"] = None
    receipt = finish({**head, "refused": False, **body,
                      "caveats": [
                          ("a fixture run proves the chain, not the Earth; the real-data anchor "
                           "is the stamped data root run the concept records")
                          if args.fixture else
                          ("a real-data run on a stamped record: the loader's stamp states the "
                           "edition, the file, the weighting and the uncertainty basis; the "
                           "Argo receipt states its domain, and the ocean rate is over that "
                           "domain, never scaled to the global ocean"),
                          "the toa_net term carries the product's anchor: over the months the "
                          "window shares with July 2005 through June 2015 it is the in situ heat "
                          "uptake the product was set to; the anomaly trend is radiometric "
                          "throughout (the bundle's ebaf-imbalance-anchored-to-ocean-heating "
                          "gotcha)",
                          "the deep ocean and the non-ocean terms are published rates with "
                          "their sources, not measurements made here",
                          "the series travels at full precision so every term, the residual "
                          "and the verdict are recomputable from the receipt",
                      ]})
    v = receipt["verdict"]
    tb = receipt["terms"]["toa_net_anomaly_trend"]["interval"]
    where = f"fixture seed {args.seed}" if args.fixture else f"data root {data['data_root']}"
    print(f"anomaly trend {tb['trend_per_decade']:+.4f} W m-2 per decade, 95% "
          f"[{tb['ci_low'] * 10:+.4f}, {tb['ci_high'] * 10:+.4f}] (r1 {tb['r1']:+.4f}, "
          f"n_eff {tb['n_eff']:.2f} of {tb['n']}); published {PUBLISHED_TREND['value_W_m2_per_decade']} "
          f"plus or minus {PUBLISHED_TREND['uncertainty_W_m2_per_decade']}", file=sys.stderr)
    t = receipt["terms"]
    print(f"energy budget {start}:{end} on {where}: {receipt['months']['n_used']} of "
          f"{receipt['months']['n_calendar']} months used; toa_net {t['toa_net']['value']:+.4f} "
          f"(unc {t['toa_net']['uncertainty']:.4f}), ohc_0_2000 {t['ohc_0_2000']['value']:+.4f} "
          f"(unc {t['ohc_0_2000']['uncertainty']:.4f}), deep {t['deep_ocean']['value']:+.3f}, "
          f"non-ocean {t['non_ocean']['value']:+.4f} W m-2; residual {v['residual_W_m2']:+.4f} "
          f"against a bar of {v['bar_W_m2']:.4f}; closed_within_uncertainty "
          f"{str(v['closed_within_uncertainty']).lower()}; run {receipt['run_id']}")
    write(receipt, args.receipt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
