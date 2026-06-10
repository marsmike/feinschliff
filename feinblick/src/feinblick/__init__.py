"""feinblick — codebase intelligence for the feinschmiede plugin family.

The public surface is the console CLI (`feinblick`), not the modules: other
plugins and CI call the bare command, never import or path into us.
"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

try:  # single source of truth = the installed package metadata (pyproject)
    __version__ = _pkg_version("feinblick")
except PackageNotFoundError:  # running from a source tree without an install
    __version__ = "0.0.0+dev"
