from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Sequence, Union


DEFAULT_MARKERS: Sequence[str] = (
    "pyproject.toml",
    "setup.cfg",
    "setup.py",
    ".git",
    "src",
)


def find_repo_root(
    start: Optional[Union[str, Path]] = None,
    markers: Sequence[str] = DEFAULT_MARKERS,
) -> Path:
    """Find the repository root by walking upward until a marker is found.

    This is designed to make notebooks robust to being run from different
    working directories.

    Parameters
    ----------
    start:
        Starting path (file or directory). If None, uses current working directory.
    markers:
        File/directory names that indicate a repo root.

    Raises
    ------
    RuntimeError
        If no repo root can be found.
    """
    if start is None:
        p = Path.cwd().resolve()
    else:
        p = Path(start).resolve()

    if p.is_file():
        p = p.parent

    for parent in (p, *p.parents):
        for m in markers:
            if (parent / m).exists():
                return parent

    raise RuntimeError(
        "Could not find repository root. "
        "Run the notebook from within the repo or set REPO_ROOT manually."
    )


def ensure_src_on_path(repo_root: Union[str, Path]) -> Path:
    """Ensure <repo_root>/src is on sys.path and return that path."""
    repo_root = Path(repo_root).resolve()
    src_path = repo_root / "src"
    if not src_path.exists():
        raise FileNotFoundError(f"Expected src/ under repo root but not found: {src_path}")
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    return src_path


def resolve_path(path_like: Union[str, Path], repo_root: Optional[Union[str, Path]] = None) -> Path:
    """Resolve a path that may be absolute or repo-relative.

    If path_like is absolute, returns it as a Path.
    If path_like is relative, requires repo_root and resolves under it.
    """
    p = Path(path_like)
    if p.is_absolute():
        return p
    if repo_root is None:
        raise ValueError(f"Relative path '{path_like}' requires repo_root")
    return (Path(repo_root) / p).resolve()
