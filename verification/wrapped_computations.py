#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Golden and PROVE wrapper for this capability's wrapping skills: the
sanctioned executors and attesters of the ASDC bundle, run on the
bundle's synthetic fixtures, so every chain a skill here wraps is
proven headless with no data download and no NASA host reachable.

Nothing scientific is reimplemented. The computations live in the
provider bundle under knowledge/asdc/references/, under the contracts
knowledge/asdc/computations/energy-budget.md and
knowledge/asdc/computations/cloud-radiative-effect.md; the expected
values are quoted from those concepts' reference runs and committed
beside this file under fixtures/ (provenance in the README there).
The bundle root is resolved the way the skills resolve it:
NASA_DAAC_KNOWLEDGE names a checkout of the provider repository, else
the installer's record (`claude plugin list --json`, the entry's
installPath) names the installed plugin.

For each chain, and in the order a skill follows: run the executor on
the fixture with every declared parameter bound and the runtime named;
attest the receipt and require PASS; only then read the receipt and
compare it with what the concept records; then run the chain's refusal
case and require exit 3 and an attestation that passes it as a
refusal.

Three modes:

  (no flags)                 the golden: both chains, both refusals.
                             Exit 0 only when all of it holds.
  --runtime NAME --out R     the PROVE step: run the energy budget
                             chain's fixture computation and write the
                             receipt at R, the capability block naming
                             this package and the bundle block naming
                             the provider bundle.
  --attest R --out A         run the matching bundle attester on receipt
                             R and write the attestation at A. Exit 0 on
                             PASS.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGE_ROOT = HERE.parent
FIXTURE = HERE / "fixtures" / "wrapped_computations.json"
PROVIDER_PLUGIN = "nasa-daac-knowledge"
BUNDLE = "asdc"
PROVE_SKILL = "energy-budget-closure"


def provider_root() -> Path:
    """The installed provider plugin's root, from the installer's record."""
    override = os.environ.get("NASA_DAAC_KNOWLEDGE")
    if override:
        return Path(override).expanduser().resolve()
    claude = shutil.which("claude")
    if claude is None:
        sys.exit("no `claude` on PATH to read the installed-plugin record; "
                 "set NASA_DAAC_KNOWLEDGE to a checkout of the provider "
                 "repository instead")
    rec = subprocess.run([claude, "plugin", "list", "--json"],
                         capture_output=True, text=True)
    if rec.returncode != 0:
        sys.exit(f"`claude plugin list --json` failed: {rec.stderr.strip()}")
    for entry in json.loads(rec.stdout):
        if entry.get("id", "").split("@")[0] != PROVIDER_PLUGIN:
            continue
        if not entry.get("enabled", True) or entry.get("errors"):
            sys.exit(f"{entry['id']} is installed but not usable: "
                     f"{entry.get('errors') or 'disabled'}")
        return Path(entry["installPath"])
    sys.exit(f"{PROVIDER_PLUGIN} is not installed; it arrives with this "
             "plugin's dependencies (`claude plugin install "
             "atmospheric-physics@open-science-pillars`), or set "
             "NASA_DAAC_KNOWLEDGE to a checkout of the provider repository")


def chains() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["chains"]


def chain_paths(chain: dict) -> tuple[Path, Path]:
    refs = provider_root() / "knowledge" / BUNDLE / "references"
    computation = refs.parent / chain["executor"]
    attester = refs.parent / chain["attester"]
    for p in (computation, attester):
        if not p.is_file():
            sys.exit(f"the provider bundle carries no {p.name} at {p.parent}; "
                     f"the {chain['skill']} chain needs {PROVIDER_PLUGIN} at a "
                     "release that ships it")
    return computation, attester


def run_computation(computation: Path, chain: dict, args: list[str], receipt: Path,
                    runtime: str, runtime_version=None) -> subprocess.CompletedProcess:
    cmd = ["uv", "run", str(computation), "--fixture", "--seed", str(chain["seed"]),
           *args, "--runtime", runtime, "--capability-root", str(PACKAGE_ROOT),
           "--receipt", str(receipt)]
    if runtime_version:
        cmd += ["--runtime-version", runtime_version]
    return subprocess.run(cmd, capture_output=True, text=True)


