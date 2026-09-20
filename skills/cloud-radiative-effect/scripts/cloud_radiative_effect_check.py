#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Deterministic attester for the attested cloud radiative effect at the
top of the atmosphere (cloud_radiative_effect.py). Stdlib only,
consumer side, no language model.

A receipt from any runtime attests PASS (exit 0) only when ALL hold,
else FAIL (exit 1) naming the check; one line per check, `PASS name`
or `FAIL name: reason`:

  fields       every declared receipt field is present;
  code         the receipt's code_sha256 is the sanctioned executor
               beside this file (or the one --computation names), so an
               edited computation invalidates every earlier receipt;
  release      the receipt's bundle block names this tree's package
               name, version and release lock digest, and its capability
               block is well formed;
  runtime      the receipt names the runtime that produced it;
  data         a fixture regenerated here at the receipt's seed hashes
               to the receipt's digest, and the generator (the executor
               itself) to the receipt's generator digest; for a data
               root, the record name, the record's digest, the files
               read and the stamp are present, and with --data-root DIR
               the record, the CSV and the stamp in that tree hash to
               the receipt's digests (without the tree the check says
               the digests were not verified);
  convention   the bound clear-sky convention is one the product
               carries, the receipt's convention bookkeeping is the
               sanctioned block for it, and the contrast block names
               the other convention;
  region       the bound region is one the computation resolves and the
               receipt's region bookkeeping carries its sanctioned
               latitude band;
  series       the months used and missing partition the window, the
               three cloud radiative effect series are the stated
               differences of the six flux columns (clear-sky minus
               all-sky in the outgoing shortwave and longwave,
               all-sky minus clear-sky in the net), and on a fixture
               the flux columns are what the regenerated fixture
               yields (1e-9);
  recompute    the three window means with their half widths and formal
               errors, the term uncertainties, the residual, the
               combined uncertainty, the verdict, the other
               convention's three terms and the distance from the
               published global mean recompute here from the receipt
               (1e-9 relative): an independent recompute of the method
               statement, with its own Student's t from the density;
  bookkeeping  every required statement is present, the published
               anchor block is the sanctioned one, the decomposition
               tolerance is the sanctioned one, the window handling
               lists exactly the months missing, and the sign
               convention is stated;
  plausible    stated bounds: the shortwave term between -120 and 0
               W m-2, the longwave between -10 and 60, the net between
               -80 and 20, the per-month uncertainties positive and
               below 20; and on the fixture the known truth: each
               recovered term within 1.5 W m-2 of the planted one, the
               recovered convention contrast within 0.3 of the planted
               one, and the known_truth block agreeing with the
               recompute.

A refusal receipt (refused true) attests PASS only as a refusal: the
identity checks hold, the reason code is one the executor issues, and
the refusal is reproduced here from the bound parameters and the
regenerated fixture, or from the tree --data-root names. A data-root
refusal that needs the record to reproduce and is given no tree is
taken on the executor's word and FAILS; a refusal that the bound
parameters alone settle (an unknown convention or an unresolvable
region) is reproduced either way. The verdict line of a reproduced
refusal reads `PASS refusal`, and the exit is 0.

--out writes the attestation: the verdict, whether it is a refusal, the
attester's and the computation's digests, the receipt's digest and run
id, the capability, bundle and runtime blocks copied from the receipt,
and every check.

  cloud_radiative_effect_check.py RECEIPT.json [--computation PATH]
      [--data-root DIR] [--out ATTESTATION.json]
  cloud_radiative_effect_check.py --selftest
"""

import argparse
import contextlib
import csv
import datetime as dt
import hashlib
import importlib.util
import io
import json
import math
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_COMPUTATION = HERE / "cloud_radiative_effect.py"
FIELDS = ("run_id", "computation", "code_sha256", "capability", "bundle", "runtime",
          "generated_utc", "data", "bound_parameters", "refused", "months", "series", "terms",
          "cre_shortwave_W_m2", "cre_longwave_W_m2", "cre_net_W_m2", "residual",
          "combined_uncertainty", "verdict", "convention_contrast", "published_comparison",
          "bookkeeping", "known_truth", "caveats")
REFUSAL_FIELDS = ("run_id", "computation", "code_sha256", "capability", "bundle",
                  "runtime", "generated_utc", "data", "bound_parameters", "refused",
                  "reason_code", "reason")
TERMS = ("cre_shortwave", "cre_longwave", "cre_net")
REL_TOL = 1e-9
ROUNDING = 5.0e-5
CONFIDENCE = 0.95
MIN_DOF = 1.0
Z95 = 1.959963984540054
BOUNDS = {"cre_shortwave": (-120.0, 0.0), "cre_longwave": (-10.0, 60.0),
          "cre_net": (-80.0, 20.0)}
UNCERTAINTY_BOUND = 20.0
TRUTH_TERM_BAND = 1.5
TRUTH_CONTRAST_BAND = 0.3
# The refusals the bound parameters alone settle, with no record needed.
PARAMETER_REFUSALS = ("clear-sky-convention-not-carried", "region-not-resolvable")


def load(path: Path):
    spec = importlib.util.spec_from_file_location("cloud_radiative_effect", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def ym(d: str) -> int:
    return int(d[:4]) * 12 + int(d[5:7]) - 1


def label(k: int) -> str:
    return f"{k // 12:04d}-{k % 12 + 1:02d}"


def close(a, b, tol=REL_TOL) -> bool:
    if not isinstance(a, (int, float)) or isinstance(a, bool) or not isinstance(b, (int, float)):
        return False
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def numbers(v, n=None):
    return (isinstance(v, list) and (n is None or len(v) == n)
            and all(isinstance(x, (int, float)) and not isinstance(x, bool)
                    and math.isfinite(x) for x in v))


# ---- Student's t from the density, independent of the executor's incomplete beta

def t_pdf(x, df):
    return (math.exp(math.lgamma((df + 1.0) / 2.0) - math.lgamma(df / 2.0))
            / math.sqrt(df * math.pi) * (1.0 + x * x / df) ** (-(df + 1.0) / 2.0))


def t_cdf_from_zero(x, df, steps=4000):
    """The integral of the density from 0 to x by Simpson's rule."""
    if x <= 0.0:
        return 0.0
    h = x / steps
    total = t_pdf(0.0, df) + t_pdf(x, df)
    for i in range(1, steps):
        total += (4.0 if i % 2 else 2.0) * t_pdf(i * h, df)
    return total * h / 3.0


