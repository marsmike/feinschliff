from feinblick.runner import RawOutput, Runner


def test_run_captures_nonzero_without_raising(tmp_path):
    r = Runner(repo_root=tmp_path, cache=False)
    out = r.run_raw(["sh", "-c", "printf '{\"k\":1}'; exit 1"])  # findings-present analogue
    assert isinstance(out, RawOutput)
    assert out.exit_code == 1 and out.stdout == '{"k":1}'


def test_availability_true_for_present_tool(tmp_path):
    r = Runner(repo_root=tmp_path, cache=False)
    assert r.tool_available("sh") is True
    assert r.tool_available("definitely-not-a-real-binary-xyz") is False


def test_cache_hit_skips_recompute(tmp_path):
    counter = tmp_path / "n"
    counter.write_text("")
    r = Runner(repo_root=tmp_path, cache=True)
    argv = ["sh", "-c", f"printf x >> {counter}; printf hello"]
    a = r.run_raw(argv, cache_key="k1", inputs=[counter])
    b = r.run_raw(argv, cache_key="k1", inputs=[counter])
    assert a.stdout == b.stdout == "hello"
    assert counter.read_text() == "x"  # command ran exactly once (2nd was cached)
