"""feinbild — image / 2D (AI images, SVG, Excalidraw) for the feinschmiede family.

The public surface is the `feinbild` console CLI, not these modules.
"""

from importlib.metadata import PackageNotFoundError, version as _pkg_version

try:  # single source of truth = the installed package metadata (pyproject)
    __version__ = _pkg_version("feinbild")
except PackageNotFoundError:  # running from a source tree without an install
    __version__ = "0.0.0+dev"