def t_quantile(p, df):
    """The two-sided quantile: the x with P(|T| <= x) = 2p - 1."""
    target = p - 0.5
    lo, hi = 0.0, 1.0
    while t_cdf_from_zero(hi, df) < target:
        hi *= 2.0
        if hi > 1e6:
            raise ArithmeticError("t quantile did not bracket")
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        if t_cdf_from_zero(mid, df) < target:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-13 * max(1.0, hi):
            break
    return 0.5 * (lo + hi)


# ---- the independent recompute of the method statement on epochs

def deseason(t_cal, y):
    tt = [float(k) for k in t_cal]
    yy = [float(v) for v in y]
    by_month = {}
    for i, k in enumerate(t_cal):
        by_month.setdefault(k % 12, []).append(i)
    for idx in by_month.values():
        my = sum(yy[i] for i in idx) / len(idx)
        mt = sum(tt[i] for i in idx) / len(idx)
        for i in idx:
            yy[i] -= my
            tt[i] -= mt
    return tt, yy


def r1_of(t_cal, e):
    ss = sum(v * v for v in e)
    num = sum(e[i] * e[i + 1] for i in range(len(e) - 1) if t_cal[i + 1] - t_cal[i] == 1)
    return (num / ss if ss > 0 else 0.0), ss


def mean_recompute(t_cal, y, unc):
    n = len(y)
    mean = sum(y) / n
    _, yy = deseason(t_cal, y)
    r1, ss = r1_of(t_cal, yy)
    n_eff = min(float(n), n * (1.0 - r1) / (1.0 + r1))
    dof = n_eff - 1.0
    out = {"n": n, "mean": mean, "r1": r1, "n_eff": n_eff, "dof": dof,
           "formal_95": Z95 * math.sqrt(sum(u * u for u in unc)) / n, "interval": False}
    if dof < MIN_DOF or n < 2:
        return out
    sd = math.sqrt(ss / (n - 1.0))
    tq = t_quantile(0.5 + CONFIDENCE / 2.0, dof)
    out.update({"interval": True, "sd": sd, "t_quantile": tq,
                "half_width": tq * sd / math.sqrt(n_eff)})
    return out


def check_mean_block(block, c):
    if not isinstance(block, dict):
        return "missing or not an object"
    if block.get("confidence") != CONFIDENCE or block.get("n") != c["n"]:
        return f"confidence {block.get('confidence')} or n {block.get('n')} (series has {c['n']})"
    for k in ("mean", "r1", "n_eff", "dof", "formal_95"):
        if not close(block.get(k), c[k]):
            return f"{k} {block.get(k)} does not recompute ({c[k]})"
    if block.get("whole_years") is not (c["n"] % 12 == 0):
        return "whole_years flag disagrees with n"
    if block.get("stated") is not True or not c["interval"]:
        return "the mean block must state a half width where the recompute does"
    for k in ("sd", "t_quantile", "half_width"):
        if not close(block.get(k), c[k]):
            return f"{k} {block.get(k)} does not recompute ({c[k]})"
    return None


def cre_from_columns(s, name):
    """The three series as the contract states them, from the flux
    columns the receipt carries."""
    if name == "cre_shortwave":
        return [a - b for a, b in zip(s["sw_clr_W_m2"], s["sw_all_W_m2"])]
    if name == "cre_longwave":
        return [a - b for a, b in zip(s["lw_clr_W_m2"], s["lw_all_W_m2"])]
    return [a - b for a, b in zip(s["net_all_W_m2"], s["net_clr_W_m2"])]


# ---- the attestation

