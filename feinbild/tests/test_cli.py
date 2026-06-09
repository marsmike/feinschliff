import pytest

from feinbild import cli


def test_version(capsys):
    with pytest.raises(SystemExit) as e:
        cli.main(["--version"])
    assert e.value.code == 0
    assert "feinbild" in capsys.readouterr().out


def test_imagine_unknown_provider_exits_1(capsys):
    rc = cli.main(["imagine", "--prompt", "x", "--provider", "nope"])
    assert rc == 1
    assert "Unknown provider" in capsys.readouterr().err


def test_svg_subcommands_parse():
    parser = cli.build_parser()
    args = parser.parse_args(["svg", "expand", "chart.svg.dsl", "--brand", "feinschliff"])
    assert args.command == "svg" and args.sub == "expand"
