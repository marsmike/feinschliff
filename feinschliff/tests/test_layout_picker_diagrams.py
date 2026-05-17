from __future__ import annotations

from lib.layout_picker import pick_layout


def test_diagram_kind_concept_picks_excalidraw():
    picks = pick_layout(diagram_kind="concept", concept_count=5)
    assert picks[0]["layout"] == "excalidraw-diagram"


def test_diagram_kind_chart_at_high_count_picks_full_svg_infographic():
    """At concept_count=11 the picker infers deep complexity and prefers the
    full-slide layout. The narrow `svg-infographic` is still picked when the
    caller explicitly asks for simple/medium complexity."""
    picks = pick_layout(
        diagram_kind="chart",
        concept_count=11,
        data_quantity=200,
    )
    assert picks[0]["layout"] == "svg-infographic-full"


def test_diagram_kind_chart_with_explicit_simple_picks_narrow():
    """Same shape as above but `diagram_complexity=simple` keeps the picker
    on the narrow svg-infographic."""
    picks = pick_layout(
        diagram_kind="chart",
        concept_count=11,
        data_quantity=200,
        diagram_complexity="simple",
    )
    assert picks[0]["layout"] == "svg-infographic"


def test_no_diagram_kind_leaves_existing_picker_unchanged():
    picks = pick_layout(
        role="data-comparison",
        concept_count=4,
        data_quantity=30,
        comparison=True,
    )
    assert picks[0]["layout"] == "bar-chart"


def test_narrative_role_system_boosts_excalidraw():
    picks = pick_layout(
        diagram_kind=None,
        concept_count=5,
        narrative_role="system",
    )
    layout_ids = [p["layout"] for p in picks[:3]]
    assert "excalidraw-diagram" in layout_ids


def test_diagram_complexity_deep_picks_full_layout():
    """Explicit `diagram_complexity=deep` routes to the full-slide layout
    even at modest concept counts where the narrow ideal_count would
    otherwise win."""
    picks = pick_layout(
        diagram_kind="concept",
        concept_count=6,
        diagram_complexity="deep",
    )
    assert picks[0]["layout"] == "excalidraw-diagram-full"


def test_diagram_complexity_inferred_deep_at_high_count():
    """Without explicit complexity, count>=8 infers deep and prefers full."""
    picks = pick_layout(
        diagram_kind="concept",
        concept_count=12,
    )
    assert picks[0]["layout"] == "excalidraw-diagram-full"


def test_diagram_complexity_simple_keeps_narrow_at_high_count():
    """Explicit simple beats the inferred-deep default even at count=12."""
    picks = pick_layout(
        diagram_kind="concept",
        concept_count=12,
        diagram_complexity="simple",
    )
    assert picks[0]["layout"] == "excalidraw-diagram"
