"""Managed subprocess execution for engine adapters."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RawOutput:
    stdout: str
    stderr: str
    exit_code: int


class Runner:
    def __init__(self, repo_root: Path, cache: bool = True, timeout: int = 600):
        self.repo_root = Path(repo_root)
        self.cache_enabled = cache
        self.timeout = timeout
        self._cache_dir = self.repo_root / ".feinblick" / "cache"

    def tool_available(self, name: str) -> bool:
        return shutil.which(name) is not None

    def uvx(self, pkg: str, version: str, args: list[str]) -> list[str]:
        spec = pkg if version in ("", "latest") else f"{pkg}@{version}"
        return ["uvx", spec, *args]

    def npx(self, pkg: str, version: str, args: list[str]) -> list[str]:
        spec = pkg if version in ("", "latest") else f"{pkg}@{version}"
        return ["npx", "-y", spec, *args]

    def run_raw(self, argv: list[str], cache_key: str | None = None,
                inputs: list[Path] | None = None, cwd: Path | None = None) -> RawOutput:
        caching = self.cache_enabled and cache_key is not None
        inputs = inputs or []
        if caching:
            hit = self._read_cache(self._key(argv, cache_key, inputs))
            if hit is not None:
                return hit
        try:
            proc = subprocess.run(argv, capture_output=True, text=True,
                                  timeout=self.timeout, cwd=str(cwd) if cwd else None)
            out = RawOutput(proc.stdout, proc.stderr, proc.returncode)
        except FileNotFoundError as e:
            out = RawOutput("", f"command not found: {argv[0]} ({e})", 127)
        except subprocess.TimeoutExpired as e:
            out = RawOutput(e.stdout or "", f"timeout after {self.timeout}s", 124)
        if caching:
            # Key on the post-run input state so a re-invocation with identical
            # inputs hits the cache. For read-only engines this equals the
            # pre-run key; it only differs when the command mutates its inputs.
            self._write_cache(self._key(argv, cache_key, inputs), out)
        return out

    def _key(self, argv, cache_key, inputs):
        h = hashlib.sha1()
        h.update("\x00".join(argv).encode())
        h.update(cache_key.encode())
        for p in sorted(inputs, key=str):
            try:
                st = Path(p).stat()
                h.update(f"{p}:{st.st_mtime_ns}:{st.st_size}".encode())
            except OSError:
                h.update(f"{p}:missing".encode())
        return h.hexdigest()

    def _read_cache(self, key):
        f = self._cache_dir / f"{key}.json"
        if not f.is_file():
            return None
        d = json.loads(f.read_text())
        return RawOutput(d["stdout"], d["stderr"], d["exit_code"])

    def _write_cache(self, key, out):
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        (self._cache_dir / f"{key}.json").write_text(
            json.dumps({"stdout": out.stdout, "stderr": out.stderr, "exit_code": out.exit_code}))
