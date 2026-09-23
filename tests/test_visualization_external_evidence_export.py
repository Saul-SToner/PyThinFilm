import hashlib
import json
from pathlib import Path

from tools.export_visualization_cases import compute_hash
from tools.export_visualization_external_evidence_cases import (
    EXTERNAL_DATA_DIR,
    EXTERNAL_EVIDENCE_CASES,
)


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "web3d" / "public" / "evidence"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(case_id: str) -> dict:
    return json.loads((EVIDENCE_DIR / f"{case_id}.json").read_text(encoding="utf-8"))


def test_all_external_evidence_contracts_are_present_and_self_consistent():
    exported = {path.stem for path in EVIDENCE_DIR.glob("*.json")}
    assert exported == set(EXTERNAL_EVIDENCE_CASES)

    for case_id in EXTERNAL_EVIDENCE_CASES:
        contract = _load(case_id)
        assert contract["case_id"] == case_id
        assert contract["schema_version"] == "1.0.0"
        assert contract["calculation_source"] in {
            "python_external_csv_analysis",
            "python_template_export",
        }
        assert isinstance(contract["summary_cards"], list)
        assert isinstance(contract["series"], list)
        assert isinstance(contract["table"]["rows"], list)

        evidence_payload = {
            key: contract[key]
            for key in (
                "case_id", "calculation_source", "evidence_status",
                "external_data_provenance", "summary_cards", "series",
                "table", "limitations",
            )
        }
        assert contract["evidence_hash"] == compute_hash(evidence_payload)
        without_result_hash = {key: value for key, value in contract.items() if key != "result_hash"}
        assert contract["result_hash"] == compute_hash(without_result_hash)

        serialized = json.dumps(contract, ensure_ascii=False)
        assert "C:\\\\Users" not in serialized
        assert "OneDrive" not in serialized
        assert "deg.p" not in serialized


def test_provenance_hashes_match_available_external_inputs():
    for case_id in EXTERNAL_EVIDENCE_CASES:
        for item in _load(case_id)["external_data_provenance"]:
            source = EXTERNAL_DATA_DIR / item["file_name"]
            if item["status"] == "AVAILABLE":
                assert source.is_file()
                assert item["size_bytes"] == source.stat().st_size
                assert item["sha256"] == _sha256(source)
            else:
                assert item["status"] == "MISSING"
                assert not source.is_file()
                assert item["size_bytes"] == 0
                assert item["sha256"] is None


def test_degraded_and_template_cases_do_not_overclaim_evidence():
    for case_id in ("tamm_interface_window_bundle", "tamm_interface_window_scan"):
        contract = _load(case_id)
        assert contract["evidence_status"] == "DEGRADED_PARTIAL_INPUT"
        statuses = [item["status"] for item in contract["external_data_provenance"]]
        assert statuses.count("AVAILABLE") == 3
        assert statuses.count("MISSING") == 3
        assert any("热力图" in note for note in contract["limitations"])

    baseline = _load("absorbing_baseline_template")
    assert baseline["evidence_status"] == "TEMPLATE_ONLY"
    assert baseline["series"] == []
    assert any("不会绘制虚构光谱" in note for note in baseline["limitations"])
