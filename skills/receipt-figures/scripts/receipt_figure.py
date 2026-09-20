#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib"]
# ///
"""Draw a figure from an attested receipt, and from nothing else.

This is the atmospheric-physics port of the ocean-science receipt-figures
renderer, with its discipline intact and its modes changed to what these
receipts carry. It computes nothing: every point plotted is a value the
receipt carries, and every line annotated with a number is annotated
with the receipt's own field. It draws no trend it fitted, no mean it
took and no difference of two receipts.

Three modes, each of which first runs the receipt's attester and stops
on anything but PASS, so a figure exists only for a receipt that
attests:

  budget        The monthly net top-of-atmosphere flux an energy budget
                receipt carries (series.toa_net_product_W_m2, the
                product's own geodetic global mean, the series the
                anchor is defined on) against the ocean side the same
                receipt read from the Argo receipt: the window mean of
                the radiation term, the ocean side sum and its
                uncertainty band, and the verdict.

  cre-series    The all-sky and the clear-sky series a cloud radiative
                effect receipt carries in one band (net, shortwave or
                longwave), with the effect series the receipt carries
                below them and the window mean term drawn across it.
                The caption and the legend name the bound convention.

  contrast      The three terms of a cloud radiative effect receipt
                under the bound convention against the same three under
                the other convention, from the receipt's own
                convention_contrast block. Six numbers, each a receipt
                field, and no seventh: the receipt carries no difference
                between the two conventions, so none is drawn or
                printed, and the two bars of each pair are the gap. The
                picture is the size of the incomparability between the
                two conventions, never a conversion.

What it refuses, each with exit 4 and a reason code, and never a
partial figure:

  attester-did-not-pass    the attester did not PASS this receipt. A
                           data-root receipt is attested with
                           --data-root DIR, without which the
                           attesters take the data digests on the
                           executor's word.
  refused-receipt          a refusal receipt. It carries a reason code
                           and no series, and a refusal is never a
                           picture.
  receipt-not-for-this-mode  a receipt of the other computation, or one
                           missing the block the mode draws.
  array-not-in-receipt     an array the receipt does not carry, or one
                           whose length is not the months the receipt
                           says it used.
  array-hash-mismatch      an array whose sha256 differs from the one
                           --expect NAME=SHA256 states. Every drawn
                           array's length and digest are printed and the
                           digest goes in the caption, so a figure can be
                           redrawn from the same receipt and proven to be
                           of the same arrays. The digest is of the values
                           the receipt stores, so it is stable for a given
                           receipt; a receipt regenerated from a fixture
                           under another interpreter can carry different
                           last bits, and the digest is not a claim about
                           that.
  receipt-changed-under-attestation  the receipt file's bytes changed
                           between the attestation and the draw.
  map-mode-unavailable     a map. These receipts carry regional and
                           global means and no per-cell field, so there
                           is nothing to put on a grid; the mode exists
                           only to refuse, by name, rather than to be
                           improvised.

The attester is named by --attester: a path, or a bare name resolved
in the scripts of the skill that runs the computation, under
`${CLAUDE_PLUGIN_ROOT}`.

Usage:
  uv run skills/receipt-figures/scripts/receipt_figure.py budget RECEIPT.json \
      --attester energy_budget_check --out budget.png
  uv run skills/receipt-figures/scripts/receipt_figure.py cre-series RECEIPT.json \
      --attester cloud_radiative_effect_check --band net --out cre_net.png
  uv run skills/receipt-figures/scripts/receipt_figure.py contrast RECEIPT.json \
      --attester cloud_radiative_effect_check --out contrast.png
  uv run skills/receipt-figures/scripts/receipt_figure.py --selftest
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

BUNDLE = "asdc"
REFUSALS = ("attester-did-not-pass", "refused-receipt",
            "receipt-not-for-this-mode", "array-not-in-receipt",
            "array-hash-mismatch", "receipt-changed-under-attestation",
            "map-mode-unavailable")
BANDS = {
    "net": ("net_all_W_m2", "net_clr_W_m2", "cre_net_W_m2", "cre_net",
            "net downward flux, positive down"),
    "shortwave": ("sw_all_W_m2", "sw_clr_W_m2", "cre_shortwave_W_m2",
                  "cre_shortwave", "outgoing shortwave flux"),
    "longwave": ("lw_all_W_m2", "lw_clr_W_m2", "cre_longwave_W_m2",
                 "cre_longwave", "outgoing longwave flux"),
}


class Refused(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def refuse(code: str, message: str):
    raise Refused(code, message)


# ---- the installed bundle

def package_root() -> Path:
    """This package's root: `${CLAUDE_PLUGIN_ROOT}` where the runtime
    sets it, else the package tree this script ships in. The executor,
    the attester and the concept are files of this package now, so
    nothing is resolved through an installed provider bundle."""
    override = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if override:
        root = Path(override).expanduser().resolve()
        if not (root / ".osp" / "package.yaml").is_file():
            sys.exit(f"CLAUDE_PLUGIN_ROOT={root} is no package tree: it "
                     "carries no .osp/package.yaml")
        return root
    here = Path(__file__).resolve().parent
    for p in (here, *here.parents):
        if (p / ".osp" / "package.yaml").is_file():
            return p
    sys.exit("no CLAUDE_PLUGIN_ROOT in the environment and no package "
             f"tree above {here}; run this script from its plugin")


def resolve_attester(name: str) -> Path:
    p = Path(name).expanduser()
    if p.is_file():
        return p.resolve()
    stem = name if name.endswith(".py") else name + ".py"
    hits = sorted(package_root().glob(f"skills/*/scripts/{stem}"))
    if len(hits) != 1:
        sys.exit(f"attester {name} not found in this package's skills: "
                 f"{[str(h) for h in hits] or 'no match'}")
    return hits[0]


def attest(receipt_path: Path, attester: Path, data_root=None) -> str:
    """The attester on this receipt, before anything is drawn from it.

    Returns its PASS line, or refuses. The receipt file is hashed on
    either side of the attestation, so what is drawn is the bytes the
    attester read."""
    before = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    cmd = ["uv", "run", str(attester), str(receipt_path)]
    if data_root is not None:
        cmd += ["--data-root", str(data_root)]
    run = subprocess.run(cmd, capture_output=True, text=True)
    text = (run.stdout or "").strip() or (run.stderr or "").strip()
    lines = [line for line in text.splitlines() if line.strip()]
    line = lines[-1] if lines else "the attester printed nothing"
    if run.returncode != 0 or not line.startswith("PASS"):
        refuse("attester-did-not-pass",
               f"{attester.name} did not PASS this receipt, so there is "
               f"nothing licensed to draw. Its last line: {line}. Report the "
               "attestation; do not draw around it.")
    after = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    if before != after:
        refuse("receipt-changed-under-attestation",
               f"{receipt_path} hashed {before[:12]} before the attestation "
               f"and {after[:12]} after it; the figure would be of bytes the "
               "attester did not read")
    return line, after


# ---- the arrays drawn

def digest(values) -> str:
    """The sha256 of one drawn array, over its canonical JSON bytes. It
    is printed, written into the caption, and checked against --expect
    where one is stated, so a redrawn figure is provably of the same
    array."""
    blob = json.dumps(values, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class Arrays:
    """Every array a figure draws, taken from the attested receipt,
    checked against the receipt's own month bookkeeping and hashed."""

    def __init__(self, receipt: dict, expect: dict):
        self.receipt = receipt
        self.expect = expect
        self.digests = {}
        self.lengths = {}
        self.n_used = ((receipt.get("months") or {}).get("n_used"))

    def series(self, name: str):
        block = self.receipt.get("series")
        if not isinstance(block, dict) or name not in block:
            carried = ", ".join(sorted(block)) if isinstance(block, dict) else "none"
            refuse("array-not-in-receipt",
                   f"the receipt carries no series {name}; it carries "
                   f"{carried}. A figure draws what the receipt carries and "
                   "nothing loaded from beside it.")
        values = block[name]
        if not isinstance(values, list) or not values:
            refuse("array-not-in-receipt",
                   f"series {name} is not a list of values in this receipt")
        if self.n_used is not None and len(values) != self.n_used:
            refuse("array-not-in-receipt",
                   f"series {name} has {len(values)} values and the receipt "
                   f"says it used {self.n_used} months; the array and the "
                   "receipt's own bookkeeping do not agree")
        return self.checked(name, values)

    def vector(self, name: str, values):
        return self.checked(name, values)

    def checked(self, name: str, values):
        got = digest(values)
        self.digests[name] = got
        self.lengths[name] = len(values)
        want = self.expect.get(name)
        if want is not None and want != got:
            refuse("array-hash-mismatch",
                   f"array {name} hashes {got} and --expect states {want}; "
                   "the figure would be of a different array than the one "
                   "that digest was taken on")
        return values

    def caption_digests(self) -> str:
        return ", ".join(f"{name} {value[:12]}"
                         for name, value in sorted(self.digests.items()))


