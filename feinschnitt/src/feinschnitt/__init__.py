"""feinschnitt — video plugin for the feinschmiede family.

The public surface is the `feinschnitt` console CLI (see cli.py), not these
modules. Imported by the bin/feinschnitt launcher's venv.
"""

from importlib.metadata import PackageNotFoundError, version as _pkg_version

try:  # single source of truth = the installed package metadata (pyproject)
    __version__ = _pkg_version("feinschnitt")
except PackageNotFoundError:  # running from a source tree without an install
    __version__ = "0.0.0+dev"
