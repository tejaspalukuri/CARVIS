"""Chunking of LlamaParse v2 output for procedure-style manuals (e.g. Subaru FSM)."""

from ingest import _units_agree, collect_spec_chunks, expand_mechanical_units

_STEP_PAGE = """FUEL INJECTION (FUEL SYSTEMS)(H4DOTC) > Throttle Body

# INSTALLATION

**1.** Set a new gasket, and install the throttle body together with the throttle body stay.

**Tightening torque:**
8 N·m (0.8 kgf-m, 5.9 ft-lb)

**2.** Connect the preheater hose (B). <u>Ref. to COOLING(H4DOTC)>Engine Coolant>REPLACEMENT.</u>
"""

_CALLOUT_PAGE = """# FUEL INJECTION (FUEL SYSTEMS)(H4DOTC) > General Description

# **1. INTAKE MANIFOLD ASSEMBLY**

**Tightening torque: N·m (kgf-m, ft-lb)**
T1: 3.4 (0.3, 2.5)
T2: 25 (2.5, 18.4)

# **11. FUEL LINE 2**

**Tightening torque: N·m (kgf-m, ft-lb)**
**T: 8 (0.8, 5.9)**
"""


def _chunks(markdown: str):
    return collect_spec_chunks(expand_mechanical_units(markdown))


def test_procedure_step_torque_becomes_one_chunk() -> None:
    chunks = _chunks(_STEP_PAGE)
    assert len(chunks) == 1
    text = chunks[0].text
    assert "Throttle Body (Installation), Set a new gasket" in text
    assert "8 newton-meters (0.8 kgf-m, 5.9 foot-pounds)" in text
    assert chunks[0].section == "FUEL INJECTION (FUEL SYSTEMS)(H4DOTC) > Throttle Body"


def test_numbered_diagram_callouts_are_skipped_but_single_t_is_kept() -> None:
    chunks = _chunks(_CALLOUT_PAGE)
    texts = "\n".join(chunk.text for chunk in chunks)
    # T1/T2 depend on the diagram, so they must not become answers.
    assert "3.4 newton-meters" not in texts
    assert "25 newton-meters" not in texts
    # A single "T" applies to every marked fastener, so it is unambiguous.
    assert "8 newton-meters (0.8 kgf-m, 5.9 foot-pounds)" in texts
    assert "every fastener marked T" in texts


def test_inconsistent_units_are_rejected_as_possible_ocr_errors() -> None:
    assert _units_agree("8 newton-meters (0.8 kgf-m, 5.9 foot-pounds)")
    assert _units_agree("25 newton-meters (2.5 kgf-m, 18.4 foot-pounds)")
    assert not _units_agree("85 newton-meters (0.8 kgf-m, 5.9 foot-pounds)")

    misread = _STEP_PAGE.replace("8 N·m (0.8", "85 N·m (0.8")
    assert _chunks(misread) == []