def field(receipt: dict, path: str):
    node = receipt
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def need(receipt: dict, path: str, mode: str):
    value = field(receipt, path)
    if value is None:
        refuse("receipt-not-for-this-mode",
               f"{mode} mode reads {path} and this receipt does not carry it; "
               f"it is a receipt of {receipt.get('computation')}")
    return value


def guard(receipt: dict, computation_tail: str, mode: str) -> None:
    if receipt.get("refused"):
        refuse("refused-receipt",
               f"this receipt is a refusal ({receipt.get('reason_code')}): "
               f"{receipt.get('reason')}. It carries a reason code and no "
               "series, and a refusal is reported in the executor's words, "
               "never drawn.")
    got = str(receipt.get("computation") or "")
    if not got.endswith(computation_tail):
        refuse("receipt-not-for-this-mode",
               f"{mode} mode reads a receipt of {computation_tail} and this "
               f"one is of {got or 'an unnamed computation'}")


# ---- the caption

def caption(receipt: dict, verdict: str, attester: Path, receipt_sha: str,
            arrays: Arrays) -> str:
    bits = [f"receipt run {receipt['run_id']}",
            f"code sha256 {receipt['code_sha256'][12:24]}",
            f"receipt sha256 {receipt_sha[:12]}"]
    data = receipt.get("data") or {}
    if data.get("mode") == "data-root":
        bits.append(f"data {data.get('record')} manifest "
                    f"{str(data.get('manifest_sha256'))[7:19]}")
    else:
        bits.append(f"fixture seed {data.get('seed')} digest "
                    f"{str(data.get('digest'))[7:19]}")
    bits.append(f"arrays {arrays.caption_digests()}")
    bits.append(f"{attester.name} {verdict.split()[0]}")
    return " . ".join(bits)


