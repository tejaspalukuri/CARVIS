"""Lexical safety gate used by search: part words must match, unloaded makes refuse."""

from main import ShopVehicleCatalog, _lexical_rank, _part_words, mentioned_unloaded_make

_WRX = ShopVehicleCatalog(
    makes=frozenset({"subaru"}),
    models=frozenset({"wrx"}),
    years=frozenset({"2022"}),
    triples=frozenset({("2022", "subaru", "wrx")}),
)

_WHEEL_NUT = (
    "| Application | Torque | Notes |\n| --- | --- | --- |\n"
    "| Wheel And Tire System (Installation), Tighten the wheel nuts to the specified torque "
    "| 120 newton-meters (12.2 kgf-m, 88.5 foot-pounds) | |"
)
_CAMBER = (
    "| Application | Torque | Notes |\n| --- | --- | --- |\n"
    "| Wheel Alignment (1. Camber (Front Wheel)), Tighten two new flange nuts "
    "| 155 newton-meters (15.8 kgf-m, 114.3 foot-pounds) | |"
)


def test_unloaded_make_is_detected() -> None:
    assert mentioned_unloaded_make("Ford F-150 head bolt torque", _WRX) == "ford"
    assert mentioned_unloaded_make("honda civic drain plug", _WRX) == "honda"
    assert mentioned_unloaded_make("chevy intake bolts", _WRX) == "chevrolet"
    assert mentioned_unloaded_make("2022 subaru wrx wheel nuts", _WRX) is None
    assert mentioned_unloaded_make("ram air intake duct", _WRX) is None


def test_part_words_drop_filler_and_vehicle_names() -> None:
    assert _part_words("what is the wheel nut torque for the subaru wrx", _WRX) == ["wheel", "nut"]
    assert _part_words("what's the torque spec?", _WRX) == []


def test_part_words_must_all_appear_and_adjacent_pairs_win() -> None:
    words = _part_words("wheel nut torque", _WRX)
    wheel_nut, camber = _lexical_rank(_WHEEL_NUT, words), _lexical_rank(_CAMBER, words)
    assert wheel_nut is not None and camber is not None
    assert wheel_nut > camber  # "wheel nuts" appear side by side only in the right chunk

    # A part the chunk never mentions is a refusal, not a near miss.
    assert _lexical_rank(_CAMBER, _part_words("caliper bolt torque", _WRX)) is None
    # Fastener words alone never satisfy the gate.
    assert _lexical_rank(_CAMBER, ["nut"]) is None