def attest(receipt_path: Path, computation: Path, data_root=None):
    """(verdict, refusal, checks, receipt) for one receipt; data_root
    is the tree a data-root receipt is verified against, when given."""
    checks = []
    tree = Path(data_root).expanduser().resolve() if data_root else None
    tree_series = None

    def check(name, ok, detail):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})
        return bool(ok)

    try:
        r = json.loads(receipt_path.read_text(encoding="utf-8"))
        assert isinstance(r, dict)
    except (OSError, ValueError, AssertionError) as e:
        check("fields", False, f"unreadable or not a JSON object: {e}")
        return "FAIL", False, checks, {}
    mod = load(computation)
    refusal = r.get("refused") is True
    fields = REFUSAL_FIELDS if refusal else FIELDS
    missing = [f for f in fields if f not in r]
    check("fields", not missing, "all present" if not missing else f"missing {missing}")

    sanctioned = sha256_file(computation)
    check("code", r.get("code_sha256") == sanctioned,
          f"receipt {r.get('code_sha256')} vs sanctioned {sanctioned}")

    identity = mod.package_identity(mod.package_root(computation.parent))
    bundle = r.get("bundle") or {}
    cap = r.get("capability") or {}
    cap_ok = (isinstance(cap, dict) and isinstance(cap.get("name"), str) and cap["name"]
              and isinstance(cap.get("version"), str) and cap["version"]
              and "release_lock" in cap
              and (cap["release_lock"] is None
                   or re.fullmatch(r"sha256:[0-9a-f]{64}", str(cap["release_lock"]))))
    check("release", bundle == identity and bool(identity.get("name")) and cap_ok,
          f"bundle {bundle} vs this tree {identity}; capability "
          f"{'well formed' if cap_ok else 'malformed'}")
    rt = r.get("runtime") or {}
    check("runtime", isinstance(rt, dict) and isinstance(rt.get("name"), str) and bool(rt.get("name")),
          f"runtime {rt.get('name')!r} {rt.get('version') or ''}".strip())

    data = r.get("data") or {}
    bound = r.get("bound_parameters") or {}
    window = str(bound.get("window", ""))
    region = bound.get("region")
    convention = bound.get("clear_sky")
    m = re.fullmatch(r"(\d{4}-\d{2}):(\d{4}-\d{2})", window)
    start, end = (m.group(1), m.group(2)) if m else (None, None)
    fx, coverage = None, None
    if data.get("mode") == "fixture":
        seed = data.get("seed")
        ok = isinstance(seed, int) and not isinstance(seed, bool)
        if ok:
            fx = mod.make_fixture(seed)
            digest = mod.fixture_digest(fx)
            ok = (data.get("digest") == digest and data.get("generator_sha256") == sanctioned
                  and data.get("span") == list(mod.FIXTURE_SPAN)
                  and data.get("truth") == json.loads(json.dumps(mod.TRUTH)))
            detail = (f"regenerated fixture at seed {seed}: {digest}; receipt {data.get('digest')}; "
                      f"generator match {data.get('generator_sha256') == sanctioned}")
            coverage = tuple(mod.FIXTURE_SPAN)
        else:
            detail = "fixture seed missing or malformed"
        check("data", ok, detail)
    elif data.get("mode") == "data-root":
        stamp = data.get("stamp")
        files = data.get("files")
        hexd = r"sha256:[0-9a-f]{64}"
        ok = (isinstance(data.get("record"), str) and data.get("record")
              and re.fullmatch(hexd, str(data.get("record_sha256")))
              and isinstance(data.get("manifest_sha256"), str)
              and isinstance(files, dict)
              and {"cre-fluxes.csv", "cre-fluxes-stamp.json"} <= set(files)
              and all(re.fullmatch(hexd, str(v)) for v in files.values())
              and isinstance(stamp, dict) and isinstance(stamp.get("months"), list)
              and len(stamp["months"]) == 2)
        if ok:
            coverage = (stamp["months"][0], stamp["months"][1])
        detail = (f"data root {data.get('data_root')} record {data.get('record')} "
                  f"({data.get('record_sha256')})")
        if ok and tree is not None:
            problems = []
            rec_path = tree / "RECORD.json"
            if not rec_path.is_file():
                problems.append(f"{tree} carries no RECORD.json")
            else:
                if sha256_file(rec_path) != data["record_sha256"]:
                    problems.append("RECORD.json in the tree does not hash to the receipt's "
                                    "record_sha256")
                try:
                    rec = json.loads(rec_path.read_text(encoding="utf-8"))
                    if rec.get("record") != data["record"] \
                            or rec.get("manifest_sha256") != data["manifest_sha256"]:
                        problems.append("the tree's record name or manifest digest differs from "
                                        "the receipt's")
                except ValueError:
                    problems.append("RECORD.json in the tree is not JSON")
            for name, digest in files.items():
                fp = tree / name
                if not fp.is_file():
                    problems.append(f"{name} is missing from the tree")
                elif sha256_file(fp) != digest:
                    problems.append(f"{name} in the tree does not hash to the receipt's digest")
            stamp_path = tree / "cre-fluxes-stamp.json"
            if stamp_path.is_file():
                try:
                    if json.loads(stamp_path.read_text(encoding="utf-8")) != stamp:
                        problems.append("the stamp copied into the receipt differs from the tree's")
                except ValueError:
                    problems.append("the tree's stamp is not JSON")
            csv_path = tree / "cre-fluxes.csv"
            if csv_path.is_file() and not problems:
                tree_series = mod.read_csv_series(csv_path)
            ok = not problems
            detail += ("; verified against the tree: RECORD.json, the flux file and the stamp "
                       "hash to the receipt's digests" if ok else "; " + "; ".join(problems))
        elif ok:
            detail += "; digests well formed but NOT verified against a tree (give --data-root)"
        check("data", ok, detail)
    else:
        check("data", False, f"data mode {data.get('mode')!r} is neither fixture nor data-root")

    if refusal:
        code = r.get("reason_code")
        recognized = code in mod.REASONS
        reproduced, why = False, "reason not reproduced"
        source = fx["series"] if fx else tree_series
        if recognized and code == "clear-sky-convention-not-carried":
            reproduced = convention not in mod.CONVENTIONS
            why = f"the convention {convention!r} is not one the product carries: {reproduced}"
        elif recognized and code == "region-not-resolvable" and region not in mod.REGIONS:
            reproduced = True
            why = f"the region {region!r} is not one the computation resolves: {reproduced}"
        elif recognized and data.get("mode") == "data-root" and tree is None:
            why = ("a data-root refusal that needs the record is taken on the executor's word "
                   "and not reproduced: give --data-root to reproduce it from the tree")
        elif recognized and start and code == "window-outside-record" and coverage:
            reproduced = not (ym(coverage[0]) <= ym(start) and ym(end) <= ym(coverage[1]))
            why = f"the window {window} leaves {coverage[0]}..{coverage[1]}: {reproduced}"
        elif recognized and start and source is not None:
            book = (mod.FIXTURE_BOOKKEEPING if fx else
                    (json.loads((tree / "RECORD.json").read_text(encoding="utf-8"))
                     .get("bookkeeping") or {}))
            body, again = mod.compute(source, region, convention, start, end, book, "recheck")
            reproduced = body is None and again[0] == code
            why = f"the executor's compute refuses the same way: {reproduced}"
        else:
            why = "the record to reproduce the refusal from is not available"
        check("refusal", recognized and reproduced,
              f"reason_code {code!r} {'recognized' if recognized else 'unknown'}; {why}")
        verdict = "PASS" if all(c["ok"] for c in checks) else "FAIL"
        return verdict, True, checks, r

    # the bound convention and region
    book = r.get("bookkeeping") or {}
    cb = book.get("convention") if isinstance(book.get("convention"), dict) else {}
    contrast = r.get("convention_contrast") or {}
    sanctioned_conv = mod.CONVENTIONS.get(convention) or {}
    conv_ok = (convention in mod.CONVENTIONS
               and cb.get("bound") == convention
               and cb.get("variable_suffix") == sanctioned_conv.get("variable_suffix")
               and cb.get("definition") == sanctioned_conv.get("statement")
               and cb.get("source") == sanctioned_conv.get("source")
               and cb.get("carried_by_the_product") == sorted(mod.CONVENTIONS)
               and cb.get("not_carried") == dict(mod.CONVENTIONS_NOT_CARRIED)
               and contrast.get("convention") == mod.other_convention(convention))
    check("convention", conv_ok,
          f"bound {convention!r}, variable suffix {cb.get('variable_suffix')!r}, contrast "
          f"against {contrast.get('convention')!r}; the product carries "
          f"{sorted(mod.CONVENTIONS)}")
    rb = book.get("region") if isinstance(book.get("region"), dict) else {}
    region_ok = (region in mod.REGIONS and rb.get("bound") == region
                 and rb.get("latitude_band") == list(mod.REGIONS.get(region, ()))
                 and rb.get("resolvable") == sorted(mod.REGIONS)
                 and rb.get("not_resolvable") == dict(mod.REGIONS_NOT_RESOLVABLE))
    check("region", region_ok,
          f"bound {region!r}, latitude band {rb.get('latitude_band')} against the sanctioned "
          f"{list(mod.REGIONS.get(region, ()))}")

    # months and series
    months = r.get("months") or {}
    used = months.get("used") or []
    miss = months.get("missing") or []
    cal = [label(k) for k in range(ym(start), ym(end) + 1)] if start else []
    n_cal = len(cal)
    months_ok = (bool(start) and months.get("window") == [start, end]
                 and months.get("n_calendar") == n_cal and months.get("n_used") == len(used)
                 and sorted(used + miss) == cal and len(set(used)) == len(used)
                 and len(used) >= mod.MIN_MONTHS)
    s = r.get("series") or {}
    flux_cols = ("sw_all_W_m2", "lw_all_W_m2", "net_all_W_m2",
                 "sw_clr_W_m2", "lw_clr_W_m2", "net_clr_W_m2")
    unc_cols = ("uncertainty_cre_shortwave_W_m2", "uncertainty_cre_longwave_W_m2",
                "uncertainty_cre_net_W_m2")
    series_ok = (months_ok and s.get("dates") == used
                 and all(numbers(s.get(c), len(used)) for c in flux_cols)
                 and all(numbers(s.get(c), len(used)) for c in unc_cols)
                 and all(numbers(s.get(f"{n}_W_m2"), len(used)) for n in TERMS))
    detail = "months and series well formed" if series_ok else "months or series malformed"
    if series_ok:
        dev = 0.0
        for name in TERMS:
            expect = cre_from_columns(s, name)
            got = s.get(f"{name}_W_m2")
            dev = max([dev] + [abs(a - b) for a, b in zip(expect, got)])
        series_ok = dev <= 1e-9
        detail = (f"the three effect series are the stated differences of the flux columns "
                  f"(max deviation {dev:.2e})")
    if series_ok and fx:
        key = f"{region}/{convention}"
        fs = fx["series"].get(key)
        if fs is None:
            series_ok, detail = False, f"the regenerated fixture carries no {key} series"
        else:
            by = {d: i for i, d in enumerate(fs["month"])}
            expect_used = [d for d in cal if d in by]
            maxdev = 0.0
            for col, src in (("sw_all_W_m2", "sw_all"), ("lw_all_W_m2", "lw_all"),
                             ("net_all_W_m2", "net_all"), ("sw_clr_W_m2", "sw_clr"),
                             ("lw_clr_W_m2", "lw_clr"), ("net_clr_W_m2", "net_clr")):
                maxdev = max([maxdev] + [abs(fs[src][by[d]] - s[col][i])
                                         for i, d in enumerate(used) if d in by])
            series_ok = used == expect_used and maxdev <= 1e-9
            detail += (f"; {len(used)} of {n_cal} months as the regenerated fixture yields "
                       f"(max deviation {maxdev:.2e})")
    elif series_ok and tree_series is not None:
        ts = tree_series.get(f"{region}/{convention}")
        if ts is None:
            series_ok, detail = False, f"the tree carries no {region}/{convention} series"
        else:
            by = {d: i for i, d in enumerate(ts["month"])}
            expect_used = [d for d in cal if d in by]
            maxdev = 0.0
            for col, src in (("sw_all_W_m2", "sw_all"), ("lw_all_W_m2", "lw_all"),
                             ("net_all_W_m2", "net_all"), ("sw_clr_W_m2", "sw_clr"),
                             ("lw_clr_W_m2", "lw_clr"), ("net_clr_W_m2", "net_clr")):
                maxdev = max([maxdev] + [abs(ts[src][by[d]] - s[col][i])
                                         for i, d in enumerate(used) if d in by])
            series_ok = used == expect_used and maxdev <= 1e-9
            detail += f"; the months and values are the tree's (max deviation {maxdev:.2e})"
    check("series", series_ok, detail)

    # recompute
    rec_ok, rec_detail = False, "series not checkable"
    terms = r.get("terms") or {}
    if series_ok:
        problems = []
        t_cal = [ym(d) - ym(start) for d in used]
        unc_of = {"cre_shortwave": s["uncertainty_cre_shortwave_W_m2"],
                  "cre_longwave": s["uncertainty_cre_longwave_W_m2"],
                  "cre_net": s["uncertainty_cre_net_W_m2"]}
        values = {}
        for name in TERMS:
            block = terms.get(name) or {}
            c = mean_recompute(t_cal, s[f"{name}_W_m2"], unc_of[name])
            err = check_mean_block(block.get("mean_block"), c)
            if err:
                problems.append(f"{name}.mean_block: {err}")
                continue
            want = max(c["half_width"], c["formal_95"])
            if not close(block.get("value"), c["mean"]) or not close(block.get("uncertainty"), want) \
                    or not close(block.get("sampling_half_width_W_m2"), c["half_width"]) \
                    or not close(block.get("formal_95_W_m2"), c["formal_95"]):
                problems.append(f"{name} {block.get('value')} (unc {block.get('uncertainty')}) "
                                f"does not recompute ({c['mean']}, {want})")
                continue
            values[name] = (c["mean"], want)
        if len(values) == len(TERMS):
            residual = values["cre_net"][0] - values["cre_shortwave"][0] - values["cre_longwave"][0]
            combined = math.sqrt(sum(values[n][1] ** 2 for n in TERMS))
            closes = abs(residual) <= mod.DECOMPOSITION_TOLERANCE
            rs = r.get("residual") or {}
            cu = r.get("combined_uncertainty") or {}
            vd = r.get("verdict") or {}
            per_month = [cre_from_columns(s, "cre_net")[i] - cre_from_columns(s, "cre_shortwave")[i]
                         - cre_from_columns(s, "cre_longwave")[i] for i in range(len(used))]
            if not close(rs.get("value"), residual) \
                    or not close(rs.get("sum_of_parts"),
                                 values["cre_shortwave"][0] + values["cre_longwave"][0]) \
                    or not close(rs.get("max_abs_per_month"), max(abs(v) for v in per_month)):
                problems.append(f"residual {rs.get('value')} does not recompute ({residual})")
            if not close(cu.get("value"), combined):
                problems.append(f"combined_uncertainty {cu.get('value')} does not recompute "
                                f"({combined})")
            if (not close(vd.get("residual_W_m2"), residual)
                    or vd.get("bar_W_m2") != mod.DECOMPOSITION_TOLERANCE
                    or not close(vd.get("combined_uncertainty_W_m2"), combined)
                    or vd.get("decomposition_closes") is not closes):
                problems.append(f"verdict {vd.get('decomposition_closes')} does not recompute "
                                f"(closes {closes})")
            for key, want in (("cre_shortwave_W_m2", values["cre_shortwave"][0]),
                              ("cre_longwave_W_m2", values["cre_longwave"][0]),
                              ("cre_net_W_m2", values["cre_net"][0])):
                v = r.get(key)
                if not isinstance(v, (int, float)) or abs(v - want) > ROUNDING + 1e-9:
                    problems.append(f"{key} {v} is not the term rounded ({want})")
            # the other convention's terms, from the fixture or the tree
            other = mod.other_convention(convention)
            source = (fx["series"] if fx else tree_series)
            if contrast.get("available") is True and source is not None:
                os_ = source.get(f"{region}/{other}")
                if os_ is None:
                    problems.append(f"the contrast claims {other} the record does not carry")
                else:
                    by = {d: i for i, d in enumerate(os_["month"])}
                    if not set(used) <= set(by):
                        problems.append("the contrast claims months the other series lacks")
                    else:
                        cre = mod.cre_series(os_, used)
                        for name in TERMS:
                            want = sum(cre[name]) / len(used)
                            if not close(contrast.get(name), want):
                                problems.append(f"convention_contrast.{name} "
                                                f"{contrast.get(name)} does not recompute ({want})")
                        if contrast.get("months") != len(used):
                            problems.append("convention_contrast.months is not the months used")
                        if contrast.get("published_adjustment") != mod.PUBLISHED_CONVENTION_ADJUSTMENT:
                            problems.append("convention_contrast carries an unsanctioned "
                                            "published adjustment")
            # with no record in hand the contrast is not recomputable; the data
            # check is the one that says the digests were not verified
            pc = r.get("published_comparison") or {}
            pub = mod.PUBLISHED_GLOBAL_MEAN
            comparable = (region == pub["region"] and convention == pub["convention"]
                          and [start, end] == pub["period"])
            if pc.get("published") != pub or pc.get("comparable") is not comparable:
                problems.append("published_comparison does not carry the sanctioned anchor or "
                                "misstates whether the run is comparable with it")
            elif comparable:
                d = pc.get("distance_W_m2") or {}
                for name, key in (("cre_shortwave", "cre_shortwave_W_m2"),
                                  ("cre_longwave", "cre_longwave_W_m2"),
                                  ("cre_net", "cre_net_W_m2")):
                    if not close(d.get(name), values[name][0] - pub[key]):
                        problems.append(f"published_comparison.distance.{name} does not recompute")
            elif pc.get("distance_W_m2") is not None:
                problems.append("published_comparison states a distance from a number of "
                                "another region, convention or period")
        rec_ok = not problems
        rec_detail = ("; ".join(problems) if problems else
                      "the three window means, their half widths and formal errors, the term "
                      "uncertainties, the residual, the combined uncertainty, the verdict, the "
                      "other convention's terms and the published distance recompute")
    check("recompute", rec_ok, rec_detail)

    # bookkeeping
    lacking = [f"{sec}.{key}" for sec, key in mod.REQUIRED_BOOKKEEPING
               if not (isinstance(book.get(sec), dict) and book[sec].get(key) not in (None, ""))]
    wh = book.get("window_handling") if isinstance(book.get("window_handling"), dict) else {}
    dec = book.get("decomposition") if isinstance(book.get("decomposition"), dict) else {}
    sign = book.get("sign_convention") if isinstance(book.get("sign_convention"), dict) else {}
    book_ok = (not lacking
               and book.get("published_anchor") == mod.PUBLISHED_GLOBAL_MEAN
               and dec.get("tolerance_W_m2") == mod.DECOMPOSITION_TOLERANCE
               and isinstance(dec.get("rule"), str)
               and isinstance(sign.get("statement"), str) and isinstance(sign.get("source"), str)
               and isinstance(wh.get("rule"), str) and wh.get("months_missing") == miss
               and wh.get("whole_years") is (n_cal % 12 == 0))
    check("bookkeeping", book_ok,
          (f"lacks {lacking}; " if lacking else "required statements present; ")
          + f"published anchor sanctioned "
            f"{book.get('published_anchor') == mod.PUBLISHED_GLOBAL_MEAN}; decomposition "
            f"tolerance {dec.get('tolerance_W_m2')}; window handling lists {len(miss)} missing "
            f"months; sign convention {'stated' if sign.get('statement') else 'not stated'}")

    # plausibility
    if rec_ok:
        problems = []
        for name, (lo, hi) in BOUNDS.items():
            v = (terms.get(name) or {}).get("value")
            if not isinstance(v, (int, float)) or not (lo <= v <= hi):
                problems.append(f"{name} {v} outside [{lo}, {hi}] W m-2")
        for col in unc_cols:
            u = s[col]
            if min(u) <= 0 or max(u) >= UNCERTAINTY_BOUND:
                problems.append(f"{col} outside (0, {UNCERTAINTY_BOUND})")
        if fx is not None:
            kt = r.get("known_truth") or {}
            truth = mod.fixture_truth_window(region, convention, start, end)
            got = {n: terms[n]["value"] for n in TERMS}
            for name, key in (("cre_shortwave", "cre_shortwave_W_m2"),
                              ("cre_longwave", "cre_longwave_W_m2"),
                              ("cre_net", "cre_net_W_m2")):
                if abs(got[name] - truth[key]) > TRUTH_TERM_BAND:
                    problems.append(f"recovered {name} {got[name]:.4f} is more than "
                                    f"{TRUTH_TERM_BAND} from the planted {truth[key]:.4f}")
            recovered_contrast = (got["cre_net"] - contrast["cre_net"]
                                  if contrast.get("available") else None)
            if recovered_contrast is None:
                problems.append("a fixture receipt carries no convention contrast")
            elif abs(recovered_contrast - truth["contrast_cre_net_W_m2"]) > TRUTH_CONTRAST_BAND:
                problems.append(f"recovered convention contrast {recovered_contrast:.4f} is more "
                                f"than {TRUTH_CONTRAST_BAND} from the planted "
                                f"{truth['contrast_cre_net_W_m2']:.4f}")
            if (not close(kt.get("planted_cre_shortwave_W_m2"), truth["cre_shortwave_W_m2"])
                    or not close(kt.get("recovered_cre_shortwave_W_m2"), got["cre_shortwave"])
                    or not close(kt.get("planted_cre_longwave_W_m2"), truth["cre_longwave_W_m2"])
                    or not close(kt.get("recovered_cre_longwave_W_m2"), got["cre_longwave"])
                    or not close(kt.get("planted_cre_net_W_m2"), truth["cre_net_W_m2"])
                    or not close(kt.get("recovered_cre_net_W_m2"), got["cre_net"])
                    or not close(kt.get("planted_contrast_cre_net_W_m2"),
                                 truth["contrast_cre_net_W_m2"])
                    or not close(kt.get("recovered_contrast_cre_net_W_m2"), recovered_contrast)
                    or kt.get("decomposition_closes") is not r["verdict"]["decomposition_closes"]):
                problems.append("known_truth block disagrees with the recompute")
        elif r.get("known_truth") is not None:
            problems.append("a data-root receipt carries a known_truth block")
        check("plausible", not problems, "; ".join(problems) if problems else
              "terms within the stated bounds" + ("; the known truth holds" if fx is not None
                                                  else "; a data root carries no known truth"))
    else:
        check("plausible", False, "not checkable: the recompute failed")

    verdict = "PASS" if all(c["ok"] for c in checks) else "FAIL"
    return verdict, False, checks, r


