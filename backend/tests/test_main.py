"""Unit tests for George voice formatting helpers (no Qdrant required)."""

from __future__ import annotations

from main import (
    ShopVehicleCatalog,
    _parse_vision_result,
    _validate_jpeg,
    _infer_vehicle_fields,
    _vehicle_fields_in_catalog,
    format_number_for_speech,
    format_voice_answer,
    query_normalizer,
    to_single_line,
)


def test_validate_jpeg_accepts_jpeg_signature() -> None:
    _validate_jpeg(b"\xff\xd8\xff\xe0demo", "image/jpeg")


def test_validate_jpeg_rejects_non_jpeg() -> None:
    import pytest

    with pytest.raises(Exception):
        _validate_jpeg(b"not-an-image", "image/jpeg")


def test_parse_vision_result_clamps_confidence() -> None:
    parsed = _parse_vision_result(
        '{"component":"intake manifold","confidence":2,"visual_context":"cast aluminum runner","uncertainty":"partially occluded"}'
    )
    assert parsed["component"] == "intake manifold"
    assert parsed["confidence"] == 1.0

_CAUTION_CHUNK = """| Application | Torque | Notes |
| --- | --- | --- |
| Intake Bolts | 15-18 foot-pounds | |
Caution: Serious damage can occur when ignition is not installed correctly.
"""

_DEMO_CATALOG = ShopVehicleCatalog(
    makes=frozenset({"subaru"}),
    models=frozenset({"wrx"}),
    years=frozenset({"2022"}),
    triples=frozenset({("2022", "subaru", "wrx")}),
)


def test_part_number_226_020_speech_spaced() -> None:
    spoken = format_number_for_speech(to_single_line("226.020"))
    assert spoken == "2 2 6 0 2 0"


def test_part_number_12_13_speech_spaced() -> None:
    spoken = format_number_for_speech(to_single_line("12.13"))
    assert spoken == "1 2 1 3"


def test_query_normalizer_collapses_digit_gaps() -> None:
    assert query_normalizer("20. 22") == "2022"
    assert "2022" in query_normalizer("20. 22 WRX")


def test_query_normalizer_repairs_wrx_mishears() -> None:
    assert query_normalizer("W R X oil drain plug") == "wrx oil drain plug"
    assert query_normalizer("w.r.x. spark plugs") == "wrx. spark plugs"
    assert query_normalizer("my subie") == "my subaru"


def test_format_voice_answer_suppresses_caution_on_torque_query() -> None:
    spoken = format_voice_answer(
        _CAUTION_CHUNK,
        "What's the intake manifold bolt torque?",
    )
    assert "15-18 foot-pounds" in spoken
    assert "ignition" not in spoken.lower()
    assert "caution" not in spoken.lower()


def test_format_voice_answer_includes_caution_when_asked() -> None:
    spoken = format_voice_answer(
        _CAUTION_CHUNK,
        "Any safety caution for intake bolts?",
    )
    assert "15-18 foot-pounds" in spoken
    assert "ignition" in spoken.lower() or "caution" in spoken.lower()


def test_infer_from_uploaded_catalog_only() -> None:
    make, model, year = _infer_vehicle_fields(
        "wrx drain plug torque", "", "", "", _DEMO_CATALOG
    )
    assert make == "subaru"
    assert model == "wrx"
    assert year == "2022"

    make, model, year = _infer_vehicle_fields(
        "2022 subaru wrx spark plugs", "", "", "", _DEMO_CATALOG
    )
    assert make == "subaru"
    assert model == "wrx"
    assert year == "2022"

    # Unknown platforms must not invent Subaru tags.
    make, model, year = _infer_vehicle_fields(
        "Ford F-150 specs", "", "", "", _DEMO_CATALOG
    )
    assert make == ""
    assert model == ""
    assert year == ""


def test_vehicle_fields_must_exist_in_catalog() -> None:
    assert _vehicle_fields_in_catalog(
        _DEMO_CATALOG, "2022", "subaru", "wrx"
    )
    assert not _vehicle_fields_in_catalog(_DEMO_CATALOG, "", "ford", "f150")
    assert not _vehicle_fields_in_catalog(
        _DEMO_CATALOG, "2022", "ford", "wrx"
    )
