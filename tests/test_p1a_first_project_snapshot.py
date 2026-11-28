"""First-project snapshot provenance and closed-reference regression tests."""
import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import bridge.openclaw_product_contract as contract
import bridge.refresh_openclaw_media_contract_snapshot as refresh


FROZEN_UPSTREAM_COMMIT = "21c170d0bdd26a425a97bd3e1c3020b320d95fdb"
FROZEN_SOURCE_SHA256 = "55902637deab958717b610a18f13a31eea17450d65c88017bf258801968605bc"
FROZEN_EXAMPLES_SHA256 = "5ed16e9ac0b2ce337b3afddbd1f00b49066da372f4dfa90eefcca5cab68d36eb"
FROZEN_CONTENT_SHA256 = "17efad3beaf9974e4a1a85786d42dbbf3139b9ae2e8cad43772bfb1674e56b78"


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args])


def commit_fixture(root, message):
    git(root, "add", ".")
    git(root, "-c", "user.name=Test", "-c", "user.email=test@example.test", "commit", "-qm", message)


def make_upstream(root):
    root.mkdir()
    git(root, "init", "-q")
    pin = contract.load_snapshot()["p1a_first_project"]
    product = {
        "api_base": "/media/api",
        "p1a_first_project": pin["contract"],
        "api_schemas": pin["api_schemas"],
    }
    product["p1a_first_project"]["examples"]["studio_pending"]["fixture_note"] = "synthetic upstream"
    path = root / refresh.PRODUCT_CONTRACT_RELATIVE_PATH
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(product), encoding="utf-8")
    pipelines = [{"pipeline_id": value, "version": "1"} for value in refresh.PIPELINE_ALIASES.values()]
    digest = refresh.catalog_digest(pipelines)
    for item in pipelines:
        item["catalog_digest"] = digest
    catalog = {
        "contract_id": "openclaw_media_product_v1",
        "contract_version": 1,
        "catalog_digest": digest,
        "pipeline_count": len(pipelines),
        "pipelines": pipelines,
    }
    catalog_path = root / refresh.CATALOG_RELATIVE_PATH
    catalog_path.parent.mkdir(parents=True)
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
    commit_fixture(root, "fixture")
    return path, product


def test_committed_fixture_reproducible_and_dirty_rejected(tmp_path):
    upstream = tmp_path / "upstream"
    path, _ = make_upstream(upstream)
    first = refresh.regenerate_snapshot(upstream)
    second = refresh.regenerate_snapshot(upstream)
    one, two = tmp_path / "one.json", tmp_path / "two.json"
    refresh.write_snapshot(one, first)
    refresh.write_snapshot(two, second)
    assert one.read_bytes() == two.read_bytes()
    assert first["upstream_commit"] == git(upstream, "rev-parse", "HEAD").decode().strip()
    assert first["p1a_first_project"]["source_sha256"] == "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    assert contract.require_p1a_snapshot(first)["examples"] == json.loads(path.read_text())["p1a_first_project"]["examples"]
    path.write_text(path.read_text() + "\n")
    with pytest.raises(refresh.SnapshotRefreshError, match="uncommitted"):
        refresh.regenerate_snapshot(upstream)


def test_missing_definition_and_digest_rejected(tmp_path):
    upstream = tmp_path / "upstream"
    path, product = make_upstream(upstream)
    del product["p1a_first_project"]["schema"]["$defs"]["DeviceSelection"]
    path.write_text(json.dumps(product), encoding="utf-8")
    commit_fixture(upstream, "remove definition")
    with pytest.raises(contract.ProductContractError, match="unresolved"):
        refresh.regenerate_snapshot(upstream)
    bad = copy.deepcopy(contract.load_snapshot())
    bad["p1a_first_project"]["content_sha256"] = "sha256:" + "0" * 64
    with pytest.raises(contract.ProductContractError, match="digest mismatch"):
        contract.validate_snapshot(bad)


def test_legacy_pin_loads_but_p1a_consumer_rejects():
    legacy = copy.deepcopy(contract.load_snapshot())
    del legacy["p1a_first_project"]
    contract.validate_snapshot(legacy)
    with pytest.raises(contract.ProductContractError, match="p1a_snapshot_missing"):
        contract.require_p1a_snapshot(legacy)


def test_checked_in_pin_matches_frozen_u08_input(tmp_path):
    snapshot = contract.load_snapshot()
    pin = snapshot["p1a_first_project"]
    examples = contract.require_p1a_snapshot(snapshot)["examples"]
    example_bytes = json.dumps(examples, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    # These digests come from the frozen Git source and keep the test independent
    # of a sibling checkout during ordinary Photo test runs.
    assert snapshot["upstream_commit"] == FROZEN_UPSTREAM_COMMIT
    assert snapshot["api_base"] == "/media/api"
    assert pin["source_sha256"] == "sha256:" + FROZEN_SOURCE_SHA256
    assert pin["content_sha256"] == "sha256:" + FROZEN_CONTENT_SHA256
    assert hashlib.sha256(example_bytes).hexdigest() == FROZEN_EXAMPLES_SHA256

    if upstream_path := os.environ.get("PHOTO_P1A_FROZEN_UPSTREAM"):
        upstream = Path(upstream_path)
        source_bytes = git(
            upstream, "show", f"{FROZEN_UPSTREAM_COMMIT}:{refresh.PRODUCT_CONTRACT_RELATIVE_PATH.as_posix()}",
        )
        assert hashlib.sha256(source_bytes).hexdigest() == FROZEN_SOURCE_SHA256
        frozen = json.loads(source_bytes)
        assert pin["contract"] == frozen["p1a_first_project"]
        assert pin["api_schemas"] == {name: frozen["api_schemas"][name] for name in pin["api_schemas"]}
        generated = tmp_path / "frozen.json"
        refresh.write_snapshot(generated, refresh.regenerate_snapshot(upstream))
        assert generated.read_bytes() == contract.SNAPSHOT_PATH.read_bytes()