def dates_of(labels):
    return [dt.date(int(m[:4]), int(m[5:7]), 15) for m in labels]


def stamp(fig, text: str) -> None:
    fig.text(0.01, 0.01, textwrap.fill(text, 160), fontsize=6.5,
             family="monospace", alpha=0.85)


# ---- the modes

def draw_budget(args, receipt, verdict, attester, receipt_sha, arrays) -> int:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    guard(receipt, "energy_budget.py", "budget")
    labels = arrays.series("dates")
    flux = arrays.series("toa_net_product_W_m2")
    dates = dates_of(labels)

    toa = need(receipt, "terms.toa_net.value", "budget")
    toa_unc = need(receipt, "terms.toa_net.uncertainty", "budget")
    ocean = need(receipt, "residual.ocean_side_sum", "budget")
    ocean_unc = need(receipt, "residual.ocean_side_uncertainty", "budget")
    resid = need(receipt, "verdict.residual_W_m2", "budget")
    bar = need(receipt, "verdict.bar_W_m2", "budget")
    closed = need(receipt, "verdict.closed_within_uncertainty", "budget")
    window = need(receipt, "bound_parameters.window", "budget")
    shared = field(receipt, "bookkeeping.anchoring.months_shared_with_anchor_decade")

    fig, ax = plt.subplots(figsize=(11, 5.4), dpi=args.dpi)
    ax.plot(dates, flux, color="#1f4e79", linewidth=1.0,
            label="monthly net TOA flux, the product's geodetic global mean "
                  "(series.toa_net_product_W_m2)")
    ax.axhline(toa, color="#1f4e79", linewidth=1.6, linestyle="--",
               label=f"toa_net window mean {toa:+.4f} +/- {toa_unc:.4f} W m-2")
    ax.fill_between([dates[0], dates[-1]], ocean - ocean_unc, ocean + ocean_unc,
                    color="#c9a227", alpha=0.30, linewidth=0,
                    label=f"ocean side {ocean:+.4f} +/- {ocean_unc:.4f} W m-2 "
                          "(Argo receipt plus the published deep ocean and "
                          "non-ocean rates)")
    ax.axhline(ocean, color="#8a6d1f", linewidth=1.4)
    ax.axhline(0, color="k", linewidth=0.4)
    ax.set_ylabel("W m-2 of the Earth's surface")
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.grid(True, linewidth=0.3, alpha=0.5)
    title = (f"energy budget closure, {window}, {len(flux)} months: residual "
             f"{resid:+.4f} against a bar of {bar:.4f} W m-2, "
             f"closed_within_uncertainty {'true' if closed else 'false'}")
    if shared is not None:
        title += f"; {shared} months shared with the anchor decade"
    ax.set_title(textwrap.fill(title, 96), fontsize=9.5)
    ax.legend(loc="upper left", fontsize=7.5, frameon=False)
    cap = caption(receipt, verdict, attester, receipt_sha, arrays)
    stamp(fig, cap)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    return finish(fig, args, cap, arrays,
                  f"energy budget {window}: toa_net {toa:+.4f}, ocean side "
                  f"{ocean:+.4f}, residual {resid:+.4f} against {bar:.4f} W m-2")