def attestation_doc(verdict, refusal, checks, r, receipt_path, computation):
    return {
        "verdict": verdict,
        "refusal": refusal,
        "attester": "skills/cloud-radiative-effect/scripts/cloud_radiative_effect_check.py",
        "attester_sha256": sha256_file(Path(__file__).resolve()),
        "computation_sha256": sha256_file(computation),
        "receipt": receipt_path.name,
        "receipt_sha256": sha256_file(receipt_path),
        "run_id": r.get("run_id"),
        "capability": r.get("capability") or {},
        "bundle": r.get("bundle") or {},
        "runtime": r.get("runtime") or {},
        "attested_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "checks": checks,
    }


def report(verdict, refusal, checks, r) -> str:
    lines = [f"PASS {c['name']}" if c["ok"] else f"FAIL {c['name']}: {c['detail']}" for c in checks]
    bound = r.get("bound_parameters") or {}
    if verdict != "PASS":
        first = next(c for c in checks if not c["ok"])
        lines.append(f"FAIL {first['name']}: {first['detail']}")
    elif refusal:
        lines.append(f"PASS refusal ({r.get('reason_code')}) run {r.get('run_id')}: "
                     f"{bound.get('region')} {bound.get('window')} clear-sky "
                     f"{bound.get('clear_sky')} refused, {r.get('reason')}")
    else:
        v, t = r["verdict"], r["terms"]
        c = r.get("convention_contrast") or {}
        p = r.get("published_comparison") or {}
        tail = ""
        if c.get("available"):
            tail += (f"; the other convention ({c['convention']}) gives net "
                     f"{c['cre_net']:+.4f}, a difference of "
                     f"{t['cre_net']['value'] - c['cre_net']:+.4f}")
        if p.get("comparable"):
            tail += (f"; published net {p['published']['cre_net_W_m2']} W m-2, distance "
                     f"{p['distance_W_m2']['cre_net']:+.4f}")
        lines.append(f"PASS run {r.get('run_id')}: {bound.get('region')} {bound.get('window')} "
                     f"clear-sky {bound.get('clear_sky')}, {r['months']['n_used']} of "
                     f"{r['months']['n_calendar']} months, shortwave "
                     f"{t['cre_shortwave']['value']:+.4f}, longwave "
                     f"{t['cre_longwave']['value']:+.4f}, net {t['cre_net']['value']:+.4f} "
                     f"W m-2, residual {v['residual_W_m2']:+.2e} against bar {v['bar_W_m2']}, "
                     f"decomposition_closes {str(v['decomposition_closes']).lower()}"
                     + tail + " (recomputed)")
    return "\n".join(lines)


