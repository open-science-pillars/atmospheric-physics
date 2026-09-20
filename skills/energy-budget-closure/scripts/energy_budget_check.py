#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Deterministic attester for the attested energy budget closure
(energy_budget.py). Stdlib only, consumer side, no language model.

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
               read, the stamp and the Argo receipt's identity are
               present, and with --data-root DIR the record, the CSV,
               the stamp and the Argo receipt in that tree hash to the
               receipt's digests and the Argo receipt's run id and
               bound parameters are the copies in the receipt (without
               the tree the check says the digests were not verified);
  ohc-window   on a non-refusal receipt the Argo receipt's window and
               depth copied into the receipt are the bound window and
               the 0 to 2000 dbar layer (the fixture plants its own);
  series       the months used and missing partition the window, the
               anomaly is the cos-latitude series minus its own mean,
               and on a fixture the values, the uncertainties and the
               product column are what the regenerated fixture yields
               (1e-9);
  recompute    the window mean and its half width, the anomaly trend
               with its interval and formal error, the four terms in
               W m-2 (the Argo rate converted with the Earth's area,
               the deep and non-ocean terms the sanctioned published
               statements), the residual, the combined uncertainty,
               the verdict, the energy over the window, the distance
               from the published trend and the published imbalance
               recomputed here from the receipt match it (1e-9
               relative): an independent recompute of the method
               statement, with its own Student's t from the density;
  bookkeeping  every required statement is present, the anchor block
               is the sanctioned one, the months shared with the anchor
               decade are what the window gives, the window handling
               lists exactly the months missing, and the area
               convention is the sanctioned one;
  plausible    stated bounds: the toa_net term between -1 and 3 W m-2,
               the Argo rate between 0 and 2, the deep term between 0
               and 0.2, the non-ocean term between 0 and 0.3, the
               anomaly trend within 3 W m-2 per decade of zero, the
               per-month uncertainty positive and below 5 W m-2; and on
               the fixture the known truth: the recovered window mean
               within 0.3 W m-2 of the planted one, the recovered trend
               within 1 W m-2 per decade of the planted one, and the
               known_truth block agreeing with the recompute.

A refusal receipt (refused true) attests PASS only as a refusal: the
identity checks hold, the reason code is one the executor issues, and
the refusal is reproduced here from the window and the regenerated
fixture, or from the tree --data-root names (its stamp's months, the
Argo receipt's window, its CSV's months, or the executor's own compute
on its series). A data-root refusal with no tree given is taken on the
executor's word and is not reproduced, so it FAILS. The verdict line of
a reproduced refusal reads `PASS refusal`, and the exit is 0.

--out writes the attestation: the verdict, whether it is a refusal, the
attester's and the computation's digests, the receipt's digest and run
id, the capability, bundle and runtime blocks copied from the receipt,
and every check.

  energy_budget_check.py RECEIPT.json [--computation PATH] [--data-root DIR] [--out ATTESTATION.json]
  energy_budget_check.py --selftest
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
DEFAULT_COMPUTATION = HERE / "energy_budget.py"
FIELDS = ("run_id", "computation", "code_sha256", "capability", "bundle", "runtime",
          "generated_utc", "data", "bound_parameters", "refused", "months", "series", "terms",
          "toa_net_W_m2", "ocean_side_W_m2", "residual_W_m2",
          "toa_net_anomaly_trend_W_m2_per_decade", "residual", "combined_uncertainty",
          "verdict", "energy_over_window_ZJ", "published_eei", "bookkeeping", "known_truth",
          "caveats")
REFUSAL_FIELDS = ("run_id", "computation", "code_sha256", "capability", "bundle",
                  "runtime", "generated_utc", "data", "bound_parameters", "refused",
                  "reason_code", "reason")
TERMS = ("toa_net", "ohc_0_2000", "deep_ocean", "non_ocean", "toa_net_anomaly_trend")
REL_TOL = 1e-9
ROUNDING = 5.0e-5
CONFIDENCE = 0.95
MIN_DOF = 1.0
Z95 = 1.959963984540054
BOUNDS = {"toa_net": (-1.0, 3.0), "ohc_0_2000": (0.0, 2.0), "deep_ocean": (0.0, 0.2),
          "non_ocean": (0.0, 0.3)}
TREND_BOUND_PER_DECADE = 3.0
UNCERTAINTY_BOUND = 5.0
TRUTH_MEAN_BAND = 0.3
TRUTH_TREND_BAND = 1.0


def load(path: Path):
    spec = importlib.util.spec_from_file_location("energy_budget", path)
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


