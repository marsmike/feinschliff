import pytest

from feinschliff.jsonwalk import walk


def test_walk_single_key():
    assert walk({"a": 1}, "a") == 1


def test_walk_dotted_path():
    assert walk({"a": {"b": {"c": 42}}}, "a.b.c") == 42


def test_walk_missing_key_returns_none():
    assert walk({"a": {}}, "a.b") is None


def test_walk_empty_path_returns_input():
    assert walk({"a": 1}, "") == {"a": 1}


def test_walk_rejects_array_indices():
    with pytest.raises(ValueError, match="array indices not supported"):
        walk({"a": [1, 2]}, "a.0")


def test_walk_through_non_dict_returns_none():
    assert walk({"a": "string"}, "a.b") is None
