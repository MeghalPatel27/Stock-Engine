"""Stock Intelligence Engine — production package (no business logic in V0.1 scaffold)."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("stock-engine")
except PackageNotFoundError:  # pragma: no cover - editable/uninstalled
    __version__ = "0.1.0"

__all__ = ["__version__"]
