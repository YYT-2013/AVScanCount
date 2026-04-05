from pathlib import Path
from typing import Callable

from core.hasher import HashAlgo, calculate_file_hash


ProgressCallback = Callable[[int, int, str], None]


def list_all_files(root_dir: Path) -> list[Path]:
    return [p for p in root_dir.rglob("*") if p.is_file()]


def build_snapshot(
    root_dir: Path,
    algorithm: HashAlgo = "md5",
    progress_callback: ProgressCallback | None = None,
) -> dict[str, dict[str, str]]:
    files = list_all_files(root_dir)
    total = len(files)
    snapshot: dict[str, dict[str, str]] = {}

    for i, file_path in enumerate(files, start=1):
        relative_path = str(file_path.relative_to(root_dir))
        if progress_callback:
            progress_callback(i, total, relative_path)
        try:
            file_hash = calculate_file_hash(file_path, algorithm=algorithm)
            snapshot[relative_path] = {"hash": file_hash, "abs_path": str(file_path)}
        except Exception:
            continue

    return snapshot