def run_attester(attester: Path, receipt: Path, out: Path | None = None) -> subprocess.CompletedProcess:
    cmd = ["uv", "run", str(attester), str(receipt)]
    if out is not None:
        cmd += ["--out", str(out)]
    return subprocess.run(cmd, capture_output=True, text=True)


def last_line(p: subprocess.CompletedProcess) -> str:
    text = (p.stdout or "").strip() or (p.stderr or "").strip()
    return text.splitlines()[-1] if text else ""


def close(got: float, want: float, tol: float, what: str) -> None:
    assert abs(got - want) <= tol, f"{what}: {got!r} is not {want!r} within {tol}"


def check_receipt(chain: dict, receipt: dict) -> None:
    """The receipt against what the signed concept records. Read only after
    the attester has passed it, which is the discipline the skills state."""
    skill = chain["skill"]
    expect = chain["expect"]
    tol = expect["tolerance"]

    # Every declared parameter the skill binds is bound in the receipt.
    assert receipt["bound_parameters"] == chain["bound_parameters"], (
        f"{skill}: bound parameters {receipt['bound_parameters']} are not the "
        f"declared {chain['bound_parameters']}")
    assert receipt["refused"] is False, f"{skill}: the reference run refused"
    assert receipt["runtime"]["name"], f"{skill}: the receipt names no runtime"
    assert receipt["run_id"].startswith("sha256:"), f"{skill}: no run identifier"
    assert receipt["capability"]["name"] == "atmospheric-physics", (
        f"{skill}: the capability block names {receipt['capability']['name']!r}, "
        "not this package")
    assert receipt["bundle"]["name"] == PROVIDER_PLUGIN, (
        f"{skill}: the bundle block names {receipt['bundle']['name']!r}")

    months = receipt["months"]
    assert months["n_used"] == expect["months_used"], f"{skill}: months used"
    assert months["n_calendar"] == expect["months_in_window"], f"{skill}: months in window"

    for term, want in expect["terms"].items():
        got = receipt["terms"][term]
        close(got["value"], want["value"], tol, f"{skill} {term}")
        if "uncertainty" in want:
            close(got["uncertainty"], want["uncertainty"], tol, f"{skill} {term} uncertainty")

    field = expect["verdict_field"]
    assert receipt["verdict"][field] is expect["verdict"], (
        f"{skill}: verdict {field} is {receipt['verdict'][field]!r}")

    if "residual" in expect:
        close(receipt["residual"]["value"], expect["residual"], tol, f"{skill} residual")
    if "residual_within" in expect:
        assert abs(receipt["residual"]["value"]) < expect["residual_within"], (
            f"{skill}: residual {receipt['residual']['value']!r} is not inside "
            f"{expect['residual_within']}")
    if "combined_uncertainty" in expect:
        close(receipt["combined_uncertainty"]["value"], expect["combined_uncertainty"],
              tol, f"{skill} combined uncertainty")

    # The energy budget's anomaly trend, in which the product's anchor cancels.
    if "anomaly_trend_W_m2_per_decade" in expect:
        trend = receipt["terms"]["toa_net_anomaly_trend"]
        close(trend["value"], expect["anomaly_trend_W_m2_per_decade"], tol,
              f"{skill} anomaly trend")
        lo, hi = expect["anomaly_trend_interval"]
        close(trend["value"] - trend["uncertainty"], lo, tol, f"{skill} trend interval low")
        close(trend["value"] + trend["uncertainty"], hi, tol, f"{skill} trend interval high")
        shared = receipt["bookkeeping"]["anchoring"]["months_shared_with_anchor_decade"]
        assert isinstance(shared, int), f"{skill}: the anchoring block counts no shared months"

    # The cloud radiative effect's contrast under the other convention.
    if "contrast_convention" in expect:
        contrast = receipt["convention_contrast"]
        assert contrast["convention"] == expect["contrast_convention"], (
            f"{skill}: the contrast is against {contrast['convention']!r}")
        close(contrast["cre_net"], expect["contrast_cre_net"], tol, f"{skill} contrast net")
        close(receipt["terms"]["cre_net"]["value"] - contrast["cre_net"],
              expect["contrast_difference"], tol, f"{skill} contrast difference")

    assert receipt["caveats"], f"{skill}: the receipt states no caveats"


