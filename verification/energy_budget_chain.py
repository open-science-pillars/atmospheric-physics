#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Golden for the energy budget closure this capability carries: the
chain the provider bundle's check routine ran before the move, written
as a golden that runs here.

Nothing scientific is reimplemented and nothing is downloaded. The
executor, the attester and the two loaders are the scripts of the
`energy-budget-closure` skill, under the contract
knowledge/computations/energy-budget.md; the stamped data root is
knowledge/references/retrieval/energy-budget-root, committed as data,
with the Argo ocean heat content receipt the ocean side is read from.
The expected values are quoted from the concept's Reference run
section and committed beside this file in
fixtures/energy-budget-chain.json (provenance in the README there).

What is checked, in order:

  1. the attester's selftest, which exercises its tampers, its wrong
     release, its refusals and its forged cases;
  2. the two loaders' selftests, each on a synthetic grid;
  3. the fixture chain: the executor at seed 7 over the reference
     window, the attester on the receipt, and only then the receipt
     against what the concept records;
  4. the refusal the chain exercises: a window outside the radiation
     record, which must exit 3, carry its reason code and attest PASS
     only as a refusal;
  5. the committed data root's manifest check;
  6. the anchored real-data run on that root, attested against the
     tree with --data-root, and its terms, its residual, its bar, its
     verdict, its anomaly trend, its shared-month count, the identity
     of the Argo receipt it read and the same terms as energy over the
     window, each against the concept.

Exit 0 only when all of it holds. Offline, headless, no credential and
no NASA host reachable: the fixture is regenerated from the seed by a
stdlib hash stream, and the real run reads the committed tree.

  uv run verification/energy_budget_chain.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGE_ROOT = HERE.parent
EXPECT = json.loads((HERE / "fixtures" / "energy-budget-chain.json").read_text(encoding="utf-8"))
RUNTIME = "goldens"


def script(key: str) -> Path:
    return PACKAGE_ROOT / EXPECT[key]


def run(argv: list, expect_code: int = 0) -> subprocess.CompletedProcess:
    p = subprocess.run(["uv", "run", *[str(a) for a in argv]],
                       cwd=str(PACKAGE_ROOT), capture_output=True, text=True)
    assert p.returncode == expect_code, (
        f"{argv[0]} exited {p.returncode}, not {expect_code}: "
        f"{((p.stdout or '') + (p.stderr or '')).strip()[-600:]}")
    return p


def last_line(p: subprocess.CompletedProcess) -> str:
    text = (p.stdout or "").strip() or (p.stderr or "").strip()
    return text.splitlines()[-1] if text else ""


def close(got: float, want: float, what: str, tol: float = None) -> None:
    tol = EXPECT["tolerance"] if tol is None else tol
    assert abs(got - want) <= tol, f"{what}: {got!r} is not {want!r} within {tol}"


