#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Sanctioned computation for the attested cloud radiative effect at the
top of the atmosphere: the shortwave, longwave and net effect of
clouds on the CERES EBAF radiation budget over one stated window and
one stated region, as the difference between the all-sky and the
clear-sky fluxes of the energy balanced product.

Contract: knowledge/computations/cloud-radiative-effect.md. Over one window
of calendar months and one region, the receipt carries three terms in
watts per square metre of the region, each with an uncertainty and the
stamp it came from:

  cre_shortwave  the window mean of the regional mean clear-sky minus
                 all-sky outgoing shortwave flux, negative where
                 clouds reflect more sunlight than the clear column;
  cre_longwave   the window mean of the regional mean clear-sky minus
                 all-sky outgoing longwave flux, positive where clouds
                 reduce the flux to space;
  cre_net        the window mean of the regional mean all-sky minus
                 clear-sky net downward flux, read from the product's
                 net fields and not from the two above.

The residual is cre_net minus the sum of the shortwave and longwave
terms: the decomposition of the net cloud radiative effect into its
two parts is an identity of the product's own fields, and the residual
measures whether the fields keep it. The combined uncertainty is the
three term uncertainties in quadrature; the verdict
decomposition_closes says whether the residual lies inside a stated
tolerance, which is the granularity of the fields and not the sampling
bar.

The clear-sky convention is a declared parameter, because the product
carries more than one quantity called clear-sky and a cloud radiative
effect inherits the convention of the field it subtracts. The energy
balanced product carries two: `total-region`, the clear-sky flux for
the whole region with its cloudy portions included, which is the
definition climate models use and the one the product's own cloud
radiative effect variables are computed from since Edition 4.1; and
`cloud-free-area`, the traditional flux over the cloud-free portions
of a region, filled where no cloud-free footprint was observed, which
is what Edition 4.0 provided. The bundle's convention concept
conventions/ceres-clear-sky-conventions.md states the four quantities
the radiation products call clear-sky and which convention each field
carries; the two this computation binds are the two the energy
balanced product's variables carry, and a convention it does not carry
is refused rather than approximated. The receipt also carries the
other convention's three terms over the same window and region and the
difference between them, so the price of the choice is a receipt fact
rather than a paragraph.

The fields are area weighted with the CERES one degree zonal geodetic
weights, the weights the product's own global means are formed with,
so a regional mean here is the product's own global mean restricted to
the region's zones. A region is a band of whole one degree zones; a
land or ocean region is not resolvable from the fields read and is
refused.

Two input modes. --data-root DIR reads cre-fluxes.csv (region,
convention, month, the three all-sky and the three clear-sky regional
means, and the three per-month uncertainty floors), the loader's
stamp, and the RECORD.json the data-root tool wrote, every file
checked against its manifest. --fixture [--seed N] generates a
synthetic record deterministically (a hash-based Gaussian stream): for
every region and both conventions a monthly all-sky and clear-sky flux
2000-03 through 2026-05 with a planted cloud radiative effect, an
annual cycle, an interannual AR(1) component, noise at the stated
per-month uncertainty, and a planted convention offset, with the net
columns formed from the shortwave and longwave ones so that the
decomposition holds by construction; the receipt shows the planted
effect and the planted offset recovered.

Refusals, exit 3 with a refusal receipt and never a number: a
clear-sky convention the product does not carry
(clear-sky-convention-not-carried); a window outside the record
(window-outside-record); a region whose mask cannot be resolved
(region-not-resolvable); fewer than 24 months in the window
(too-few-months); a window mean whose half width cannot be stated
(interval-not-stated).

The receipt's run_id digests the receipt without its timestamp; the
data root is recorded package-relative when it sits under this
package, so a record run reproduces its id on any machine. Consumers
bind values for the declared parameters and MUST NOT edit this file;
the attester hashes it, regenerates the fixture at the receipt's seed,
and recomputes every number from the receipt.

  cloud_radiative_effect.py --window YYYY-MM:YYYY-MM --region NAME
      --clear-sky CONVENTION --runtime NAME
      (--fixture [--seed N] | --data-root DIR)
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
COMPUTATION = "skills/cloud-radiative-effect/scripts/cloud_radiative_effect.py"

