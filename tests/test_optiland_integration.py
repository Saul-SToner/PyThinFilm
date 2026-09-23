"""Tests for the dependency-free part of the optional Optiland bridge."""

import json

import pytest

from thinfilm.optiland_integration import (
    CoatingLayerInput,
    CoatingStackInput,
    SequentialSurfaceInput,
    SequentialSystemInput,
    make_singlet_system_input,
    make_teaching_system_input,
    optiland_runtime_status,
    referenced_material_records,
)


def _front_stack(*, coated: bool = True) -> CoatingStackInput:
    layers = (
        CoatingLayerInput("MgF2", 99.7456876693, "Real MgF2"),
    ) if coated else ()
    return CoatingStackInput("Air", "N-BK7", layers)


def test_minimal_system_contract_is_json_serializable() -> None:
    spec = make_singlet_system_input(
        name="AR singlet",
        glass_material_id="N-BK7",
        front_coating=_front_stack(),
        wavelength_um=0.55,
    )

    encoded = json.dumps(spec.to_dict())

    assert '"thickness_nm": 99.7456876693' in encoded
    assert spec.material_ids() == ("Air", "N-BK7", "MgF2")
    assert spec.surfaces[0].thickness_mm == "infinity"


def test_material_records_keep_pythinfilm_provenance() -> None:
    spec = make_singlet_system_input(
        name="AR singlet",
        glass_material_id="N-BK7",
        front_coating=_front_stack(),
        wavelength_um=0.55,
    )

    records = {row["material_id"]: row for row in referenced_material_records(spec)}

    assert "Dodge" in records["MgF2"]["source"]
    assert "Schott" in records["N-BK7"]["source"]
    assert records["MgF2"]["file"].endswith("MgF2_Dodge_o.csv")


def test_system_rejects_coating_incident_medium_mismatch() -> None:
    bad_stack = CoatingStackInput("N-BK7", "N-BK7")

    with pytest.raises(ValueError, match="does not match previous medium"):
        make_singlet_system_input(
            name="invalid",
            glass_material_id="N-BK7",
            front_coating=bad_stack,
            wavelength_um=0.55,
        )


def test_system_rejects_coating_substrate_medium_mismatch() -> None:
    bad_stack = CoatingStackInput("Air", "SiO2")

    with pytest.raises(ValueError, match="does not match transmitted medium"):
        make_singlet_system_input(
            name="invalid",
            glass_material_id="N-BK7",
            front_coating=bad_stack,
            wavelength_um=0.55,
        )


@pytest.mark.parametrize("thickness_nm", [0.0, -1.0, float("inf")])
def test_coating_layer_requires_positive_finite_thickness(thickness_nm: float) -> None:
    with pytest.raises(ValueError, match="finite and positive"):
        CoatingLayerInput("MgF2", thickness_nm)


def test_material_wavelength_validation_accepts_visible_design() -> None:
    spec = make_singlet_system_input(
        name="visible",
        glass_material_id="N-BK7",
        front_coating=_front_stack(),
        wavelength_um=0.55,
    )

    spec.validate_material_wavelength_ranges()


def test_material_wavelength_validation_rejects_out_of_range() -> None:
    spec = make_singlet_system_input(
        name="outside BK7 data",
        glass_material_id="N-BK7",
        front_coating=_front_stack(coated=False),
        wavelength_um=0.2,
    )

    with pytest.raises(ValueError, match="N-BK7 does not cover"):
        spec.validate_material_wavelength_ranges()


def test_system_input_rejects_nonsequential_coating_on_object_surface() -> None:
    with pytest.raises(ValueError, match="object surface"):
        SequentialSystemInput(
            name="invalid",
            surfaces=(
                SequentialSurfaceInput(
                    material_id="Air",
                    coating=CoatingStackInput("Air", "Air"),
                ),
                SequentialSurfaceInput(material_id="Air"),
            ),
            wavelengths_um=(0.55,),
        )


def test_explicit_missing_checkout_reports_optional_runtime_unavailable(tmp_path) -> None:
    status = optiland_runtime_status(tmp_path / "missing-optiland")

    assert status["available"] is False
    assert "source checkout not found" in status["error"]


@pytest.mark.parametrize(
    ("template", "expected_surface_count", "expected_aperture"),
    [
        ("single_lens_imaging", 4, 10.0),
        ("phone_camera_module", 8, 5.0),
        ("wide_field_camera", 6, 10.0),
        ("complex_camera_lens", 8, 9.0),
        ("dual_band_imager", 6, 7.0),
        ("spectral_camera", 4, 5.0),
        ("folded_reflector", 5, 6.0),
    ],
)
def test_teaching_templates_keep_distinct_system_shapes(template: str, expected_surface_count: int, expected_aperture: float) -> None:
    spec = make_teaching_system_input(
        template=template,
        name=template,
        glass_material_id="N-BK7",
        front_coating=_front_stack(),
        wavelength_um=0.55,
    )

    assert len(spec.surfaces) == expected_surface_count
    assert spec.aperture_epd_mm == expected_aperture
