import numpy as np

from thinfilm.figure_audit import (
    audit_external_comparison,
    audit_missing_values,
    audit_rta_data,
    build_figure_audit,
    collect_figure_audits,
    publication_scope,
    write_figure_audit,
)


def test_valid_conservative_rta_passes():
    wl = np.array([500.0, 550.0, 600.0])
    R = np.array([0.2, 0.1, 0.3])
    T = 1.0 - R
    check = audit_rta_data(wl, R, T, np.zeros_like(R), focus="R", feature_kind="valley", feature_wavelength=550.0)
    assert check["passed"]
    assert check["metrics"]["max_energy_conservation_error"] == 0.0


def test_rta_catches_bounds_conservation_and_wrong_feature():
    check = audit_rta_data(
        [500.0, 550.0, 600.0],
        [0.2, 1.1, 0.3],
        [0.7, 0.1, 0.6],
        [0.0, 0.0, 0.0],
        focus="R",
        feature_kind="peak",
        feature_wavelength=500.0,
    )
    codes = {item["code"] for item in check["issues"]}
    assert {"response_out_of_bounds", "energy_conservation", "feature_mismatch"} <= codes


def test_comsol_claim_without_source_fails():
    check = audit_external_comparison([0.1, 0.2], [0.1, 0.21], reference_label="COMSOL", reference_file=None)
    audit = build_figure_audit(figure_id="x", title="x", evidence_level="external_validation", checks=[check])
    assert audit["status"] == "fail"
    assert audit["issues"][0]["code"] == "missing_reference_source"


def test_wrong_residual_definition_fails(tmp_path):
    source = tmp_path / "reference.csv"
    source.write_text("x,y\n1,2\n", encoding="utf-8")
    check = audit_external_comparison(
        [0.2, 0.4], [0.1, 0.3], reference_label="external", reference_file=source, residual=[0.1, -0.1]
    )
    assert not check["passed"]
    assert any(item["code"] == "residual_definition" for item in check["issues"])


def test_missing_values_are_warning_not_zero():
    check = audit_missing_values([0.5, None, np.nan])
    audit = build_figure_audit(figure_id="x", title="x", evidence_level="theory", checks=[check])
    assert audit["status"] == "warn"
    assert check["metrics"]["missing_count"] == 2


def test_publication_scope_excludes_placeholder_and_failures():
    placeholder = build_figure_audit(figure_id="p", title="p", evidence_level="placeholder", checks=[])
    assert placeholder["status"] == "warn"
    assert publication_scope(placeholder) == "excluded"
    approximation = build_figure_audit(figure_id="a", title="a", evidence_level="approximation", checks=[])
    assert publication_scope(approximation) == "appendix"


def test_delivery_gate_collects_and_fails_on_bad_audit(tmp_path):
    good = build_figure_audit(figure_id="good", title="good", evidence_level="theory", checks=[])
    bad_check = audit_external_comparison([0.1], [0.1], reference_label="COMSOL", reference_file=None)
    bad = build_figure_audit(figure_id="bad", title="bad", evidence_level="external_validation", checks=[bad_check])
    write_figure_audit(tmp_path / "good_figure_audit.json", good)
    write_figure_audit(tmp_path / "bad_figure_audit.json", bad)
    manifest = collect_figure_audits([tmp_path])
    assert manifest["gate_status"] == "fail"
    assert manifest["counts"]["main_text"] == 1
    assert manifest["counts"]["excluded"] == 1