def draw_cre_series(args, receipt, verdict, attester, receipt_sha, arrays) -> int:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    guard(receipt, "cloud_radiative_effect.py", "cre-series")
    all_key, clr_key, cre_key, term, what = BANDS[args.band]
    labels = arrays.series("dates")
    all_sky = arrays.series(all_key)
    clear = arrays.series(clr_key)
    effect = arrays.series(cre_key)
    dates = dates_of(labels)

    value = need(receipt, f"terms.{term}.value", "cre-series")
    unc = need(receipt, f"terms.{term}.uncertainty", "cre-series")
    rule = need(receipt, f"terms.{term}.rule", "cre-series")
    window = need(receipt, "bound_parameters.window", "cre-series")
    region = need(receipt, "bound_parameters.region", "cre-series")
    convention = need(receipt, "bound_parameters.clear_sky", "cre-series")
    suffix = field(receipt, "bookkeeping.convention.variable_suffix")

    fig, (top, bottom) = plt.subplots(2, 1, figsize=(11, 7.0), dpi=args.dpi,
                                      sharex=True,
                                      gridspec_kw={"height_ratios": [3, 2]})
    top.plot(dates, all_sky, color="#1f4e79", linewidth=1.0,
             label=f"all-sky {what} (series.{all_key})")
    top.plot(dates, clear, color="#b2411c", linewidth=1.0,
             label=f"clear-sky {what}, convention {convention}"
                   + (f" ({suffix})" if suffix else "")
                   + f" (series.{clr_key})")
    top.set_ylabel("W m-2 of the region")
    top.grid(True, linewidth=0.3, alpha=0.5)
    top.legend(loc="upper left", fontsize=7.5, frameon=False)
    top.set_title(textwrap.fill(
        f"{args.band} cloud radiative effect, region {region}, {window}, "
        f"{len(effect)} months, clear-sky convention {convention}", 96),
        fontsize=9.5)

    bottom.plot(dates, effect, color="#3f6f3f", linewidth=1.0,
                label=textwrap.fill(
                    f"the effect the receipt carries (series.{cre_key}): "
                    f"{rule}", 88))
    bottom.axhline(value, color="#3f6f3f", linewidth=1.6, linestyle="--",
                   label=f"{term} window mean {value:+.4f} +/- {unc:.4f} W m-2")
    bottom.axhline(0, color="k", linewidth=0.4)
    bottom.set_ylabel("W m-2 of the region")
    bottom.xaxis.set_major_locator(mdates.YearLocator(2))
    bottom.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    bottom.grid(True, linewidth=0.3, alpha=0.5)
    bottom.legend(loc="upper left", fontsize=7.5, frameon=False)
    cap = caption(receipt, verdict, attester, receipt_sha, arrays)
    stamp(fig, cap)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    return finish(fig, args, cap, arrays,
                  f"{args.band} effect, {region}, {window}, convention "
                  f"{convention}: {term} {value:+.4f} +/- {unc:.4f} W m-2")