# The two clear-sky conventions the energy balanced product carries.
CONVENTIONS = {
    "total-region": {
        "variable_suffix": "clr_t",
        "statement": "the clear-sky flux for the total region, the cloudy portions included "
                     "with their clouds removed, which the data quality summary describes as "
                     "defined in a manner more in line with how clear-sky fluxes are "
                     "represented in climate models; it entered at Edition 4.1 and the "
                     "product's own cloud radiative effect variables are computed from it "
                     "(their long names say so: uses Clear-Sky for total region)",
        "source": "the bundle's convention concept conventions/ceres-clear-sky-conventions.md "
                  "and its gotcha gotchas/ebaf-clear-sky-definitions.md; the CERES_EBAF_Ed4.2 "
                  "and Ed4.2.1 Data Quality Summary; Loeb and others (2020), "
                  "doi:10.1175/JCLI-D-19-0381.1",
    },
    "cloud-free-area": {
        "variable_suffix": "clr_c",
        "statement": "the traditional clear-sky flux over the cloud-free portions of a region, "
                     "inferred from CERES and imager measurements where no cloud-free footprint "
                     "was observed so that every region carries a value every month; this is "
                     "what Edition 4.0 provided and what its published global mean cloud "
                     "radiative effect was computed from",
        "source": "the bundle's convention concept conventions/ceres-clear-sky-conventions.md "
                  "and its gotcha gotchas/ebaf-clear-sky-definitions.md; the CERES_EBAF_Ed4.2 "
                  "and Ed4.2.1 and the CERES_EBAF_Ed4.0 Data Quality Summaries",
    },
}
# Quantities the radiation products call clear-sky that this product's
# fields do not carry; naming one is a refusal with its reason, not an
# approximation.
CONVENTIONS_NOT_CARRIED = {
    "pristine": "the SYN1deg clear-sky computation with the aerosols removed, so that only "
                "molecular scattering and absorption remain; an effect formed against it is a "
                "cloud plus aerosol effect, and the energy balanced product carries no such "
                "field",
    "computed-cloud-removed": "the SYN1deg clear-sky flux computed hourly by removing the "
                              "clouds from the radiative transfer calculation with the all-sky "
                              "profiles, so that the clear-sky sampling equals the all-sky "
                              "sampling; the energy balanced product carries no such field",
    "total-sky-no-aerosol": "the SYN1deg all-sky computation with the aerosols removed; the "
                            "energy balanced product carries no such field",
}
# The regions this computation resolves: bands of whole one degree
# zones, an inclusive lower and an exclusive upper latitude (the band
# that ends at 90 includes the pole zone).
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
# Regions a reader may ask for that the fields read cannot resolve.
REGIONS_NOT_RESOLVABLE = {
    "ocean": "a surface type mask, which the subset read carries no field for",
    "land": "a surface type mask, which the subset read carries no field for",
    "sea-ice": "a sea ice mask varying by month, which the subset read carries no field for",
}
TERMS = ("cre_shortwave", "cre_longwave", "cre_net")
FIXTURE_SPAN = ("2000-03", "2026-05")
MIN_MONTHS = 24
CONFIDENCE = 0.95
MIN_DOF = 1.0
Z95 = 1.959963984540054              # two-sided 95 percent normal quantile
# The decomposition of the net cloud radiative effect into its
# shortwave and longwave parts is an identity of the product's own
# fields. The bar below is two orders of magnitude above the storage
# and rounding granularity of the six fields that enter the residual
# (each stored as a 32 bit float at magnitudes up to about 340 W m-2,
# about 2e-5 W m-2 apiece, and written to the data root at six decimal
# places) and three orders below the smallest term, so a residual
# outside it is a disagreement between the product's net field and its
# shortwave and longwave fields, not noise.
DECOMPOSITION_TOLERANCE = 0.01