def golden() -> int:
    failures = []
    for chain in chains():
        skill = chain["skill"]
        computation, attester = chain_paths(chain)
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            receipt_path = tmp / "receipt.json"
            run = run_computation(computation, chain, chain["args"], receipt_path, "goldens")
            if run.returncode != 0:
                failures.append(f"{skill}: the fixture run exited {run.returncode}: {last_line(run)}")
                continue
            att = run_attester(attester, receipt_path)
            if att.returncode != 0:
                failures.append(f"{skill}: the attester did not pass the receipt: {last_line(att)}")
                continue
            verdict = last_line(att)
            try:
                check_receipt(chain, json.loads(receipt_path.read_text(encoding="utf-8")))
            except AssertionError as bad:
                failures.append(f"{skill}: {bad}")
                continue
            print(f"== {skill} wraps {chain['concept']}")
            print(f"   bound {chain['bound_parameters']}")
            print(f"   {verdict}")

            refusal = chain["refusal"]
            refusal_path = tmp / "refusal.json"
            ref = run_computation(computation, chain, refusal["args"], refusal_path, "goldens")
            if ref.returncode != 3:
                failures.append(f"{skill}: the refusal case exited {ref.returncode}, not 3")
                continue
            body = json.loads(refusal_path.read_text(encoding="utf-8"))
            if body.get("refused") is not True or body.get("reason_code") != refusal["reason_code"]:
                failures.append(f"{skill}: the refusal is {body.get('reason_code')!r}, "
                                f"not {refusal['reason_code']!r}")
                continue
            ratt = run_attester(attester, refusal_path)
            rline = last_line(ratt)
            if ratt.returncode != 0 or not rline.startswith("PASS refusal"):
                failures.append(f"{skill}: the refusal did not attest as a refusal: {rline}")
                continue
            print(f"   refusal {refusal['reason_code']}: exit 3, {rline.split(' run ')[0]}")
    for bad in failures:
        print(f"FAIL {bad}", file=sys.stderr)
    if failures:
        return 1
    print(f"wrapped computations: {len(chains())} chains, each run, attested and refused as the "
          "concept records")
    return 0


def prove(runtime: str, runtime_version: str | None, out: Path) -> int:
    chain = next(c for c in chains() if c["skill"] == PROVE_SKILL)
    computation, _ = chain_paths(chain)
    run = run_computation(computation, chain, chain["args"], out, runtime, runtime_version)
    print((run.stdout or "") + (run.stderr or ""), end="")
    return run.returncode


def attest(receipt_path: Path, out: Path) -> int:
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    computation = receipt.get("computation", "")
    chain = next((c for c in chains() if c["executor"] == computation), None)
    if chain is None:
        sys.exit(f"no wrapping skill here runs {computation!r}")
    _, attester = chain_paths(chain)
    att = run_attester(attester, receipt_path, out)
    print((att.stdout or "") + (att.stderr or ""), end="")
    return att.returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runtime", help="the runtime that ran this (PROVE)")
    ap.add_argument("--runtime-version")
    ap.add_argument("--attest", metavar="RECEIPT", help="attest this receipt")
    ap.add_argument("--out", metavar="PATH", help="where the receipt or attestation is written")
    args = ap.parse_args()
    if args.attest:
        if not args.out:
            ap.error("--attest needs --out")
        return attest(Path(args.attest), Path(args.out))
    if args.runtime:
        if not args.out:
            ap.error("--runtime needs --out")
        return prove(args.runtime, args.runtime_version, Path(args.out))
    return golden()


if __name__ == "__main__":
    sys.exit(main())