def draw_contrast(args, receipt, verdict, attester, receipt_sha, arrays) -> int:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    guard(receipt, "cloud_radiative_effect.py", "contrast")
    bound = need(receipt, "bound_parameters.clear_sky", "contrast")
    other = need(receipt, "convention_contrast.convention", "contrast")
    window = need(receipt, "bound_parameters.window", "contrast")
    region = need(receipt, "bound_parameters.region", "contrast")
    names = ("cre_shortwave", "cre_longwave", "cre_net")
    here = [need(receipt, f"terms.{n}.value", "contrast") for n in names]
    unc = [need(receipt, f"terms.{n}.uncertainty", "contrast") for n in names]
    there = [need(receipt, f"convention_contrast.{n}", "contrast") for n in names]
    arrays.vector("terms_bound_convention", here)
    arrays.vector("terms_other_convention", there)
    # No difference is formed here. The receipt's convention_contrast
    # block carries the other convention's three terms and no difference
    # field, so a difference drawn on these axes would be a number this
    # skill computed. The two bars of each pair are the gap.

    fig, ax = plt.subplots(figsize=(11, 5.2), dpi=args.dpi)
    positions = list(range(len(names)))
    ax.barh([p + 0.19 for p in positions], here, height=0.36, xerr=unc,
            color="#1f4e79", error_kw={"elinewidth": 1.0, "ecolor": "#0d2c47"},
            label=f"bound convention {bound} (terms)")
    ax.barh([p - 0.19 for p in positions], there, height=0.36,
            color="#b2411c",
            label=f"other convention {other} (convention_contrast)")
    span = max(abs(v) for v in here + there) or 1.0
    ax.set_xlim(-1.2 * span, 1.2 * span)
    ax.set_yticks(positions)
    ax.set_yticklabels([n.replace("cre_", "") for n in names])
    ax.axvline(0, color="k", linewidth=0.5)
    ax.set_xlabel("W m-2 of the region")
    ax.grid(True, axis="x", linewidth=0.3, alpha=0.5)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2,
              fontsize=8, frameon=False)
    ax.set_title(textwrap.fill(
        f"the two clear-sky conventions over the same months, region "
        f"{region}, {window}: the size of the incomparability, not a "
        f"conversion", 96), fontsize=9.5)
    cap = caption(receipt, verdict, attester, receipt_sha, arrays)
    stamp(fig, cap)
    fig.tight_layout(rect=(0, 0.10, 1, 1))
    return finish(fig, args, cap, arrays,
                  f"contrast, {region}, {window}: net {here[2]:+.4f} W m-2 on "
                  f"{bound} against {there[2]:+.4f} on {other}")


def draw_map(args, *rest) -> int:
    refuse("map-mode-unavailable",
           "these receipts carry regional and global window means and monthly "
           "regional series, and no per-cell field: there is no array on a "
           "grid to draw, and the computations write none. A map of a cloud "
           "radiative effect or of a net flux would have to be loaded from "
           "beside the receipt and would be a picture no receipt licenses. "
           "Report the table or the series instead, or ask the provider "
           "bundle for a computation that writes per-cell fields.")


def finish(fig, args, cap: str, arrays: Arrays, line: str) -> int:
    out = Path(args.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out)
    print(f"{out}: {line}")
    for name, value in sorted(arrays.digests.items()):
        print(f"  array {name} n={arrays.lengths[name]} sha256 {value}")
    print(f"  {cap}")
    return 0


MODES = {"budget": draw_budget, "cre-series": draw_cre_series,
         "contrast": draw_contrast, "map": draw_map}


def render(args) -> int:
    if args.mode == "map":
        return draw_map(args)
    receipt_path = Path(args.receipt).expanduser().resolve()
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    attester = resolve_attester(args.attester)
    verdict, receipt_sha = attest(receipt_path, attester, args.data_root)
    expect = {}
    for item in args.expect:
        if "=" not in item:
            sys.exit(f"--expect takes NAME=SHA256; got {item}")
        name, want = item.split("=", 1)
        expect[name] = want
    arrays = Arrays(receipt, expect)
    return MODES[args.mode](args, receipt, verdict, attester, receipt_sha, arrays)


# ---- selftest

