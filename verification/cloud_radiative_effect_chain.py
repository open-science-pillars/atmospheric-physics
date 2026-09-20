#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Golden for the cloud radiative effect this capability carries: the
chain the provider bundle's check routine ran before the move, written
as a golden that runs here, with the eight regions on both clear-sky
conventions beside it.

Nothing scientific is reimplemented and nothing is downloaded. The
executor, the attester and the two loaders are the scripts of the
`cloud-radiative-effect` skill, under the contract
knowledge/computations/cloud-radiative-effect.md; the stamped data root
is knowledge/references/retrieval/cloud-radiative-effect-root,
committed as data. The expected values are committed beside this file
in fixtures/cloud-radiative-effect-chain.json, the four reference runs
quoted from the concept and the eight-region table measured from
receipts the attester passed (provenance in the README there).

What is checked, in order:

  1. the attester's selftest, which exercises its tampers, its wrong
     release, all five refusals and its forged cases;
  2. the two loaders' selftests, each on a synthetic grid;
  3. the fixture chain: the executor at seed 7 with every declared
     parameter bound, the attester on the receipt, and only then the
     receipt against what the concept records;
  4. the refusal the chain exercises: a clear-sky convention the
     product does not carry, which must exit 3, carry its reason code
     and attest PASS only as a refusal;
  5. the committed data root's manifest check;
  6. the three real-data runs the concept records, attested against
     the tree with --data-root: the published anchor on the
     cloud-free-area convention with its distance from the published
     global mean, the companion run on the other convention over the
     same months, which states no distance, and the Antarctic band;
  7. the eight regions on both conventions over one window, every cell
     equal to the term of the receipt it was copied from and to the
     recorded table, and the sign of the convention difference
     asserted band by band: negative over the six non-polar bands and
     reversed over the arctic and the antarctic.

Exit 0 only when all of it holds. Offline, headless, no credential and
no NASA host reachable.

  uv run verification/cloud_radiative_effect_chain.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGE_ROOT = HERE.parent
EXPECT = json.loads(
    (HERE / "fixtures" / "cloud-radiative-effect-chain.json").read_text(encoding="utf-8"))
RUNTIME = "goldens"


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
        if "uncertainty" in want:
            close(r["terms"][term]["uncertainty"], want["uncertainty"],
                  f"{name} {term} uncertainty")
    assert abs(r["residual"]["value"]) < spec["residual_within"], (
        f"{name}: the decomposition residual {r['residual']['value']!r} is not inside "
        f"{spec['residual_within']}")
    assert r["verdict"]["decomposition_closes"] is spec["verdict"], (
        f"{name}: the verdict is {r['verdict']['decomposition_closes']!r}")

    contrast = r["convention_contrast"]
    assert contrast["convention"] == spec["contrast_convention"], (
        f"{name}: the contrast is against {contrast['convention']!r}")
    close(contrast["cre_net"], spec["contrast_cre_net"], f"{name} contrast net")
    if "contrast_difference" in spec:
        close(r["terms"]["cre_net"]["value"] - contrast["cre_net"],
              spec["contrast_difference"], f"{name} contrast difference")
    if "published_distance_cre_net" in spec:
        close(r["published_comparison"]["distance_W_m2"]["cre_net"],
              spec["published_distance_cre_net"], f"{name} published distance")
    if spec.get("no_published_distance"):
        published = r["published_comparison"]
        assert published["comparable"] is False, (
            f"{name}: the receipt calls the run comparable with a published figure of "
            "another convention")
        assert published["convention_matches"] is False, (
            f"{name}: the receipt says the convention matches the published figure's")
        assert published["distance_W_m2"] is None, (
            f"{name}: the receipt states the distance {published['distance_W_m2']!r} for a run "
            "whose convention the published figure is not of")
    assert r["caveats"], f"{name}: the receipt states no caveats"


def region_table(executor: Path, attester: Path, root: Path, tmp: Path) -> None:
    """The eight regions on both conventions: every cell from a receipt
    the attester passed, against the recorded table, and the sign of the
    convention difference band by band."""
    window = EXPECT["regions"]["window"]
    conventions = EXPECT["regions"]["conventions"]
    reversed_bands = set(EXPECT["regions"]["sign_reversal_bands"])
    tol = EXPECT["measured_tolerance"]
    for row in EXPECT["regions"]["table"]:
        region = row["region"]
        for convention in conventions:
            path = tmp / f"{region}-{convention}.json"
            run([executor, "--data-root", root, "--region", region,
                 "--clear-sky", convention, "--window", window,
                 "--runtime", RUNTIME, "--receipt", path])
            run([attester, path, "--data-root", root])
            r = json.loads(path.read_text(encoding="utf-8"))
            want = row[convention]
            for term in ("cre_shortwave", "cre_longwave", "cre_net"):
                got = r["terms"][term]["value"]
                close(got, want[term], f"{region} {convention} {term}",
                      tol=abs(want[term]) * tol + tol)
            close(r["convention_contrast"]["cre_net"], want["contrast_cre_net"],
                  f"{region} {convention} contrast net",
                  tol=abs(want["contrast_cre_net"]) * tol + tol)
        difference = (row[conventions[0]]["cre_net"]
                      - row[conventions[0]]["contrast_cre_net"])
        close(difference, row["total_region_minus_cloud_free_area_net"],
              f"{region} convention difference", tol=abs(difference) * tol + tol)
        if region in reversed_bands:
            assert difference > 0, (
                f"{region}: the sign reversal of the convention difference is gone; the band "
                f"gives {difference!r}, which is not the reversed sign the concept states")
        else:
            assert difference < 0, (
                f"{region}: the convention difference is {difference!r}, not the negative sign "
                "every band but the polar ones carries")
        print(f"   {region:24} total-region minus cloud-free-area net {difference:+8.4f} W m-2")


def main() -> int:
    executor = PACKAGE_ROOT / EXPECT["executor"]
    attester = PACKAGE_ROOT / EXPECT["attester"]
    root = PACKAGE_ROOT / EXPECT["data_root"]

    for loader in EXPECT["loaders"]:
        run([PACKAGE_ROOT / loader, "--selftest"])
    run([attester, "--selftest"])
    print(f"== selftests: the attester and {len(EXPECT['loaders'])} loaders")
    run([PACKAGE_ROOT / EXPECT["loaders"][1], "--root", root, "--check"])

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for spec in EXPECT["runs"]:
            receipt = tmp / f"{spec['name']}.json"
            argv = [executor]
            attest = [attester, receipt]
            if spec.get("on_data_root"):
                argv += ["--data-root", root]
                attest += ["--data-root", root]
            argv += [*spec["args"], "--runtime", RUNTIME, "--receipt", receipt]
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

        print(f"== the eight regions on both conventions over {EXPECT['regions']['window']}")
        region_table(executor, attester, root, tmp)

    print("cloud radiative effect chain: the attester and both loaders selftest, the fixture run, "
          f"the three anchored runs on {EXPECT['record']} and the convention refusal are as "
          f"{EXPECT['concept']} records them, and the eight regions reproduce on both conventions "
          "with the sign reversal over the polar bands intact")
    return 0


if __name__ == "__main__":
    sys.exit(main())
