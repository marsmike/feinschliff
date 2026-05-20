from feinschliff.layout_picker import pick_layout


def test_negative_guidance_penalty_demotes_match(monkeypatch):
    fake_layouts = {
        "two-column-comparison": {
            "role": "comparison", "ideal_count": (2, 2),
            "when_not_to_use": ["narrative_role=closing"],
        },
        "single-statement": {
            "role": "closing", "ideal_count": (1, 1),
        },
    }
    monkeypatch.setattr("feinschliff.layout_picker._LAYOUTS", fake_layouts)

    ranked = pick_layout(
        role="closing",
        concept_count=2,
        narrative_role="closing",
        top_k=2,
    )
    ids = [r["layout"] for r in ranked]
    assert ids[0] == "single-statement"
    assert "negative-guidance" in " ".join(ranked[1]["rationale"])


def test_negative_guidance_no_match_no_penalty(monkeypatch):
    fake_layouts = {
        "two-column-comparison": {
            "role": "comparison", "ideal_count": (2, 2),
            "when_not_to_use": ["narrative_role=closing"],
        },
    }
    monkeypatch.setattr("feinschliff.layout_picker._LAYOUTS", fake_layouts)
    ranked = pick_layout(
        role="comparison",
        concept_count=2,
        narrative_role="problem",
        top_k=1,
    )
    assert "negative-guidance" not in " ".join(ranked[0]["rationale"])