# ---- selftest

def synthetic_root(mod, root: Path, seed: int = 11, smooth: bool = False):
    """A stamped data root from the fixture's own series, so the
    data-root path is exercised offline; with smooth, every effect
    series is a noise-free straight line, whose residual
    autocorrelation leaves no degrees of freedom."""
    fx = mod.make_fixture(seed)
    rows = []
    for key, s in sorted(fx["series"].items()):
        region, convention = key.split("/")
        n = len(s["month"])
        for i in range(n):
            sw_all, lw_all = s["sw_all"][i], s["lw_all"][i]
            if smooth:
                cre_sw = -45.0 + 0.01 * i
                cre_lw = 26.0 - 0.005 * i
                sw_clr, lw_clr = sw_all + cre_sw, lw_all + cre_lw
                net_all = 340.0 - sw_all - lw_all
                net_clr = 340.0 - sw_clr - lw_clr
            else:
                sw_clr, lw_clr = s["sw_clr"][i], s["lw_clr"][i]
                net_all, net_clr = s["net_all"][i], s["net_clr"][i]
            rows.append([region, convention, s["month"][i],
                         f"{sw_all:.6f}", f"{lw_all:.6f}", f"{net_all:.6f}",
                         f"{sw_clr:.6f}", f"{lw_clr:.6f}", f"{net_clr:.6f}",
                         "0.400000", "0.400000", "0.400000"])
    rows.sort(key=lambda r: (r[0], r[1], r[2]))
    with (root / "cre-fluxes.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(list(mod.CSV_COLUMNS))
        w.writerows(rows)
    months = sorted({r[2] for r in rows})
    stamp = {"term": "cre-fluxes", "product": "synthetic", "product_version": "selftest",
             "doi": "none", "file": "none", "months": [months[0], months[-1]],
             "n_months": len(months), "weights": "selftest", "mask": "selftest",
             "uncertainty_basis": "planted noise",
             "clear_sky_conventions": {name: {"variable_suffix": b["variable_suffix"],
                                              "variables": [f"toa_x_{b['variable_suffix']}_mon"]}
                                       for name, b in mod.CONVENTIONS.items()}}
    (root / "cre-fluxes-stamp.json").write_text(json.dumps(stamp, indent=2) + "\n",
                                                encoding="utf-8")
    (root / "SOURCES.json").write_text("{}\n", encoding="utf-8")
    files = {n: sha256_file(root / n)
             for n in ("cre-fluxes.csv", "cre-fluxes-stamp.json", "SOURCES.json")}
    mh = hashlib.sha256("\n".join(f"{k} {v}" for k, v in sorted(files.items())).encode()).hexdigest()
    record = {"record": "selftest-root", "manifest": files, "manifest_sha256": "sha256:" + mh,
              "verified_utc": "2026-01-01T00:00:00Z", "terms": {"cre-fluxes": stamp},
              "bookkeeping": {"convention": {"statement": "selftest"},
                              "weighting": {"statement": "selftest"},
                              "edition": {"statement": "selftest"},
                              "uncertainty": {"basis": "selftest"},
                              "region": {"statement": "selftest"}}}
    (root / "RECORD.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return root


def selftest(computation: Path) -> int:
    mod = load(computation)

    def run(argv, path):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = mod.main([*argv, "--runtime", "selftest", "--receipt", str(path)])
        return rc

    def verdict_of(path, comp=None, root=None):
        v, refusal, checks, _ = attest(path, comp or computation, root)
        failed = [c["name"] for c in checks if not c["ok"]]
        return v, refusal, failed

    def first_fail(path, comp=None, root=None):
        v, _, failed = verdict_of(path, comp, root)
        return failed[0] if v == "FAIL" and failed else None

    def tampered(src: Path, dst: Path, edit):
        doc = json.loads(src.read_text(encoding="utf-8"))
        edit(doc)
        dst.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        return dst

    # the two Student's t implementations agree
    for df in (3.0, 17.5, 98.03, 400.0):
        assert abs(t_quantile(0.975, df) - mod.t_quantile(0.975, df)) < 1e-9, df

    base = ["--fixture", "--seed", "7", "--region", "global", "--clear-sky", "total-region"]
    with tempfile.TemporaryDirectory() as d:
        w = Path(d)
        ref = w / "ref.json"
        assert run([*base, "--window", "2006-01:2020-12"], ref) == 0
        assert verdict_of(ref) == ("PASS", False, []), verdict_of(ref)
        v, refusal, checks, r = attest(ref, computation)
        assert "PASS run" in report(v, refusal, checks, r)
        assert "the other convention" in report(v, refusal, checks, r)

        # a polar region and the other convention attest too
        alt = w / "alt.json"
        assert run(["--fixture", "--seed", "7", "--region", "antarctic",
                    "--clear-sky", "cloud-free-area", "--window", "2006-01:2020-12"], alt) == 0
        assert verdict_of(alt) == ("PASS", False, []), verdict_of(alt)

        # tampers, each failing on its check
        t1 = tampered(ref, w / "t1.json", lambda r: r["series"]["sw_clr_W_m2"].__setitem__(
            3, r["series"]["sw_clr_W_m2"][3] + 1e-6))
        assert first_fail(t1) == "series", verdict_of(t1)
        t2 = tampered(ref, w / "t2.json", lambda r: r["terms"]["cre_net"]["mean_block"].__setitem__(
            "mean", r["terms"]["cre_net"]["mean_block"]["mean"] * 1.001))
        assert first_fail(t2) == "recompute", verdict_of(t2)
        t3 = tampered(ref, w / "t3.json",
                      lambda r: r["verdict"].__setitem__("decomposition_closes", False))
        assert first_fail(t3) == "recompute", verdict_of(t3)
        t4 = tampered(ref, w / "t4.json", lambda r: r["terms"]["cre_shortwave"].__setitem__(
            "uncertainty", r["terms"]["cre_shortwave"]["uncertainty"] / 2))
        assert first_fail(t4) == "recompute", verdict_of(t4)
        t5 = tampered(ref, w / "t5.json", lambda r: r["convention_contrast"].__setitem__(
            "cre_net", r["convention_contrast"]["cre_net"] + 0.5))
        assert first_fail(t5) == "recompute", verdict_of(t5)
        t6 = tampered(ref, w / "t6.json", lambda r: r["bookkeeping"]["convention"].pop("statement"))
        assert verdict_of(t6)[2] == ["bookkeeping"], verdict_of(t6)
        t7 = tampered(ref, w / "t7.json", lambda r: r["runtime"].__setitem__("name", ""))
        assert verdict_of(t7)[2] == ["runtime"], verdict_of(t7)
        t8 = tampered(ref, w / "t8.json", lambda r: r["data"].__setitem__("seed", 8))
        assert first_fail(t8) == "data", verdict_of(t8)
        t9 = tampered(ref, w / "t9.json", lambda r: r["known_truth"].__setitem__(
            "planted_cre_net_W_m2", 0.0))
        assert verdict_of(t9)[2] == ["plausible"], verdict_of(t9)
        # a relabelled convention: the bookkeeping no longer matches the bound name
        t10 = tampered(ref, w / "t10.json",
                       lambda r: r["bound_parameters"].__setitem__("clear_sky", "cloud-free-area"))
        assert "convention" in verdict_of(t10)[2], verdict_of(t10)
        # a relabelled region: the sanctioned latitude band no longer matches
        t11 = tampered(ref, w / "t11.json",
                       lambda r: r["bound_parameters"].__setitem__("region", "tropics"))
        assert "region" in verdict_of(t11)[2], verdict_of(t11)
        # a forged published distance on a run of another convention
        t12 = tampered(ref, w / "t12.json", lambda r: r["published_comparison"].__setitem__(
            "distance_W_m2", {"cre_net": 0.0}))
        assert first_fail(t12) == "recompute", verdict_of(t12)
        # an unsanctioned published anchor
        t13 = tampered(ref, w / "t13.json",
                       lambda r: r["bookkeeping"]["published_anchor"].__setitem__("cre_net_W_m2", -20.0))
        assert "bookkeeping" in verdict_of(t13)[2], verdict_of(t13)

        # wrong release: the bundle block names another version, or the capability is malformed
        w1 = tampered(ref, w / "w1.json", lambda r: r["bundle"].__setitem__("version", "0.0.0"))
        assert verdict_of(w1)[2] == ["release"], verdict_of(w1)
        w2 = tampered(ref, w / "w2.json", lambda r: r["capability"].__setitem__("name", ""))
        assert verdict_of(w2)[2] == ["release"], verdict_of(w2)

        # a tampered computation fails code and the generator digest
        bad = w / "cloud_radiative_effect.py"
        bad.write_bytes(computation.read_bytes() + b"\n")
        v, _, failed = verdict_of(ref, bad)
        assert v == "FAIL" and "code" in failed and "data" in failed, failed

        # the five refusals, each exiting 3 and attesting as a refusal
        conv = w / "convention.json"
        assert run(["--fixture", "--seed", "7", "--region", "global", "--clear-sky", "pristine",
                    "--window", "2006-01:2020-12"], conv) == 3
        assert json.loads(conv.read_text())["reason_code"] == "clear-sky-convention-not-carried"
        assert verdict_of(conv) == ("PASS", True, []), verdict_of(conv)
        v, refusal, checks, rr = attest(conv, computation)
        assert "PASS refusal" in report(v, refusal, checks, rr)
        reg = w / "region.json"
        assert run(["--fixture", "--seed", "7", "--region", "ocean", "--clear-sky",
                    "total-region", "--window", "2006-01:2020-12"], reg) == 3
        assert json.loads(reg.read_text())["reason_code"] == "region-not-resolvable"
        assert verdict_of(reg) == ("PASS", True, []), verdict_of(reg)
        out = w / "outside.json"
        assert run([*base, "--window", "1998-01:1999-12"], out) == 3
        assert json.loads(out.read_text())["reason_code"] == "window-outside-record"
        assert verdict_of(out) == ("PASS", True, []), verdict_of(out)
        few = w / "few.json"
        assert run([*base, "--window", "2020-01:2020-12"], few) == 3
        assert json.loads(few.read_text())["reason_code"] == "too-few-months"
        assert verdict_of(few) == ("PASS", True, []), verdict_of(few)
        forged = tampered(out, w / "forged.json",
                          lambda r: r["bound_parameters"].__setitem__("window", "2006-01:2020-12"))
        assert verdict_of(forged)[2] == ["refusal"], verdict_of(forged)

        # a data root: the receipt verifies against the tree, and a fabricated tree fails
        (w / "root").mkdir()
        root = synthetic_root(mod, w / "root")
        dr = w / "dr.json"
        assert run(["--data-root", str(root), "--region", "tropics", "--clear-sky",
                    "cloud-free-area", "--window", "2006-01:2020-12"], dr) == 0
        v, _, checks, rr = attest(dr, computation, root)
        assert v == "PASS" and "verified against the tree" in checks[4]["detail"], checks
        v, _, checks, _ = attest(dr, computation)
        assert v == "PASS" and "NOT verified" in checks[4]["detail"], checks
        assert rr["known_truth"] is None and rr["published_comparison"]["comparable"] is False
        fab = tampered(dr, w / "fab.json", lambda r: r["data"]["files"].__setitem__(
            "cre-fluxes.csv", "sha256:" + "1" * 64))
        assert first_fail(fab, None, root) == "data", verdict_of(fab, None, root)

        # the published anchor: a global cloud-free-area run over the published
        # decade states a distance, and the attester recomputes it
        anchor = w / "anchor.json"
        assert run(["--data-root", str(root), "--region", "global", "--clear-sky",
                    "cloud-free-area", "--window", "2005-07:2015-06"], anchor) == 0
        ra = json.loads(anchor.read_text())
        assert ra["published_comparison"]["comparable"] is True
        assert isinstance(ra["published_comparison"]["distance_W_m2"]["cre_net"], float)
        assert verdict_of(anchor, None, root) == ("PASS", False, []), verdict_of(anchor, None, root)

        # a window outside the tree's record refuses, and reproduces only against the tree
        late = w / "late.json"
        assert run(["--data-root", str(root), "--region", "global", "--clear-sky",
                    "total-region", "--window", "2030-01:2032-12"], late) == 3
        assert verdict_of(late, None, root) == ("PASS", True, []), verdict_of(late, None, root)
        # a convention refusal on a data root needs no tree: the parameters settle it
        conv2 = w / "conv2.json"
        assert run(["--data-root", str(root), "--region", "global", "--clear-sky",
                    "computed-cloud-removed", "--window", "2006-01:2020-12"], conv2) == 3
        assert verdict_of(conv2) == ("PASS", True, []), verdict_of(conv2)

        # a smooth record leaves no degrees of freedom: interval-not-stated,
        # reproduced against the tree and not without it
        (w / "smooth").mkdir()
        smooth = synthetic_root(mod, w / "smooth", smooth=True)
        ins = w / "ins.json"
        assert run(["--data-root", str(smooth), "--region", "global", "--clear-sky",
                    "total-region", "--window", "2006-01:2020-12"], ins) == 3
        assert json.loads(ins.read_text())["reason_code"] == "interval-not-stated"
        v, refusal, checks, rr = attest(ins, computation, smooth)
        assert (v, refusal) == ("PASS", True) and "PASS refusal" in report(v, refusal, checks, rr), checks
        assert verdict_of(ins)[2] == ["refusal"], verdict_of(ins)

        # the attestation document carries the verdict and the identity blocks
        doc = attestation_doc(*attest(ref, computation), ref, computation)
        assert doc["verdict"] == "PASS" and doc["capability"]["name"] and doc["runtime"]["name"] == "selftest"
        assert {c["name"] for c in doc["checks"]} == {"fields", "code", "release", "runtime",
                                                      "data", "convention", "region", "series",
                                                      "recompute", "bookkeeping", "plausible"}
    print("cloud_radiative_effect_check selftest: ok")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("receipt", nargs="?", type=Path)
    ap.add_argument("--computation", type=Path, default=DEFAULT_COMPUTATION)
    ap.add_argument("--data-root", type=Path, default=None,
                    help="the tree a data-root receipt is verified against")
    ap.add_argument("--out", type=Path, default=None, help="write the attestation JSON here")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    computation = args.computation.resolve()
    if args.selftest:
        return selftest(computation)
    if not args.receipt:
        ap.error("give a receipt, or --selftest")
    verdict, refusal, checks, r = attest(args.receipt, computation, args.data_root)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(attestation_doc(verdict, refusal, checks, r, args.receipt,
                                                       computation), indent=2) + "\n",
                            encoding="utf-8")
    print(report(verdict, refusal, checks, r) + (f"; attestation {args.out}" if args.out else ""))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