PUBLISHED_GLOBAL_MEAN = {
    "region": "global",
    "convention": "cloud-free-area",
    "period": ["2005-07", "2015-06"],
    "edition": "Edition 4.0",
    "cre_shortwave_W_m2": -45.8,
    "cre_longwave_W_m2": 28.0,
    "cre_net_W_m2": -17.9,
    "all_sky_shortwave_W_m2": 99.1,
    "all_sky_longwave_W_m2": 240.1,
    "clear_sky_shortwave_W_m2": 53.3,
    "clear_sky_longwave_W_m2": 268.1,
    "rounding_W_m2": 0.1,
    "statement": "the published global mean cloud radiative effect: the CERES_EBAF_Ed4.0 Data "
                 "Quality Summary's table of global mean TOA fluxes for July 2005 through June "
                 "2015 gives a shortwave cloud radiative effect of -45.8, a longwave one of "
                 "28.0 and a net one of -17.9 W m-2 for Edition 4.0, whose clear-sky flux is "
                 "the cloud-free-area one; a run over that decade on that convention is "
                 "compared with it, and a run on the total-region convention is not, because "
                 "the published number is not of that convention",
    "source": "CERES_EBAF_Ed4.0 Data Quality Summary, 2018-01-17, Table 6-1 (global mean TOA "
              "fluxes from EBAF Ed4.0 and EBAF Ed2.8 for July 2005 through June 2015); Loeb "
              "and others (2018), doi:10.1175/JCLI-D-17-0208.1, the Edition 4.0 product paper",
}
PUBLISHED_CONVENTION_ADJUSTMENT = {
    "toa_longwave_W_m2": -2.2,
    "toa_shortwave_W_m2": 0.5,
    "statement": "the published size of the adjustment that converts the cloud-free-area "
                 "clear-sky flux to the total-region one: a global mean longwave adjustment of "
                 "-2.2 W m-2 at the top of the atmosphere and a shortwave one of 0.5 W m-2, "
                 "pronounced at high latitudes in winter, under cirrus and over sea ice and "
                 "heavy aerosol; the bundle's gotcha owns the number and the edition history",
    "source": "Loeb and others (2020), Toward a Consistent Definition between Satellite and "
              "Model Clear-Sky Radiative Fluxes, Journal of Climate 33, 61 to 75, "
              "doi:10.1175/JCLI-D-19-0381.1 (the record and abstract on the Crossref registry; "
              "the journal page sits behind a bot check), as the bundle's gotcha "
              "gotchas/ebaf-clear-sky-definitions.md carries it",
}
TRUTH = {                             # what the fixture imposes
    "all_sky_shortwave_W_m2": 99.0, "all_sky_longwave_W_m2": 240.0, "solar_W_m2": 340.0,
    "annual_amplitude_shortwave_W_m2": 6.0, "annual_amplitude_longwave_W_m2": 3.0,
    "annual_peak_month": 7,
    "noise_sigma_W_m2": 0.40, "offset_sigma_W_m2": 0.05,
    "interannual_ar1": {"phi": 0.75, "sigma_W_m2": 0.50},
    # per region: the planted total-region shortwave and longwave cloud
    # radiative effect, and what the cloud-free-area convention adds to
    # each. The values are the order of the real record's regional
    # means over the anchor decade, rounded to two decimals.
    "planted": {
        "global": {"sw": -45.35, "lw": 25.72, "offset_sw": -0.47, "offset_lw": 2.22},
        "tropics": {"sw": -44.90, "lw": 30.24, "offset_sw": -0.46, "offset_lw": 3.14},
        "northern-extratropics": {"sw": -40.55, "lw": 22.18, "offset_sw": -0.70, "offset_lw": 1.83},
        "southern-extratropics": {"sw": -50.62, "lw": 24.58, "offset_sw": -0.26, "offset_lw": 1.66},
        "northern-midlatitudes": {"sw": -47.70, "lw": 25.35, "offset_sw": -0.95, "offset_lw": 2.38},
        "southern-midlatitudes": {"sw": -62.63, "lw": 28.56, "offset_sw": -0.55, "offset_lw": 2.46},
        "arctic": {"sw": -27.90, "lw": 16.36, "offset_sw": -0.07, "offset_lw": -0.90},
        "antarctic": {"sw": -28.59, "lw": 17.96, "offset_sw": 0.56, "offset_lw": -2.36},
    },
    "basis": "the planted effects are the order of the regional means the real record carries "
             "over the product's anchor decade, and the planted offsets the order of the "
             "difference the two conventions make there, the polar ones with the reversed sign "
             "the record shows; one all-sky series per region serves both conventions, as the "
             "product carries one all-sky field, and the cloud-free-area clear-sky column is "
             "the total-region one plus the planted offset and a small independent part, so "
             "the contrast recovers the offset; the net columns are formed from the shortwave "
             "and longwave ones, so the decomposition holds by construction",
}
FIXTURE_BOOKKEEPING = {
    "convention": {"statement": "synthetic: two planted clear-sky columns standing in for the "
                                "product's two conventions, offset by a planted amount per "
                                "region; a real run names the variable each convention reads"},
    "weighting": {"statement": "synthetic: no grid; a real run states the CERES one degree "
                               "zonal geodetic weights and the cross-check against the "
                               "product's own global means"},
    "edition": {"statement": "synthetic: no product; a real run names the edition, the release "
                             "date, the DOI and the file"},
    "uncertainty": {"basis": "synthetic: the per-month uncertainty is the noise sigma the "
                             "fixture generated the series with"},
    "region": {"statement": "synthetic: a planted series per named region; a real run states "
                            "the latitude band, its share of the geodetic weight and the "
                            "absence of a surface type mask"},
}
REQUIRED_BOOKKEEPING = (
    ("convention", "statement"), ("weighting", "statement"), ("edition", "statement"),
    ("uncertainty", "basis"), ("region", "statement"),
)
REASONS = ("clear-sky-convention-not-carried", "window-outside-record", "region-not-resolvable",
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


def other_convention(convention: str) -> str:
    return next(c for c in CONVENTIONS if c != convention)


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


def fixture_deterministic(region: str, convention: str, month: int):
    """The noise-free shortwave and longwave cloud radiative effect of a
    region and convention in a calendar month."""
    t = TRUTH
    p = t["planted"][region]
    add_sw = p["offset_sw"] if convention == "cloud-free-area" else 0.0
    add_lw = p["offset_lw"] if convention == "cloud-free-area" else 0.0
    phase = 2.0 * math.pi * (month - t["annual_peak_month"]) / 12.0
    sw = p["sw"] + add_sw + t["annual_amplitude_shortwave_W_m2"] * math.cos(phase)
    lw = p["lw"] + add_lw + t["annual_amplitude_longwave_W_m2"] * math.cos(phase)
    return sw, lw


def make_fixture(seed: int) -> dict:
    """A synthetic record in the shape of the loader's CSV. One all-sky
    series per region, as the product carries one all-sky field; the
    total-region clear-sky column formed from a planted cloud radiative
    effect; the cloud-free-area column formed from that same effect
    plus the planted offset and a small independent part, as the
    product's two clear-sky fields are two measurements of nearly the
    same thing; the net columns formed from the other two, so the
    decomposition holds by construction."""
    t = TRUTH
    k0, k1 = ym(FIXTURE_SPAN[0]), ym(FIXTURE_SPAN[1])
    dates = [label(k) for k in range(k0, k1 + 1)]
    n = len(dates)
    rows = {}
    for region in REGIONS:
        e_sw = normals(seed, f"{region}/sw", n)
        e_lw = normals(seed, f"{region}/lw", n)
        e_all = normals(seed, f"{region}/all", n)
        e_off_sw = normals(seed, f"{region}/offset-sw", n)
        e_off_lw = normals(seed, f"{region}/offset-lw", n)
        i_sw = ar1(seed, f"{region}/sw-interannual", n, t["interannual_ar1"]["phi"],
                   t["interannual_ar1"]["sigma_W_m2"])
        i_lw = ar1(seed, f"{region}/lw-interannual", n, t["interannual_ar1"]["phi"],
                   t["interannual_ar1"]["sigma_W_m2"])
        series = {c: {k: [] for k in ("month", "sw_all", "lw_all", "net_all",
                                      "sw_clr", "lw_clr", "net_clr")}
                  for c in CONVENTIONS}
        for i, d in enumerate(dates):
            month = int(d[5:7])
            phase = 2.0 * math.pi * (month - t["annual_peak_month"]) / 12.0
            sw_all = (t["all_sky_shortwave_W_m2"] + 4.0 * math.cos(phase)
                      + t["noise_sigma_W_m2"] * e_all[i])
            lw_all = t["all_sky_longwave_W_m2"] + 2.0 * math.cos(phase)
            base_sw, base_lw = fixture_deterministic(region, "total-region", month)
            cre_sw = base_sw + i_sw[i] + t["noise_sigma_W_m2"] * e_sw[i]
            cre_lw = base_lw + i_lw[i] + t["noise_sigma_W_m2"] * e_lw[i]
            planted = t["planted"][region]
            for convention in CONVENTIONS:
                if convention == "cloud-free-area":
                    c_sw = cre_sw + planted["offset_sw"] + t["offset_sigma_W_m2"] * e_off_sw[i]
                    c_lw = cre_lw + planted["offset_lw"] + t["offset_sigma_W_m2"] * e_off_lw[i]
                else:
                    c_sw, c_lw = cre_sw, cre_lw
                sw_clr, lw_clr = sw_all + c_sw, lw_all + c_lw
                s = series[convention]
                s["month"].append(d)
                s["sw_all"].append(sw_all)
                s["lw_all"].append(lw_all)
                s["net_all"].append(t["solar_W_m2"] - sw_all - lw_all)
                s["sw_clr"].append(sw_clr)
                s["lw_clr"].append(lw_clr)
                s["net_clr"].append(t["solar_W_m2"] - sw_clr - lw_clr)
        for convention in CONVENTIONS:
            series[convention]["uncertainty"] = {b: t["noise_sigma_W_m2"]
                                                 for b in ("sw", "lw", "net")}
            rows[f"{region}/{convention}"] = series[convention]
    return {"seed": seed, "span": list(FIXTURE_SPAN), "regions": sorted(REGIONS),
            "conventions": sorted(CONVENTIONS), "series": rows}


def fixture_digest(fx: dict) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(fx, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def fixture_truth_window(region: str, convention: str, start: str, end: str) -> dict:
    """The planted noise-free window means for a region and convention,
    and the planted contrast with the other convention."""
    n = ym(end) - ym(start) + 1
    def planted(conv):
        sw = lw = 0.0
        for j in range(n):
            a, b = fixture_deterministic(region, conv, (ym(start) + j) % 12 + 1)
            sw += a
            lw += b
        return sw / n, lw / n
    sw, lw = planted(convention)
    osw, olw = planted(other_convention(convention))
    return {"cre_shortwave_W_m2": sw, "cre_longwave_W_m2": lw, "cre_net_W_m2": sw + lw,
            "other_convention": other_convention(convention),
            "other_cre_shortwave_W_m2": osw, "other_cre_longwave_W_m2": olw,
            "other_cre_net_W_m2": osw + olw,
            "contrast_cre_net_W_m2": (sw + lw) - (osw + olw)}


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


CSV_COLUMNS = ("region", "convention", "month", "sw_all_W_m2", "lw_all_W_m2", "net_all_W_m2",
               "sw_clr_W_m2", "lw_clr_W_m2", "net_clr_W_m2", "cre_sw_uncertainty_W_m2",
               "cre_lw_uncertainty_W_m2", "cre_net_uncertainty_W_m2")


def read_csv_series(path: Path) -> dict:
    """The loader's CSV as {region/convention: series}, each series the
    columns the computation reads, months unique and in order."""
    out = {}
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != list(CSV_COLUMNS):
            raise SystemExit(f"{path.name}: columns are {reader.fieldnames}, expected "
                             f"{list(CSV_COLUMNS)}")
        for row in reader:
            key = f"{row['region'].strip()}/{row['convention'].strip()}"
            s = out.setdefault(key, {c: [] for c in ("month", "sw_all", "lw_all", "net_all",
                                                     "sw_clr", "lw_clr", "net_clr",
                                                     "unc_sw", "unc_lw", "unc_net")})
            s["month"].append(row["month"].strip())
            for name, col in (("sw_all", "sw_all_W_m2"), ("lw_all", "lw_all_W_m2"),
                              ("net_all", "net_all_W_m2"), ("sw_clr", "sw_clr_W_m2"),
                              ("lw_clr", "lw_clr_W_m2"), ("net_clr", "net_clr_W_m2"),
                              ("unc_sw", "cre_sw_uncertainty_W_m2"),
                              ("unc_lw", "cre_lw_uncertainty_W_m2"),
                              ("unc_net", "cre_net_uncertainty_W_m2")):
                s[name].append(float(row[col]))
    for key, s in out.items():
        if s["month"] != sorted(s["month"]) or len(set(s["month"])) != len(s["month"]):
            raise SystemExit(f"{path.name}: months of {key} must be unique and in order")
    return out


def read_data_root(root: Path) -> dict:
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
    for name in ("cre-fluxes.csv", "cre-fluxes-stamp.json"):
        if name not in files:
            raise SystemExit(f"RECORD.json manifest lacks {name}")
    stamp = json.loads((root / "cre-fluxes-stamp.json").read_text(encoding="utf-8"))
    return {"series": read_csv_series(root / "cre-fluxes.csv"), "record": record, "stamp": stamp,
            "files": files, "record_sha256": sha256_file(record_path),
            "data_root": tree_label(root)}


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
    removed (the annual cycle taken out of what is summarised)."""
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
    block.update({"stated": True, "sd": sd, "t_quantile": tq,
                  "half_width": tq * sd / math.sqrt(n_eff)})
    return block


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


# ---- the computation

def cre_series(series: dict, used):
    """The three cloud radiative effect series over the months used:
    clear-sky minus all-sky in the outgoing shortwave and longwave, and
    all-sky minus clear-sky in the net downward flux, which is the
    product's own arithmetic."""
    by = {d: i for i, d in enumerate(series["month"])}
    idx = [by[d] for d in used]
    return {
        "cre_shortwave": [series["sw_clr"][i] - series["sw_all"][i] for i in idx],
        "cre_longwave": [series["lw_clr"][i] - series["lw_all"][i] for i in idx],
        "cre_net": [series["net_all"][i] - series["net_clr"][i] for i in idx],
    }


def uncertainty_series(series: dict, used):
    by = {d: i for i, d in enumerate(series["month"])}
    idx = [by[d] for d in used]
    if "unc_sw" in series:
        return {"cre_shortwave": [series["unc_sw"][i] for i in idx],
                "cre_longwave": [series["unc_lw"][i] for i in idx],
                "cre_net": [series["unc_net"][i] for i in idx]}
    u = series["uncertainty"]
    return {"cre_shortwave": [u["sw"]] * len(idx), "cre_longwave": [u["lw"]] * len(idx),
            "cre_net": [u["net"]] * len(idx)}


def term_block(name, t_cal, values, uncertainty, stamp_name) -> dict:
    block = mean_block(t_cal, values, uncertainty)
    if not block["stated"]:
        return {"stated": False, "mean_block": block}
    return {
        "stated": True,
        "value": block["mean"], "units": "W m-2 of the region",
        "uncertainty": max(block["half_width"], block["formal_95"]),
        "uncertainty_basis": "the larger of the 95 percent sampling half width of the window "
                             "mean under the lag-1 autocorrelated residual about the "
                             "calendar-month means and the formal error the per-month floor "
                             "propagates to the mean",
        "sampling_half_width_W_m2": block["half_width"],
        "formal_95_W_m2": block["formal_95"],
        "rule": {"cre_shortwave": "the clear-sky minus the all-sky outgoing shortwave flux",
                 "cre_longwave": "the clear-sky minus the all-sky outgoing longwave flux",
                 "cre_net": "the all-sky minus the clear-sky net downward flux, from the "
                            "product's net fields and not from the two terms above"}[name],
        "mean_block": block, "stamp": stamp_name,
    }


def contrast(series_by_key: dict, region: str, convention: str, used, stamp_name):
    """The other convention's three terms over the same months, and the
    difference this run's convention makes."""
    other = other_convention(convention)
    s = series_by_key.get(f"{region}/{other}")
    if s is None:
        return {"convention": other, "available": False,
                "reason": f"the record carries no {region}/{other} series",
                "statement": "the price of the convention could not be stated from this record"}
    have = set(s["month"])
    if not set(used) <= have:
        return {"convention": other, "available": False,
                "reason": f"the {other} series does not carry every month used",
                "statement": "the price of the convention could not be stated from this record"}
    cre = cre_series(s, used)
    means = {k: sum(v) / len(v) for k, v in cre.items()}
    return {
        "convention": other, "available": True, "months": len(used),
        "convention_statement": CONVENTIONS[other]["statement"],
        "cre_shortwave": means["cre_shortwave"], "cre_longwave": means["cre_longwave"],
        "cre_net": means["cre_net"],
        "published_adjustment": dict(PUBLISHED_CONVENTION_ADJUSTMENT),
        "rule": "the same three terms over the same months and region under the other "
                "clear-sky convention the product carries, and this run's terms minus them",
        "stamp": stamp_name,
    }


def published_block(region: str, convention: str, start: str, end: str, terms):
    """The published global mean cloud radiative effect and the distance
    from it, stated only where the run is of its region, convention and
    period."""
    pub = dict(PUBLISHED_GLOBAL_MEAN)
    same_region = region == PUBLISHED_GLOBAL_MEAN["region"]
    same_convention = convention == PUBLISHED_GLOBAL_MEAN["convention"]
    same_period = [start, end] == PUBLISHED_GLOBAL_MEAN["period"]
    out = {"published": pub, "region_matches": same_region,
           "convention_matches": same_convention, "period_matches": same_period,
           "comparable": bool(same_region and same_convention and same_period)}
    if out["comparable"]:
        out["distance_W_m2"] = {
            "cre_shortwave": terms["cre_shortwave"]["value"] - pub["cre_shortwave_W_m2"],
            "cre_longwave": terms["cre_longwave"]["value"] - pub["cre_longwave_W_m2"],
            "cre_net": terms["cre_net"]["value"] - pub["cre_net_W_m2"]}
        out["statement"] = ("the run is over the published number's region, convention and "
                            "period, so the distance is stated; the published values are "
                            "rounded to 0.1 W m-2 and come from an Edition 4.0 file, while "
                            "this run reads Edition 4.2.1, so the distance carries both the "
                            "rounding and the edition change")
    else:
        why = []
        if not same_region:
            why.append(f"the region is {region}, not {pub['region']}")
        if not same_convention:
            why.append(f"the convention is {convention}, not {pub['convention']}")
        if not same_period:
            why.append(f"the window is {start}:{end}, not "
                       f"{pub['period'][0]}:{pub['period'][1]}")
        out["distance_W_m2"] = None
        out["statement"] = ("no distance is stated: " + "; ".join(why)
                            + ". The published number is a global, cloud-free-area, July 2005 "
                              "through June 2015 mean, and a distance from it would compare "
                              "quantities of different definition")
    return out


def compute(series_by_key: dict, region: str, convention: str, start: str, end: str,
            bookkeeping: dict, stamp_name: str):
    """(receipt body, None) or (None, (reason_code, reason))."""
    key = f"{region}/{convention}"
    series = series_by_key.get(key)
    if series is None:
        return None, ("region-not-resolvable",
                      f"the record carries no series for {key}; the regions it carries are "
                      + ", ".join(sorted({k.split('/')[0] for k in series_by_key})))
    k0, k1 = ym(start), ym(end)
    calendar = [label(k) for k in range(k0, k1 + 1)]
    n_calendar = len(calendar)
    have = set(series["month"])
    used = [d for d in calendar if d in have]
    missing = [d for d in calendar if d not in have]
    if n_calendar < MIN_MONTHS or len(used) < MIN_MONTHS:
        return None, ("too-few-months",
                      f"{len(used)} of {n_calendar} months of {start}:{end} carry a value for "
                      f"{key}; the cloud radiative effect needs at least {MIN_MONTHS}")
    t_cal = [ym(d) - k0 for d in used]
    cre = cre_series(series, used)
    unc = uncertainty_series(series, used)
    terms = {}
    for name in TERMS:
        block = term_block(name, t_cal, cre[name], unc[name], stamp_name)
        if not block["stated"]:
            return None, ("interval-not-stated",
                          f"the window mean of {name} carries no half width "
                          f"({block['mean_block']['reason']}); no uncertainty can be stated")
        terms[name] = block
    residual = terms["cre_net"]["value"] - (terms["cre_shortwave"]["value"]
                                            + terms["cre_longwave"]["value"])
    combined = math.sqrt(sum(terms[n]["uncertainty"] ** 2 for n in TERMS))
    per_month = [cre["cre_net"][i] - cre["cre_shortwave"][i] - cre["cre_longwave"][i]
                 for i in range(len(used))]
    closes = abs(residual) <= DECOMPOSITION_TOLERANCE

    by = {d: i for i, d in enumerate(series["month"])}
    idx = [by[d] for d in used]
    book = json.loads(json.dumps(bookkeeping))
    book["convention"].update({
        "bound": convention,
        "variable_suffix": CONVENTIONS[convention]["variable_suffix"],
        "definition": CONVENTIONS[convention]["statement"],
        "source": CONVENTIONS[convention]["source"],
        "carried_by_the_product": sorted(CONVENTIONS),
        "not_carried": dict(CONVENTIONS_NOT_CARRIED),
        "inheritance": "a cloud radiative effect is all-sky minus clear-sky in every one of "
                       "these products, so it inherits the convention of the field it "
                       "subtracts, and nothing in a difference of two flux variables records "
                       "which one that was; this receipt records it",
    })
    book["region"].update({
        "bound": region,
        "latitude_band": list(REGIONS[region]),
        "resolvable": sorted(REGIONS),
        "not_resolvable": dict(REGIONS_NOT_RESOLVABLE),
        "rule": "a band of whole one degree zones, so the regional mean is the product's own "
                "global mean restricted to those zones",
    })
    book["window_handling"] = {
        "rule": "a calendar month of the window with no value for this region and convention "
                "is a hole, dropped from the mean and never interpolated",
        "months_missing": missing,
        "whole_years": n_calendar % 12 == 0,
        "note": "a window that is not whole years leaves part of the annual cycle in the mean; "
                "the mean is the arithmetic mean over the months used, as stated",
    }
    book["decomposition"] = {
        "rule": "cre_net minus (cre_shortwave plus cre_longwave); the decomposition is an "
                "identity of the product's own fields, since the net flux is the solar "
                "irradiance minus the outgoing shortwave and longwave fluxes",
        "tolerance_W_m2": DECOMPOSITION_TOLERANCE,
        "tolerance_basis": "two orders of magnitude above the storage and rounding granularity "
                           "of the six fields that enter the residual and three below the "
                           "smallest term, so a residual outside it is a disagreement between "
                           "the product's fields and not noise",
    }
    book["sign_convention"] = {
        "statement": "the shortwave and longwave fields are outgoing fluxes and the net field "
                     "is downward minus upward; the shortwave effect is negative where clouds "
                     "reflect more sunlight than the clear column and the longwave effect "
                     "positive where clouds reduce the flux to space",
        "source": "the CERES_EBAF_Ed4.2 and Ed4.2.1 Data Quality Summary: cloud radiative "
                  "effects are computed as all-sky flux minus clear-sky flux, the net being "
                  "downward minus upward",
    }
    book["published_anchor"] = dict(PUBLISHED_GLOBAL_MEAN)

    body = {
        "months": {"window": [start, end], "n_calendar": n_calendar, "n_used": len(used),
                   "used": used, "missing": missing},
        "series": {
            "dates": used,
            "sw_all_W_m2": [series["sw_all"][i] for i in idx],
            "lw_all_W_m2": [series["lw_all"][i] for i in idx],
            "net_all_W_m2": [series["net_all"][i] for i in idx],
            "sw_clr_W_m2": [series["sw_clr"][i] for i in idx],
            "lw_clr_W_m2": [series["lw_clr"][i] for i in idx],
            "net_clr_W_m2": [series["net_clr"][i] for i in idx],
            "cre_shortwave_W_m2": cre["cre_shortwave"],
            "cre_longwave_W_m2": cre["cre_longwave"],
            "cre_net_W_m2": cre["cre_net"],
            "uncertainty_cre_shortwave_W_m2": unc["cre_shortwave"],
            "uncertainty_cre_longwave_W_m2": unc["cre_longwave"],
            "uncertainty_cre_net_W_m2": unc["cre_net"],
        },
        "terms": terms,
        "cre_shortwave_W_m2": round(terms["cre_shortwave"]["value"], 4),
        "cre_longwave_W_m2": round(terms["cre_longwave"]["value"], 4),
        "cre_net_W_m2": round(terms["cre_net"]["value"], 4),
        "residual": {"value": residual, "units": "W m-2 of the region",
                     "rule": "cre_net minus (cre_shortwave plus cre_longwave)",
                     "max_abs_per_month": max(abs(v) for v in per_month),
                     "sum_of_parts": terms["cre_shortwave"]["value"] + terms["cre_longwave"]["value"]},
        "combined_uncertainty": {"value": combined, "units": "W m-2 of the region",
                                 "rule": "the three term uncertainties in quadrature"},
        "verdict": {"decomposition_closes": closes,
                    "rule": "closed when the residual lies within the stated decomposition "
                            "tolerance, which is the granularity of the product's fields and "
                            "not the sampling bar",
                    "residual_W_m2": residual, "bar_W_m2": DECOMPOSITION_TOLERANCE,
                    "combined_uncertainty_W_m2": combined},
        "convention_contrast": contrast(series_by_key, region, convention, used, stamp_name),
        "published_comparison": published_block(region, convention, start, end, terms),
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
        "bound_parameters": {"window": args.window, "region": args.region,
                             "clear_sky": args.clear_sky},
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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--window", required=True, help="YYYY-MM:YYYY-MM (declared parameter)")
    ap.add_argument("--region", required=True,
                    help="the region whose mask the computation resolves (declared parameter)")
    ap.add_argument("--clear-sky", required=True, dest="clear_sky",
                    help="the clear-sky convention the effect is formed against "
                         "(declared parameter)")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--fixture", action="store_true", help="the synthetic record")
    mode.add_argument("--data-root", type=Path, help="a recorded tree (execution plumbing)")
    ap.add_argument("--seed", type=int, default=7, help="fixture seed (default 7)")
    ap.add_argument("--runtime", required=True,
                    help="the runtime that ran this (claude-code, a gate's name, ...)")
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
        fx = make_fixture(args.seed)
        data = {"mode": "fixture", "seed": args.seed, "span": list(FIXTURE_SPAN),
                "digest": fixture_digest(fx),
                "generator": COMPUTATION + " (make_fixture)",
                "generator_sha256": sha256_file(Path(__file__).resolve()),
                "truth": json.loads(json.dumps(TRUTH))}
        series_by_key, bookkeeping, span = fx["series"], FIXTURE_BOOKKEEPING, FIXTURE_SPAN
        stamp_name = "fixture"
    else:
        tree = read_data_root(args.data_root)
        data = {"mode": "data-root", "data_root": tree["data_root"],
                "record": tree["record"].get("record"),
                "record_sha256": tree["record_sha256"],
                "manifest_sha256": tree["record"].get("manifest_sha256"),
                "files": tree["files"], "stamp": tree["stamp"]}
        series_by_key, bookkeeping = tree["series"], tree["record"]["bookkeeping"]
        span = tuple(tree["stamp"].get("months") or ["", ""])
        stamp_name = "cre-fluxes-stamp.json"
    head = receipt_head(args, capability, bundle, data)

    refusal = None
    if args.clear_sky not in CONVENTIONS:
        why = CONVENTIONS_NOT_CARRIED.get(args.clear_sky)
        refusal = ("clear-sky-convention-not-carried",
                   f"the clear-sky convention {args.clear_sky!r} is not one the energy "
                   f"balanced product carries ({', '.join(sorted(CONVENTIONS))})"
                   + (f": it is {why}" if why else "")
                   + "; a cloud radiative effect inherits the convention of the field it "
                     "subtracts, so no number is computed against a field the product has not")
    elif args.region not in REGIONS:
        why = REGIONS_NOT_RESOLVABLE.get(args.region)
        refusal = ("region-not-resolvable",
                   f"the region {args.region!r} is not one this computation resolves "
                   f"({', '.join(sorted(REGIONS))})"
                   + (f": it needs {why}" if why else "")
                   + "; no number is computed over a mask that cannot be resolved")
    elif not (span[0] and span[1] and ym(span[0]) <= ym(start) and ym(end) <= ym(span[1])):
        refusal = ("window-outside-record",
                   f"the window {start}:{end} lies outside the flux record "
                   f"{span[0]} through {span[1]}")
    else:
        body, refusal = compute(series_by_key, args.region, args.clear_sky, start, end,
                                bookkeeping, stamp_name)
    if refusal:
        receipt = finish({**head, "refused": True, "reason_code": refusal[0],
                          "reason": refusal[1]})
        print(f"REFUSED ({refusal[0]}): {refusal[1]}")
        write(receipt, args.receipt)
        return 3

    if args.fixture:
        truth = fixture_truth_window(args.region, args.clear_sky, start, end)
        c = body["convention_contrast"]
        body["known_truth"] = {
            "planted_cre_shortwave_W_m2": truth["cre_shortwave_W_m2"],
            "recovered_cre_shortwave_W_m2": body["terms"]["cre_shortwave"]["value"],
            "planted_cre_longwave_W_m2": truth["cre_longwave_W_m2"],
            "recovered_cre_longwave_W_m2": body["terms"]["cre_longwave"]["value"],
            "planted_cre_net_W_m2": truth["cre_net_W_m2"],
            "recovered_cre_net_W_m2": body["terms"]["cre_net"]["value"],
            "planted_contrast_cre_net_W_m2": truth["contrast_cre_net_W_m2"],
            "recovered_contrast_cre_net_W_m2": (body["terms"]["cre_net"]["value"] - c["cre_net"])
            if c.get("available") else None,
            "planted_decomposition": "the net column is formed from the shortwave and longwave "
                                     "ones, so the residual is zero up to floating point",
            "decomposition_closes": body["verdict"]["decomposition_closes"],
        }
    else:
        body["known_truth"] = None
    receipt = finish({**head, "refused": False, **body,
                      "caveats": [
                          ("a fixture run proves the chain, not the Earth; the real-data anchor "
                           "is the stamped data root run the concept records")
                          if args.fixture else
                          ("a real-data run on a stamped record: the loader's stamp states the "
                           "edition, the file, the variable each convention reads, the weights "
                           "and the uncertainty basis"),
                          "the terms carry the clear-sky convention bound above; the same "
                          "window and region under the other convention the product carries "
                          "are in convention_contrast, and the two are not interchangeable "
                          "(the bundle's ebaf-clear-sky-definitions gotcha)",
                          "the shortwave and longwave terms are formed from the product's "
                          "outgoing flux fields and the net term from its net fields, so the "
                          "residual is a check on the product's own fields and not a physical "
                          "closure",
                          "the series travels at full precision so every term, the residual "
                          "and the verdict are recomputable from the receipt",
                      ]})
    v = receipt["verdict"]
    t = receipt["terms"]
    c = receipt["convention_contrast"]
    where = f"fixture seed {args.seed}" if args.fixture else f"data root {data['data_root']}"
    print(f"cloud radiative effect {args.region} {start}:{end} on {where}, clear-sky "
          f"{args.clear_sky}: {receipt['months']['n_used']} of "
          f"{receipt['months']['n_calendar']} months used; shortwave "
          f"{t['cre_shortwave']['value']:+.4f} (unc {t['cre_shortwave']['uncertainty']:.4f}), "
          f"longwave {t['cre_longwave']['value']:+.4f} (unc "
          f"{t['cre_longwave']['uncertainty']:.4f}), net {t['cre_net']['value']:+.4f} (unc "
          f"{t['cre_net']['uncertainty']:.4f}) W m-2; residual {v['residual_W_m2']:+.2e} "
          f"against a bar of {v['bar_W_m2']}; decomposition_closes "
          f"{str(v['decomposition_closes']).lower()}", file=sys.stderr)
    if c.get("available"):
        print(f"the other convention ({c['convention']}) over the same months: net "
              f"{c['cre_net']:+.4f} W m-2, so this convention is "
              f"{t['cre_net']['value'] - c['cre_net']:+.4f} W m-2 from it", file=sys.stderr)
    p = receipt["published_comparison"]
    if p["comparable"]:
        print(f"published global mean (Edition 4.0, cloud-free-area, July 2005 through June "
              f"2015): shortwave {p['published']['cre_shortwave_W_m2']}, longwave "
              f"{p['published']['cre_longwave_W_m2']}, net {p['published']['cre_net_W_m2']} "
              f"W m-2; distance net {p['distance_W_m2']['cre_net']:+.4f}", file=sys.stderr)
    print(f"run {receipt['run_id']}")
    write(receipt, args.receipt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