def selftest() -> int:
    """Every mode and every refusal, on the executors' fixtures."""
    root = package_root()
    cre = root / "skills" / "cloud-radiative-effect" / "scripts"
    eb = root / "skills" / "energy-budget-closure" / "scripts"
    cre_exec = cre / "cloud_radiative_effect.py"
    eb_exec = eb / "energy_budget.py"
    cre_att = cre / "cloud_radiative_effect_check.py"
    eb_att = eb / "energy_budget_check.py"
    me = str(Path(__file__).resolve())

    def figure(argv):
        return subprocess.run([sys.executable, me, *argv],
                              capture_output=True, text=True)

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        cre = work / "cre.json"
        eb = work / "eb.json"
        refusal = work / "refusal.json"
        run = subprocess.run(
            ["uv", "run", str(cre_exec), "--fixture", "--seed", "7",
             "--window", "2006-01:2020-12", "--region", "antarctic",
             "--clear-sky", "total-region", "--runtime", "selftest",
             "--receipt", str(cre)], capture_output=True, text=True)
        assert run.returncode == 0, run.stdout + run.stderr
        run = subprocess.run(
            ["uv", "run", str(eb_exec), "--fixture", "--seed", "7",
             "--window", "2006-01:2020-12", "--runtime", "selftest",
             "--receipt", str(eb)], capture_output=True, text=True)
        assert run.returncode == 0, run.stdout + run.stderr
        run = subprocess.run(
            ["uv", "run", str(cre_exec), "--fixture", "--seed", "7",
             "--window", "2006-01:2020-12", "--region", "global",
             "--clear-sky", "pristine", "--runtime", "selftest",
             "--receipt", str(refusal)], capture_output=True, text=True)
        assert run.returncode == 3, run.stdout + run.stderr

        # 1. The three modes draw, and each names its arrays' digests.
        out = figure(["budget", str(eb), "--attester", str(eb_att),
                      "--out", str(work / "budget.png")])
        assert out.returncode == 0, out.stdout + out.stderr
        assert (work / "budget.png").is_file()
        assert "array toa_net_product_W_m2 n=180 sha256" in out.stdout, out.stdout
        assert "energy_budget_check.py PASS" in out.stdout
        out = figure(["cre-series", str(cre), "--attester", str(cre_att),
                      "--band", "net", "--out", str(work / "cre.png")])
        assert out.returncode == 0, out.stdout + out.stderr
        assert (work / "cre.png").is_file()
        assert "array cre_net_W_m2 n=180 sha256" in out.stdout, out.stdout
        out = figure(["contrast", str(cre), "--attester", str(cre_att),
                      "--out", str(work / "contrast.png")])
        assert out.returncode == 0, out.stdout + out.stderr
        assert (work / "contrast.png").is_file()
        assert "array terms_other_convention n=3 sha256" in out.stdout, out.stdout

        # 2. An array's digest, restated, draws again; a wrong one is a
        #    refusal rather than a figure.
        line = [ln for ln in out.stdout.splitlines()
                if "array terms_bound_convention n=3 sha256" in ln][0]
        good = line.strip().split()[-1]
        again = figure(["contrast", str(cre), "--attester", str(cre_att),
                        "--expect", f"terms_bound_convention={good}",
                        "--out", str(work / "contrast2.png")])
        assert again.returncode == 0, again.stdout + again.stderr
        bad = figure(["contrast", str(cre), "--attester", str(cre_att),
                      "--expect", "terms_bound_convention=" + "0" * 64,
                      "--out", str(work / "nope.png")])
        assert bad.returncode == 4 and "array-hash-mismatch" in bad.stdout, bad.stdout
        assert not (work / "nope.png").is_file()

        # 3. A receipt the attester does not pass is never drawn.
        tampered = work / "tampered.json"
        doctored = json.loads(cre.read_text())
        doctored["cre_net_W_m2"] = doctored["cre_net_W_m2"] + 0.5
        tampered.write_text(json.dumps(doctored, indent=2) + "\n")
        out = figure(["cre-series", str(tampered), "--attester", str(cre_att),
                      "--band", "net", "--out", str(work / "tampered.png")])
        assert out.returncode == 4 and "attester-did-not-pass" in out.stdout, out.stdout
        assert not (work / "tampered.png").is_file()

        # 4. A refusal receipt attests as a refusal and is still not a
        #    picture.
        out = figure(["cre-series", str(refusal), "--attester", str(cre_att),
                      "--band", "net", "--out", str(work / "refusal.png")])
        assert out.returncode == 4 and "refused-receipt" in out.stdout, out.stdout
        assert "clear-sky-convention-not-carried" in out.stdout
        assert not (work / "refusal.png").is_file()

        # 5. A receipt of the other computation, and an array the
        #    receipt does not carry.
        out = figure(["budget", str(cre), "--attester", str(cre_att),
                      "--out", str(work / "wrong.png")])
        assert out.returncode == 4 and "receipt-not-for-this-mode" in out.stdout, out.stdout
        short = work / "short.json"
        clipped = json.loads(cre.read_text())
        clipped["series"]["cre_net_W_m2"] = clipped["series"]["cre_net_W_m2"][:10]
        short.write_text(json.dumps(clipped, indent=2) + "\n")
        out = figure(["cre-series", str(short), "--attester", str(cre_att),
                      "--band", "net", "--out", str(work / "short.png")])
        # the attester catches the clipped series first, which is the
        # stronger of the two gates; either refusal leaves no figure
        assert out.returncode == 4, out.stdout
        assert not (work / "short.png").is_file()
        arrays = Arrays(json.loads(cre.read_text()), {})
        for name, body in (("w_ekman", json.loads(cre.read_text())),
                           ("cre_net_W_m2", json.loads(short.read_text()))):
            try:
                Arrays(body, {}).series(name)
            except Refused as bad_array:
                assert bad_array.code == "array-not-in-receipt", bad_array.code
            else:
                raise AssertionError(f"array {name} drew and should not have")

        # 6. A receipt whose bytes change under the attestation is
        #    refused: what would be drawn is not what was attested.
        meddler = work / "meddling_attester.py"
        meddler.write_text(
            "import json, sys\n"
            "path = sys.argv[1]\n"
            "body = json.loads(open(path).read())\n"
            "body['cre_net_W_m2'] = body['cre_net_W_m2'] + 0.5\n"
            "open(path, 'w').write(json.dumps(body, indent=2) + '\\n')\n"
            "print('PASS run meddled')\n")
        moving = work / "moving.json"
        moving.write_text(cre.read_text())
        try:
            attest(moving, meddler)
        except Refused as changed:
            assert changed.code == "receipt-changed-under-attestation", changed.code
        else:
            raise AssertionError("a receipt that changed under the attestation "
                                 "was accepted")

        # 7. A map is refused by name, because these receipts carry no
        #    per-cell field.
        out = figure(["map", str(cre), "--attester", str(cre_att),
                      "--out", str(work / "map.png")])
        assert out.returncode == 4 and "map-mode-unavailable" in out.stdout, out.stdout
        assert not (work / "map.png").is_file()

    print("receipt-figures selftest: ok "
          f"(3 modes drawn from attested fixture receipts; {len(REFUSALS)} "
          f"refusals enforced: {', '.join(REFUSALS)})")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", nargs="?", choices=sorted(MODES),
                    help="budget, cre-series, contrast, or map (always refused)")
    ap.add_argument("receipt", nargs="?", help="the receipt to draw from")
    ap.add_argument("--attester", help="attester path, or a bare name under the "
                                       "provider's references/attesters")
    ap.add_argument("--data-root", default=None,
                    help="the stamped tree, for a data-root receipt; without it "
                         "the attester takes the data digests on the executor's "
                         "word")
    ap.add_argument("--band", choices=sorted(BANDS), default="net",
                    help="which band cre-series draws (default net)")
    ap.add_argument("--expect", action="append", default=[],
                    help="NAME=SHA256 for a drawn array; a mismatch is refused")
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--out", help="where the figure is written")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    missing = [name for name in ("mode", "receipt", "out")
               if getattr(args, name) is None]
    if args.mode == "map":
        missing = [name for name in missing if name != "receipt"]
    if missing:
        ap.error("these are required to draw: " + ", ".join(missing))
    if args.mode != "map" and not args.attester:
        ap.error("--attester is required: the attester runs before anything "
                 "is drawn")
    try:
        return render(args)
    except Refused as refused:
        print(f"FIGURE REFUSED ({refused.code}): {refused.message}")
        return 4


if __name__ == "__main__":
    sys.exit(main())