def trend_recompute(t_cal, y, unc):
    n = len(y)
    tt, yy = deseason(t_cal, y)
    tbar, ybar = sum(tt) / n, sum(yy) / n
    sxx = sum((a - tbar) ** 2 for a in tt)
    slope = sum((a - tbar) * (b - ybar) for a, b in zip(tt, yy)) / sxx
    icpt = ybar - slope * tbar
    e = [b - icpt - slope * a for a, b in zip(tt, yy)]
    r1, ss = r1_of(t_cal, e)
    formal = math.sqrt(sum(((a - tbar) / sxx * s) ** 2 for a, s in zip(tt, unc)))
    out = {"n": n, "trend": slope * 12.0, "trend_per_decade": slope * 120.0,
           "formal_95": Z95 * formal * 12.0, "r1": r1,
           "n_eff": min(float(n), n * (1.0 - r1) / (1.0 + r1)), "interval": False}
    out["dof"] = out["n_eff"] - 2.0
    if out["dof"] < MIN_DOF:
        return out
    se = math.sqrt(ss / out["dof"] / sxx)
    tq = t_quantile(0.5 + CONFIDENCE / 2.0, out["dof"])
    half = tq * se * 12.0
    out.update({"interval": True, "se": se * 12.0, "t_quantile": tq, "half_width": half,
                "half_width_per_decade": half * 10.0,
                "ci_low": out["trend"] - half, "ci_high": out["trend"] + half})
    return out


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
    out.update({"interval": True, "sd": sd, "t_quantile": tq, "half_width": tq * sd / math.sqrt(n_eff)})
    return out


def check_trend_block(block, c):
    if not isinstance(block, dict):
        return "missing or not an object"
    if block.get("confidence") != CONFIDENCE or block.get("n") != c["n"]:
        return f"confidence {block.get('confidence')} or n {block.get('n')} (series has {c['n']})"
    if block.get("deseasonalize") != "climatology":
        return "deseasonalize is not climatology"
    for k in ("trend", "trend_per_decade", "formal_95", "r1", "n_eff", "dof"):
        if not close(block.get(k), c[k]):
            return f"{k} {block.get(k)} does not recompute ({c[k]})"
    if block.get("stated") is False:
        if c["interval"]:
            return "block refuses an interval the recompute states"
        return None if isinstance(block.get("reason"), str) and block["reason"] else "refused interval carries no reason"
    if block.get("stated") is not True:
        return "stated must be true or false"
    if not c["interval"]:
        return "block states an interval the recompute refuses"
    for k in ("se", "t_quantile", "half_width", "half_width_per_decade", "ci_low", "ci_high"):
        if not close(block.get(k), c[k]):
            return f"{k} {block.get(k)} does not recompute ({c[k]})"
    if block.get("significant_at_confidence") is not (c["ci_low"] * c["ci_high"] > 0):
        return "significance flag disagrees with the interval"
    return None


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


def resolve_under_package(mod, computation: Path, rel):
    pkg = mod.package_root(computation.parent)
    if not isinstance(rel, str) or not rel:
        return None
    p = Path(rel)
    if p.is_absolute():
        return p
    return (pkg / p) if pkg else None


# ---- the attestation

