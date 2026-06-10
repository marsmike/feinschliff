"""feinklang — ElevenLabs voiceover for the feinschmiede plugin family.

The public surface of this package is its console CLI (`feinklang`), not its
modules: other plugins call the bare command, never import or path into us.
"""

from importlib.metadata import PackageNotFoundError, version as _pkg_version

try:  # single source of truth = the installed package metadata (pyproject)
    __version__ = _pkg_version("feinklang")
except PackageNotFoundError:  # running from a source tree without an install
    __version__ = "0.0.0+dev"