def check_receipt(spec: dict, r: dict) -> None:
    """The receipt against the concept. Read only after the attester has
    passed it, which is the discipline the skill states."""
    name = spec["name"]
    assert r["refused"] is False, f"{name}: the reference run refused"
    assert r["bound_parameters"] == spec["bound_parameters"], (
        f"{name}: bound {r['bound_parameters']}, not {spec['bound_parameters']}")
    assert r["computation"] == EXPECT["executor"], (
        f"{name}: the receipt names the computation {r['computation']!r}")
    for block in ("capability", "bundle"):
        assert r[block]["name"] == "atmospheric-physics", (
            f"{name}: the {block} block names {r[block]['name']!r}, not this package")
    assert r["months"]["n_used"] == spec["months_used"], f"{name}: months used"
    assert r["months"]["n_calendar"] == spec["months_in_window"], f"{name}: months in window"

    for term, want in spec["terms"].items():
        close(r["terms"][term]["value"], want["value"], f"{name} {term}")
        close(r["terms"][term]["uncertainty"], want["uncertainty"], f"{name} {term} uncertainty")
    close(r["residual"]["value"], spec["residual"], f"{name} residual")
    close(r["combined_uncertainty"]["value"], spec["combined_uncertainty"],
          f"{name} combined uncertainty")
    assert r["verdict"]["closed_within_uncertainty"] is spec["verdict"], (
        f"{name}: the verdict is {r['verdict']['closed_within_uncertainty']!r}")

    trend = r["terms"]["toa_net_anomaly_trend"]
    close(trend["value"], spec["anomaly_trend_W_m2_per_decade"], f"{name} anomaly trend")
    lo, hi = spec["anomaly_trend_interval"]
    close(trend["value"] - trend["uncertainty"], lo, f"{name} trend interval low")
    close(trend["value"] + trend["uncertainty"], hi, f"{name} trend interval high")

    if "ocean_side" in spec:
        close(r["residual"]["ocean_side_sum"], spec["ocean_side"]["value"], f"{name} ocean side")
        close(r["residual"]["ocean_side_uncertainty"], spec["ocean_side"]["uncertainty"],
              f"{name} ocean side uncertainty")
    if "months_shared_with_anchor_decade" in spec:
        shared = r["bookkeeping"]["anchoring"]["months_shared_with_anchor_decade"]
        assert shared == spec["months_shared_with_anchor_decade"], (
            f"{name}: the anchoring block counts {shared} months shared with the anchor decade")
    if "argo_receipt_run_id" in spec:
        receipt = r["bookkeeping"]["ocean_input"]["receipt"]
        assert receipt["run_id"] == spec["argo_receipt_run_id"], (
            f"{name}: the ocean side was read from {receipt['run_id']!r}")
        assert receipt["refused"] is False, f"{name}: the Argo receipt is a refusal"
    assert r["caveats"], f"{name}: the receipt states no caveats"


def main() -> int:
    executor, attester = script("executor"), script("attester")
    root = PACKAGE_ROOT / EXPECT["data_root"]

    for loader in EXPECT["loaders"]:
        run([PACKAGE_ROOT / loader, "--selftest"])
    print(f"== selftests: the attester and {len(EXPECT['loaders'])} loaders")
    run([attester, "--selftest"])

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for spec in EXPECT["runs"]:
            receipt = tmp / f"{spec['name']}.json"
            argv = [executor, *spec["args"], "--runtime", RUNTIME, "--receipt", receipt]
            attest = [attester, receipt]
            if spec.get("on_data_root"):
                run([PACKAGE_ROOT / EXPECT["loaders"][1], "--root", root, "--check"])
                argv = [executor, "--data-root", root, *spec["args"],
                        "--runtime", RUNTIME, "--receipt", receipt]
                attest = [attester, receipt, "--data-root", root]
            run(argv)
            verdict = last_line(run(attest))
            check_receipt(spec, json.loads(receipt.read_text(encoding="utf-8")))
            print(f"== {spec['name']} run of {EXPECT['concept']}")
            print(f"   {verdict}")

        refusal = EXPECT["refusal"]
        path = tmp / "refusal.json"
        run([executor, *refusal["args"], "--runtime", RUNTIME, "--receipt", path], expect_code=3)
        body = json.loads(path.read_text(encoding="utf-8"))
        assert body["refused"] is True and body["reason_code"] == refusal["reason_code"], (
            f"the refusal is {body.get('reason_code')!r}, not {refusal['reason_code']!r}")
        line = last_line(run([attester, path]))
        assert line.startswith("PASS refusal"), f"the refusal did not attest as a refusal: {line}"
        print(f"   refusal {refusal['reason_code']}: exit 3, attested as a refusal")

    print("energy budget chain: the attester and both loaders selftest, the fixture run and the "
          f"anchored run on {EXPECT['record']} reproduce every value "
          f"{EXPECT['concept']} records, and the window refusal is a refusal")
    return 0


if __name__ == "__main__":
    sys.exit(main())