def attest(receipt_path: Path, computation: Path, data_root=None):
    """(verdict, refusal, checks, receipt) for one receipt; data_root
    is the tree a data-root receipt is verified against, when given."""
    checks = []
    tree = Path(data_root).expanduser().resolve() if data_root else None
    tree_series, tree_ohc = None, None

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
    m = re.fullmatch(r"(\d{4}-\d{2}):(\d{4}-\d{2})", window)
    start, end = (m.group(1), m.group(2)) if m else (None, None)
    fx, coverage, ohc_window = None, None, None
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
            ohc_window = window
        else:
            detail = "fixture seed missing or malformed"
        check("data", ok, detail)
    elif data.get("mode") == "data-root":
        stamp = data.get("stamp")
        files = data.get("files")
        ohc = data.get("ohc_receipt")
        hexd = r"sha256:[0-9a-f]{64}"
        ok = (isinstance(data.get("record"), str) and data.get("record")
              and re.fullmatch(hexd, str(data.get("record_sha256")))
              and isinstance(data.get("manifest_sha256"), str)
              and isinstance(files, dict) and {"toa-net.csv", "toa-net-stamp.json"} <= set(files)
              and all(re.fullmatch(hexd, str(v)) for v in files.values())
              and isinstance(stamp, dict) and isinstance(stamp.get("months"), list)
              and len(stamp["months"]) == 2
              and isinstance(ohc, dict) and re.fullmatch(hexd, str(ohc.get("sha256")))
              and str(ohc.get("computation", "")).endswith("argo_ohc.py")
              and isinstance(ohc.get("bound_parameters"), dict))
        if ok:
            coverage = (stamp["months"][0], stamp["months"][1])
            ohc_window = ohc["bound_parameters"].get("window")
        detail = (f"data root {data.get('data_root')} record {data.get('record')} "
                  f"({data.get('record_sha256')}); Argo receipt {ohc.get('run_id') if isinstance(ohc, dict) else None}")
        if ok and tree is not None:
            problems = []
            rec_path = tree / "RECORD.json"
            if not rec_path.is_file():
                problems.append(f"{tree} carries no RECORD.json")
            else:
                if sha256_file(rec_path) != data["record_sha256"]:
                    problems.append("RECORD.json in the tree does not hash to the receipt's record_sha256")
                try:
                    rec = json.loads(rec_path.read_text(encoding="utf-8"))
                    if rec.get("record") != data["record"] or rec.get("manifest_sha256") != data["manifest_sha256"]:
                        problems.append("the tree's record name or manifest digest differs from the receipt's")
                except ValueError:
                    problems.append("RECORD.json in the tree is not JSON")
            for name, digest in files.items():
                fp = tree / name
                if not fp.is_file():
                    problems.append(f"{name} is missing from the tree")
                elif sha256_file(fp) != digest:
                    problems.append(f"{name} in the tree does not hash to the receipt's digest")
            stamp_path = tree / "toa-net-stamp.json"
            if stamp_path.is_file():
                try:
                    if json.loads(stamp_path.read_text(encoding="utf-8")) != stamp:
                        problems.append("the stamp copied into the receipt differs from the tree's")
                except ValueError:
                    problems.append("the tree's stamp is not JSON")
            ohc_path = (tree / Path(str(ohc.get("path"))).name if ohc.get("in_data_root_manifest")
                        else resolve_under_package(mod, computation, ohc.get("path")))
            if ohc_path is None or not ohc_path.is_file():
                problems.append(f"the Argo receipt {ohc.get('path')} is not reachable from the tree or the package")
            elif sha256_file(ohc_path) != ohc["sha256"]:
                problems.append("the Argo receipt does not hash to the receipt's digest")
            else:
                try:
                    tree_ohc = json.loads(ohc_path.read_text(encoding="utf-8"))
                except ValueError:
                    problems.append("the Argo receipt is not JSON")
                if isinstance(tree_ohc, dict) and (
                        tree_ohc.get("run_id") != ohc.get("run_id")
                        or tree_ohc.get("bound_parameters") != ohc.get("bound_parameters")
                        or tree_ohc.get("code_sha256") != ohc.get("code_sha256")
                        or tree_ohc.get("refused") != ohc.get("refused")):
                    problems.append("the Argo receipt's run id, code digest, refusal flag or bound "
                                    "parameters differ from the identity block copied into the receipt")
            csv_path = tree / "toa-net.csv"
            if csv_path.is_file() and not problems:
                tree_series = mod.read_csv_series(csv_path)
            ok = not problems
            detail += ("; verified against the tree: RECORD.json, the CSV, the stamp and the Argo "
                       "receipt hash to the receipt's digests" if ok else "; " + "; ".join(problems))
        elif ok:
            detail += "; digests well formed but NOT verified against a tree (give --data-root)"
        check("data", ok, detail)
    else:
        check("data", False, f"data mode {data.get('mode')!r} is neither fixture nor data-root")

    if refusal:
        code = r.get("reason_code")
        recognized = code in mod.REASONS
        reproduced, why = False, "reason not reproduced"
        series_for = fx["series"] if fx else tree_series
        if recognized and start and coverage and data.get("mode") == "data-root" and tree is None:
            why = ("a data-root refusal is taken on the executor's word and not reproduced: "
                   "give --data-root to reproduce it from the tree")
        elif recognized and start and coverage:
            if code == "window-outside-record":
                reproduced = not (ym(coverage[0]) <= ym(start) and ym(end) <= ym(coverage[1]))
                why = f"the window {window} leaves {coverage[0]}..{coverage[1]}: {reproduced}"
            elif code == "ohc-window-mismatch":
                reproduced = ohc_window != window
                why = f"the Argo receipt's window {ohc_window} against {window}: {reproduced}"
            elif code == "ohc-receipt-refused":
                refused_flag = (data.get("ohc_receipt") or {}).get("refused") if not fx else False
                reproduced = refused_flag is True and (tree_ohc is None or tree_ohc.get("refused") is True)
                why = f"the Argo receipt is a refusal: {reproduced}"
            elif code == "too-few-months" and series_for:
                n_cal = ym(end) - ym(start) + 1
                have = set(series_for["dates"])
                used = [label(k) for k in range(ym(start), ym(end) + 1) if label(k) in have]
                reproduced = n_cal < mod.MIN_MONTHS or len(used) < mod.MIN_MONTHS
                why = f"{len(used)} of {n_cal} months, floor {mod.MIN_MONTHS}: {reproduced}"
            elif code == "interval-not-stated" and series_for:
                ohc_in = mod.fixture_ohc_receipt(start, end) if fx else tree_ohc
                book = mod.FIXTURE_BOOKKEEPING if fx else (json.loads((tree / "RECORD.json").read_text(
                    encoding="utf-8")).get("bookkeeping") or {})
                body, again = mod.compute(series_for, ohc_in, start, end, book, "recheck")
                reproduced = body is None and again[0] == code
                why = f"the executor's compute refuses the same way: {reproduced}"
            else:
                why = "the series to reproduce the refusal from is not available"
        check("refusal", recognized and reproduced,
              f"reason_code {code!r} {'recognized' if recognized else 'unknown'}; {why}")
        verdict = "PASS" if all(c["ok"] for c in checks) else "FAIL"
        return verdict, True, checks, r

    # the Argo receipt's window is the window
    if data.get("mode") == "fixture":
        check("ohc-window", True, "the fixture plants its own Argo-shaped receipt over the bound window")
    else:
        ob = ((data.get("ohc_receipt") or {}).get("bound_parameters") or {})
        ok = ob.get("window") == window and ob.get("depth") == mod.OHC_DEPTH and window != ""
        check("ohc-window", ok, f"the Argo receipt's window {ob.get('window')} and depth {ob.get('depth')} "
                                f"against the bound window {window} and {mod.OHC_DEPTH} dbar")

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
    series_ok = (months_ok and s.get("dates") == used
                 and numbers(s.get("toa_net_coslat_W_m2"), len(used))
                 and numbers(s.get("toa_net_product_W_m2"), len(used))
                 and numbers(s.get("uncertainty_W_m2"), len(used))
                 and numbers(s.get("toa_net_anomaly_W_m2"), len(used)))
    detail = "months and series well formed" if series_ok else "months or series malformed"
    if series_ok:
        cmean = sum(s["toa_net_coslat_W_m2"]) / len(used)
        dev = max(abs(v - cmean - a) for v, a in zip(s["toa_net_coslat_W_m2"], s["toa_net_anomaly_W_m2"]))
        series_ok = dev <= 1e-9
        detail = f"anomaly is the cos-latitude series minus its mean (max deviation {dev:.2e})"
    if series_ok and fx:
        fs = fx["series"]
        by = {d: (v, u, p) for d, v, u, p in zip(fs["dates"], fs["value_W_m2"], fs["uncertainty_W_m2"],
                                                 fs["product_global_W_m2"])}
        expect_used = [d for d in cal if d in by]
        maxdev = max([abs(by[d][0] - s["toa_net_coslat_W_m2"][i]) for i, d in enumerate(used) if d in by]
                     + [abs(by[d][1] - s["uncertainty_W_m2"][i]) for i, d in enumerate(used) if d in by]
                     + [abs(by[d][2] - s["toa_net_product_W_m2"][i]) for i, d in enumerate(used) if d in by]
                     + [0.0])
        series_ok = used == expect_used and maxdev <= 1e-9
        detail += (f"; {len(used)} of {n_cal} months as the regenerated fixture yields "
                   f"(max deviation {maxdev:.2e})")
    elif series_ok and tree_series is not None:
        by = {d: (v, u, p) for d, v, u, p in zip(tree_series["dates"], tree_series["value_W_m2"],
                                                 tree_series["uncertainty_W_m2"], tree_series["product_global_W_m2"])}
        expect_used = [d for d in cal if d in by]
        maxdev = max([abs(by[d][0] - s["toa_net_coslat_W_m2"][i]) for i, d in enumerate(used) if d in by]
                     + [abs((by[d][2] or 0.0) - s["toa_net_product_W_m2"][i]) for i, d in enumerate(used) if d in by]
                     + [0.0])
        series_ok = used == expect_used and maxdev <= 1e-9
        detail += f"; the months and values are the tree's (max deviation {maxdev:.2e})"
    check("series", series_ok, detail)

    # recompute
    rec_ok, rec_detail = False, "series not checkable"
    terms = r.get("terms") or {}
    if series_ok:
        problems = []
        t_cal = [ym(d) - ym(start) for d in used]
        unc = s["uncertainty_W_m2"]
        toa = terms.get("toa_net") or {}
        cm = mean_recompute(t_cal, s["toa_net_product_W_m2"], unc)
        err = check_mean_block(toa.get("mean_block"), cm)
        if err:
            problems.append(f"toa_net.mean_block: {err}")
        else:
            sampling = max(cm["half_width"], cm["formal_95"])
            toa_unc = math.sqrt(mod.ANCHOR["uncertainty_W_m2"] ** 2 + sampling ** 2)
            offsets = [c - p for c, p in zip(s["toa_net_coslat_W_m2"], s["toa_net_product_W_m2"])]
            wo = toa.get("weighting_offset_W_m2") or {}
            if not close(toa.get("value"), cm["mean"]) or not close(toa.get("uncertainty"), toa_unc) \
                    or not close(toa.get("sampling_uncertainty_W_m2"), sampling) \
                    or toa.get("anchor_uncertainty_W_m2") != mod.ANCHOR["uncertainty_W_m2"] \
                    or not close(toa.get("coslat_window_mean_W_m2"), sum(s["toa_net_coslat_W_m2"]) / len(used)) \
                    or not close(wo.get("mean"), sum(offsets) / len(offsets)) \
                    or not close(wo.get("max_abs"), max(abs(o) for o in offsets)):
                problems.append(f"toa_net {toa.get('value')} (unc {toa.get('uncertainty')}) does not "
                                f"recompute ({cm['mean']}, {toa_unc})")
        ct = trend_recompute(t_cal, s["toa_net_anomaly_W_m2"], unc)
        an = terms.get("toa_net_anomaly_trend") or {}
        err = check_trend_block(an.get("interval"), ct)
        if err:
            problems.append(f"toa_net_anomaly_trend.interval: {err}")
        elif not ct["interval"]:
            problems.append("the anomaly trend carries no interval; a receipt with none is a refusal")
        else:
            an_unc = max(ct["half_width_per_decade"], ct["formal_95"] * 10.0)
            pub = mod.PUBLISHED_TREND
            dist = ct["trend_per_decade"] - pub["value_W_m2_per_decade"]
            if not close(an.get("value"), ct["trend_per_decade"]) or not close(an.get("uncertainty"), an_unc) \
                    or an.get("published") != pub \
                    or not close(an.get("distance_W_m2_per_decade"), dist) \
                    or not close(an.get("distance_over_published_uncertainty"), dist / pub["uncertainty_W_m2_per_decade"]):
                problems.append(f"toa_net_anomaly_trend {an.get('value')} (unc {an.get('uncertainty')}) does not "
                                f"recompute ({ct['trend_per_decade']}, {an_unc})")
        oh = terms.get("ohc_0_2000") or {}
        rate_w = mod.zj_yr_to_w_m2(oh.get("rate_ZJ_yr")) if isinstance(oh.get("rate_ZJ_yr"), (int, float)) else None
        unc_w = mod.zj_yr_to_w_m2(oh.get("uncertainty_ZJ_yr")) if isinstance(oh.get("uncertainty_ZJ_yr"), (int, float)) else None
        if rate_w is None or not close(oh.get("value"), rate_w) or not close(oh.get("uncertainty"), unc_w):
            problems.append(f"ohc_0_2000 {oh.get('value')} does not convert from {oh.get('rate_ZJ_yr')} ZJ/yr ({rate_w})")
        if tree_ohc is not None or fx is not None:
            source = tree_ohc if tree_ohc is not None else mod.fixture_ohc_receipt(start, end)
            st = ((source.get("terms") or {}).get("trend") or {})
            if not close(oh.get("rate_ZJ_yr"), st.get("value")) or not close(oh.get("uncertainty_ZJ_yr"), st.get("uncertainty")):
                problems.append("ohc_0_2000 rate is not the Argo receipt's trend term")
        deep = terms.get("deep_ocean") or {}
        if (deep.get("value") != mod.DEEP_OCEAN["value_W_m2"] or deep.get("uncertainty") != mod.DEEP_OCEAN["uncertainty_W_m2"]
                or deep.get("published") != mod.DEEP_OCEAN):
            problems.append("deep_ocean is not the sanctioned published statement")
        non = terms.get("non_ocean") or {}
        tot = mod.non_ocean_total()
        if (not close(non.get("value"), tot["value_W_m2"]) or not close(non.get("uncertainty"), tot["uncertainty_W_m2"])
                or non.get("published") != json.loads(json.dumps(mod.NON_OCEAN))):
            problems.append("non_ocean is not the sanctioned published statement")
        if not problems:
            ocean_sum = oh["value"] + deep["value"] + non["value"]
            ocean_unc = math.sqrt(oh["uncertainty"] ** 2 + deep["uncertainty"] ** 2 + non["uncertainty"] ** 2)
            residual = toa["value"] - ocean_sum
            combined = math.sqrt(toa["uncertainty"] ** 2 + oh["uncertainty"] ** 2 + deep["uncertainty"] ** 2
                                 + non["uncertainty"] ** 2)
            closed = abs(residual) <= combined
            rs, cu, vd = r.get("residual") or {}, r.get("combined_uncertainty") or {}, r.get("verdict") or {}
            if not close(rs.get("value"), residual) or not close(rs.get("ocean_side_sum"), ocean_sum) \
                    or not close(rs.get("ocean_side_uncertainty"), ocean_unc):
                problems.append(f"residual {rs.get('value')} does not recompute ({residual})")
            if not close(cu.get("value"), combined):
                problems.append(f"combined_uncertainty {cu.get('value')} does not recompute ({combined})")
            if (not close(vd.get("residual_W_m2"), residual) or not close(vd.get("bar_W_m2"), combined)
                    or vd.get("closed_within_uncertainty") is not closed):
                problems.append(f"verdict {vd.get('closed_within_uncertainty')} does not recompute (closed {closed})")
            for key, want in (("toa_net_W_m2", toa["value"]), ("ocean_side_W_m2", ocean_sum),
                              ("residual_W_m2", residual),
                              ("toa_net_anomaly_trend_W_m2_per_decade", an["value"])):
                v = r.get(key)
                if not isinstance(v, (int, float)) or abs(v - want) > ROUNDING + 1e-9:
                    problems.append(f"{key} {v} is not the term rounded ({want})")
            en = r.get("energy_over_window_ZJ") or {}
            expect = {"toa_net": toa["value"], "toa_net_uncertainty": toa["uncertainty"],
                      "ohc_0_2000": oh["value"], "ohc_0_2000_uncertainty": oh["uncertainty"],
                      "deep_ocean": deep["value"], "non_ocean": non["value"],
                      "residual": residual, "bar": combined}
            for k, rate in expect.items():
                if not close(en.get(k), mod.energy_over_window(rate, n_cal)):
                    problems.append(f"energy_over_window_ZJ.{k} does not recompute")
            if not close(en.get("window_years"), n_cal / 12.0):
                problems.append("energy_over_window_ZJ.window_years is not the window length")
            pe = r.get("published_eei") or {}
            if (pe.get("published") != mod.PUBLISHED_EEI
                    or not close(pe.get("toa_net_minus_published_W_m2"), toa["value"] - mod.PUBLISHED_EEI["value_W_m2"])
                    or not close(pe.get("ocean_side_minus_published_W_m2"), ocean_sum - mod.PUBLISHED_EEI["value_W_m2"])):
                problems.append("published_eei block does not recompute")
        rec_ok = not problems
        rec_detail = ("; ".join(problems) if problems else
                      "the window mean, the anomaly trend, the four terms, the residual, the combined "
                      "uncertainty, the verdict, the energy over the window and the published "
                      "distances recompute")
    check("recompute", rec_ok, rec_detail)

    # bookkeeping
    book = r.get("bookkeeping") or {}
    lacking = [f"{sec}.{key}" for sec, key in mod.REQUIRED_BOOKKEEPING
               if not (isinstance(book.get(sec), dict) and book[sec].get(key) not in (None, ""))]
    anch = book.get("anchoring") if isinstance(book.get("anchoring"), dict) else {}
    wh = book.get("window_handling") if isinstance(book.get("window_handling"), dict) else {}
    area = book.get("area_convention") if isinstance(book.get("area_convention"), dict) else {}
    shared = mod.overlap_months(start, end, mod.ANCHOR["period"]) if start else None
    book_ok = (not lacking and anch.get("anchor") == mod.ANCHOR
               and anch.get("months_shared_with_anchor_decade") == shared
               and anch.get("months_in_window") == n_cal
               and isinstance(anch.get("independence"), str)
               and isinstance(wh.get("rule"), str) and wh.get("months_missing") == miss
               and wh.get("whole_years") is (n_cal % 12 == 0)
               and isinstance(book.get("deep_ocean"), dict) and isinstance(book.get("non_ocean"), dict)
               and book.get("published_eei") == mod.PUBLISHED_EEI
               and close(area.get("earth_surface_area_m2"), mod.EARTH_AREA_M2))
    check("bookkeeping", book_ok,
          (f"lacks {lacking}; " if lacking else "required statements present; ")
          + f"anchor block sanctioned {anch.get('anchor') == mod.ANCHOR}; {shared} months shared with the "
            f"anchor decade; window handling lists {len(miss)} missing months; area convention "
            f"{'sanctioned' if close(area.get('earth_surface_area_m2'), mod.EARTH_AREA_M2) else 'not sanctioned'}")

    # plausibility
    if rec_ok:
        problems = []
        for name, (lo, hi) in BOUNDS.items():
            v = (terms.get(name) or {}).get("value")
            if not isinstance(v, (int, float)) or not (lo <= v <= hi):
                problems.append(f"{name} {v} outside [{lo}, {hi}] W m-2")
        tv = (terms.get("toa_net_anomaly_trend") or {}).get("value")
        if not isinstance(tv, (int, float)) or abs(tv) > TREND_BOUND_PER_DECADE:
            problems.append(f"anomaly trend {tv} beyond {TREND_BOUND_PER_DECADE} W m-2 per decade")
        u = s["uncertainty_W_m2"]
        if min(u) <= 0 or max(u) >= UNCERTAINTY_BOUND:
            problems.append(f"per-month uncertainty outside (0, {UNCERTAINTY_BOUND})")
        if fx is not None:
            kt = r.get("known_truth") or {}
            truth = mod.fixture_truth_window(start, end)
            toa_v = terms["toa_net"]["value"]
            tr_v = terms["toa_net_anomaly_trend"]["value"]
            tb = terms["toa_net_anomaly_trend"]["interval"]
            inside = tb["ci_low"] * 10.0 <= truth["trend_W_m2_per_decade"] <= tb["ci_high"] * 10.0
            if abs(toa_v - truth["geodetic_window_mean_W_m2"]) > TRUTH_MEAN_BAND:
                problems.append(f"recovered window mean {toa_v:.4f} is more than {TRUTH_MEAN_BAND} from "
                                f"the planted {truth['geodetic_window_mean_W_m2']:.4f}")
            if abs(tr_v - truth["trend_W_m2_per_decade"]) > TRUTH_TREND_BAND:
                problems.append(f"recovered trend {tr_v:.4f} is more than {TRUTH_TREND_BAND} per decade from "
                                f"the planted {truth['trend_W_m2_per_decade']}")
            if (not close(kt.get("planted_geodetic_window_mean_W_m2"), truth["geodetic_window_mean_W_m2"])
                    or not close(kt.get("recovered_toa_net_W_m2"), toa_v)
                    or kt.get("planted_trend_W_m2_per_decade") != truth["trend_W_m2_per_decade"]
                    or not close(kt.get("recovered_trend_W_m2_per_decade"), tr_v)
                    or kt.get("trend_inside_interval") is not inside
                    or not close(kt.get("planted_ohc_rate_W_m2"), truth["ohc_rate_W_m2"])
                    or kt.get("residual_within_bar") is not r["verdict"]["closed_within_uncertainty"]):
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
        "attester": "skills/energy-budget-closure/scripts/energy_budget_check.py",
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
        lines.append(f"PASS refusal ({r.get('reason_code')}) run {r.get('run_id')}: window "
                     f"{bound.get('window')} refused, {r.get('reason')}")
    else:
        v, t = r["verdict"], r["terms"]
        lines.append(f"PASS run {r.get('run_id')}: window {bound.get('window')}, "
                     f"{r['months']['n_used']} of {r['months']['n_calendar']} months, toa_net "
                     f"{t['toa_net']['value']:+.4f} against an ocean side of "
                     f"{r['residual']['ocean_side_sum']:+.4f} W m-2, residual {v['residual_W_m2']:+.4f} "
                     f"against bar {v['bar_W_m2']:.4f}, closed_within_uncertainty "
                     f"{str(v['closed_within_uncertainty']).lower()}; anomaly trend "
                     f"{t['toa_net_anomaly_trend']['value']:+.4f} W m-2 per decade (recomputed)")
    return "\n".join(lines)


