import pytest

from feinbild import images


def test_unknown_provider_raises():
    with pytest.raises(images.ImagineError):
        images.generate(prompt="x", provider="nope", model=None, aspect_ratio="1:1", out_path=None, api_keys={})


def test_replicate_requires_key():
    with pytest.raises(images.ImagineError) as e:
        images.generate(prompt="x", provider="replicate", model=None, aspect_ratio="1:1", out_path=None, api_keys={})
    assert "REPLICATE_API_KEY" in str(e.value)


def test_default_models():
    assert images.default_model("replicate") == "black-forest-labs/flux-schnell"
    assert images.default_model("gemini") == "gemini-2.5-flash-image"
