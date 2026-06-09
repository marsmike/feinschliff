from feinblick.config import Config, load_config


def test_zero_config_defaults(tmp_path):
    cfg = load_config(tmp_path)                       # no feinblick.toml
    assert isinstance(cfg, Config)
    assert cfg.code.roots == ["feinschmiede/feinschmiede"]
    assert cfg.code.engines == ["cytoscnpy", "tach"]
    assert cfg.skills.engines == ["agnix"]
    assert cfg.skills.skill_md_max_lines == 500
    assert cfg.gate.fail_on == ["error"]
    assert cfg.gate.tolerance == 0
    assert cfg.engine_version("cytoscnpy") == "1.2.23"
    assert cfg.engine_version("tach") == "0.35.0"


def test_overrides_from_toml(tmp_path):
    (tmp_path / "feinblick.toml").write_text(
        '[code]\nroots=["src","lib"]\nengines=["cytoscnpy"]\n'
        '[skills]\nskill_md_max_lines=300\n'
        '[gate]\ntolerance=5\nfail_on=["error","warning"]\n'
        '[engines.cytoscnpy]\nversion="9.9.9"\n')
    cfg = load_config(tmp_path)
    assert cfg.code.roots == ["src", "lib"] and cfg.code.engines == ["cytoscnpy"]
    assert cfg.skills.skill_md_max_lines == 300
    assert cfg.gate.tolerance == 5 and cfg.gate.fail_on == ["error", "warning"]
    assert cfg.engine_version("cytoscnpy") == "9.9.9"   # override
    assert cfg.engine_version("tach") == "0.35.0"       # still default


def test_invalid_engine_name_raises(tmp_path):
    (tmp_path / "feinblick.toml").write_text('[code]\nengines=["nope"]\n')
    import pytest
    with pytest.raises(ValueError, match="unknown engine"):
        load_config(tmp_path)