# ---- selftest

def synthetic_root(mod, root: Path, start: str, end: str, seed: int = 11, smooth: bool = False):
    """A stamped data root from the fixture's own series and a planted
    Argo-shaped receipt, so the data-root path is exercised offline;
    with smooth, the cos-latitude column is a noise-free quadratic, whose
    residual autocorrelation leaves no degrees of freedom."""
    fx = mod.make_fixture(seed)
    fs = fx["series"]
    if smooth:
        n = len(fs["dates"])
        fs["value_W_m2"] = [0.5 + 1e-4 * (i - n / 2.0) ** 2 for i in range(n)]
        fs["product_global_W_m2"] = [v - 0.2 for v in fs["value_W_m2"]]
    with (root / "toa-net.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["month", "value_W_m2", "uncertainty_W_m2", "product_global_W_m2"])
        for d, v, u, p in zip(fs["dates"], fs["value_W_m2"], fs["uncertainty_W_m2"], fs["product_global_W_m2"]):
            w.writerow([d, f"{v:.9f}", f"{u:.9f}", f"{p:.9f}"])
    stamp = {"term": "toa-net", "product": "synthetic", "product_version": "selftest", "doi": "none",
             "file": "none", "months": [fs["dates"][0], fs["dates"][-1]], "n_months": len(fs["dates"]),
             "uncertainty_W_m2": fs["uncertainty_W_m2"][0], "uncertainty_basis": "planted noise"}
    (root / "toa-net-stamp.json").write_text(json.dumps(stamp, indent=2) + "\n", encoding="utf-8")
    ohc = mod.fixture_ohc_receipt(start, end)
    ohc.update({"computation": "references/computations/argo_ohc.py", "code_sha256": "sha256:" + "0" * 64,
                "run_id": "sha256:selftest", "bundle": {"name": "selftest"}, "capability": {"name": "selftest"},
                "runtime": {"name": "selftest"}, "generated_utc": "2026-01-01T00:00:00+00:00"})
    (root / "ohc-2000-receipt.json").write_text(json.dumps(ohc, indent=2) + "\n", encoding="utf-8")
    (root / "SOURCES.json").write_text("{}\n", encoding="utf-8")
    files = {n: sha256_file(root / n) for n in ("toa-net.csv", "toa-net-stamp.json", "ohc-2000-receipt.json", "SOURCES.json")}
    mh = hashlib.sha256("\n".join(f"{k} {v}" for k, v in sorted(files.items())).encode()).hexdigest()
    record = {"record": "selftest-root", "manifest": files, "manifest_sha256": "sha256:" + mh,
              "verified_utc": "2026-01-01T00:00:00Z", "terms": {"toa-net": stamp},
              "bookkeeping": {"anchoring": {"statement": "selftest"}, "weighting": {"statement": "selftest"},
                              "edition": {"statement": "selftest"}, "uncertainty": {"basis": "selftest"},
                              "ocean_input": {"statement": "selftest"}}}
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

    with tempfile.TemporaryDirectory() as d:
        w = Path(d)
        ref = w / "ref.json"
        assert run(["--fixture", "--seed", "7", "--window", "2006-01:2020-12"], ref) == 0
        assert verdict_of(ref) == ("PASS", False, []), verdict_of(ref)
        v, refusal, checks, r = attest(ref, computation)
        assert "PASS run" in report(v, refusal, checks, r)

        # tampers, each failing on its check
        t1 = tampered(ref, w / "t1.json", lambda r: r["series"]["toa_net_coslat_W_m2"].__setitem__(3, r["series"]["toa_net_coslat_W_m2"][3] + 1e-6))
        assert first_fail(t1) == "series", verdict_of(t1)
        t2 = tampered(ref, w / "t2.json", lambda r: r["terms"]["toa_net_anomaly_trend"]["interval"].__setitem__("trend", r["terms"]["toa_net_anomaly_trend"]["interval"]["trend"] * 1.001))
        assert first_fail(t2) == "recompute", verdict_of(t2)
        t3 = tampered(ref, w / "t3.json", lambda r: r["verdict"].__setitem__("closed_within_uncertainty", False))
        assert first_fail(t3) == "recompute", verdict_of(t3)
        t4 = tampered(ref, w / "t4.json", lambda r: r["terms"]["toa_net"].__setitem__("uncertainty", r["terms"]["toa_net"]["uncertainty"] / 2))
        assert first_fail(t4) == "recompute", verdict_of(t4)
        t5 = tampered(ref, w / "t5.json", lambda r: r["terms"]["deep_ocean"].__setitem__("value", 0.0))
        assert first_fail(t5) == "recompute", verdict_of(t5)
        t6 = tampered(ref, w / "t6.json", lambda r: r["bookkeeping"]["anchoring"].pop("statement"))
        assert verdict_of(t6)[2] == ["bookkeeping"], verdict_of(t6)
        t7 = tampered(ref, w / "t7.json", lambda r: r["runtime"].__setitem__("name", ""))
        assert verdict_of(t7)[2] == ["runtime"], verdict_of(t7)
        t8 = tampered(ref, w / "t8.json", lambda r: r["data"].__setitem__("seed", 8))
        assert first_fail(t8) == "data", verdict_of(t8)
        t9 = tampered(ref, w / "t9.json", lambda r: r["known_truth"].__setitem__("trend_inside_interval", not r["known_truth"]["trend_inside_interval"]))
        assert verdict_of(t9)[2] == ["plausible"], verdict_of(t9)

        # wrong release: the bundle block names another version, or the capability block is malformed
        w1 = tampered(ref, w / "w1.json", lambda r: r["bundle"].__setitem__("version", "0.0.0"))
        assert verdict_of(w1)[2] == ["release"], verdict_of(w1)
        w2 = tampered(ref, w / "w2.json", lambda r: r["capability"].__setitem__("name", ""))
        assert verdict_of(w2)[2] == ["release"], verdict_of(w2)

        # a tampered computation fails code and the generator digest
        bad = w / "energy_budget.py"
        bad.write_bytes(computation.read_bytes() + b"\n")
        v, _, failed = verdict_of(ref, bad)
        assert v == "FAIL" and "code" in failed and "data" in failed, failed

        # refusals attest PASS as refusals, exit 3 from the executor
        rf = w / "outside.json"
        assert run(["--fixture", "--seed", "7", "--window", "1998-01:2005-12"], rf) == 3
        v, refusal, checks, r = attest(rf, computation)
        assert (v, refusal) == ("PASS", True) and r["reason_code"] == "window-outside-record", checks
        assert "PASS refusal" in report(v, refusal, checks, r)
        few = w / "few.json"
        assert run(["--fixture", "--seed", "7", "--window", "2020-01:2020-12"], few) == 3
        assert verdict_of(few) == ("PASS", True, []), verdict_of(few)
        forged = tampered(rf, w / "forged.json", lambda r: r["bound_parameters"].__setitem__("window", "2006-01:2020-12"))
        assert verdict_of(forged)[2] == ["refusal"], verdict_of(forged)

        # a data root: the receipt verifies against the tree, and a fabricated tree fails
        (w / "root").mkdir()
        root = synthetic_root(mod, w / "root", "2006-01", "2020-12")
        dr = w / "dr.json"
        assert run(["--data-root", str(root), "--window", "2006-01:2020-12"], dr) == 0
        v, _, checks, r = attest(dr, computation, root)
        assert v == "PASS" and "verified against the tree" in checks[4]["detail"], checks
        v, _, checks, _ = attest(dr, computation)
        assert v == "PASS" and "NOT verified" in checks[4]["detail"], checks
        assert r["terms"]["ohc_0_2000"]["stamp"].startswith("argo receipt")
        fab = tampered(dr, w / "fab.json", lambda r: r["data"]["files"].__setitem__("toa-net.csv", "sha256:" + "1" * 64))
        assert first_fail(fab, None, root) == "data", verdict_of(fab, None, root)
        # the pass path enforces the window rule: a relabelled identity block fails ohc-window
        # without the tree, and a swapped identity block fails data against the tree
        rl = tampered(dr, w / "relabel.json", lambda r: r["data"]["ohc_receipt"]["bound_parameters"].__setitem__("window", "2008-01:2018-12"))
        assert first_fail(rl) == "ohc-window", verdict_of(rl)
        assert "ohc-window" in verdict_of(rl, None, root)[2], verdict_of(rl, None, root)
        sw = tampered(dr, w / "swap.json", lambda r: r["data"]["ohc_receipt"].__setitem__("run_id", "sha256:other"))
        assert first_fail(sw, None, root) == "data", verdict_of(sw, None, root)
        # the window mismatch refusal reproduces only against the tree
        mm = w / "mismatch.json"
        assert run(["--data-root", str(root), "--window", "2008-01:2018-12"], mm) == 3
        assert verdict_of(mm, None, root) == ("PASS", True, []), verdict_of(mm, None, root)
        assert verdict_of(mm)[2] == ["refusal"], verdict_of(mm)
        # a refused Argo receipt refuses the budget
        ohc_path = root / "ohc-2000-receipt.json"
        doc = json.loads(ohc_path.read_text(encoding="utf-8"))
        doc.update({"refused": True, "reason_code": "too-few-months", "reason": "selftest"})
        refused_ohc = w / "refused-ohc.json"
        refused_ohc.write_text(json.dumps(doc) + "\n", encoding="utf-8")
        rr = w / "rr.json"
        assert run(["--data-root", str(root), "--ohc-receipt", str(refused_ohc), "--window", "2006-01:2020-12"], rr) == 3
        assert json.loads(rr.read_text())["reason_code"] == "ohc-receipt-refused"
        assert verdict_of(rr, None, root) == ("PASS", True, []), verdict_of(rr, None, root)
        assert verdict_of(rr)[2] == ["refusal"], verdict_of(rr)
        # a smooth series leaves no degrees of freedom: interval-not-stated, reproduced against the tree
        (w / "smooth").mkdir()
        smooth = synthetic_root(mod, w / "smooth", "2006-01", "2020-12", smooth=True)
        ins = w / "ins.json"
        assert run(["--data-root", str(smooth), "--window", "2006-01:2020-12"], ins) == 3
        assert json.loads(ins.read_text())["reason_code"] == "interval-not-stated"
        v, refusal, checks, r = attest(ins, computation, smooth)
        assert (v, refusal) == ("PASS", True) and "PASS refusal" in report(v, refusal, checks, r), checks
        assert verdict_of(ins)[2] == ["refusal"], verdict_of(ins)

        # the attestation document carries the verdict and the identity blocks
        doc = attestation_doc(*attest(ref, computation), ref, computation)
        assert doc["verdict"] == "PASS" and doc["capability"]["name"] and doc["runtime"]["name"] == "selftest"
        assert {c["name"] for c in doc["checks"]} == {"fields", "code", "release", "runtime", "data",
                                                       "ohc-window", "series", "recompute", "bookkeeping",
                                                       "plausible"}
    print("energy_budget_check selftest: ok")
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
