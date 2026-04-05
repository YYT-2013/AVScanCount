import re
import shutil
import subprocess
import sys
import zipfile
import os
from pathlib import Path
from typing import Callable


ProgressCallback = Callable[[int, int, str], None]
ARCHIVE_EXTENSIONS = {".zip", ".rar", ".7z"}


def is_archive(path: Path) -> bool:
    return path.suffix.lower() in ARCHIVE_EXTENSIONS


def _safe_join(base_dir: Path, target_path: Path) -> Path:
    resolved_base = base_dir.resolve()
    resolved_target = target_path.resolve()
    if not str(resolved_target).startswith(str(resolved_base)):
        raise ValueError(f"Illegal archive path: {target_path}")
    return resolved_target


def _sanitize_folder_component(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return "UnknownAV"
    value = re.sub(r"[<>:\"/\\|?*]+", "_", value)
    return value.strip(" ._") or "UnknownAV"


def _make_extract_dir(archive_path: Path, antivirus_name: str, extract_root: Path | None = None) -> Path:
    safe_av = _sanitize_folder_component(antivirus_name)
    base_name = f"{archive_path.stem}_{safe_av}"
    parent = extract_root if extract_root else archive_path.parent
    parent.mkdir(parents=True, exist_ok=True)
    target = parent / base_name

    if not target.exists():
        target.mkdir(parents=True, exist_ok=True)
        return target

    idx = 1
    while True:
        candidate = parent / f"{base_name}_{idx:03d}"
        if not candidate.exists():
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
        idx += 1


def _extract_zip(
    archive_path: Path,
    dest_dir: Path,
    password: str | None,
    progress_callback: ProgressCallback | None,
) -> None:
    with zipfile.ZipFile(archive_path) as zf:
        members = zf.infolist()
        total = len(members)
        pwd = password.encode("utf-8") if password else None

        for i, member in enumerate(members, start=1):
            safe_target = _safe_join(dest_dir, dest_dir / member.filename)
            if progress_callback:
                progress_callback(i, total, member.filename)
            if member.is_dir():
                safe_target.mkdir(parents=True, exist_ok=True)
                continue
            safe_target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member, pwd=pwd) as src, safe_target.open("wb") as dst:
                shutil.copyfileobj(src, dst)


def _find_7z_executable() -> Path | None:
    candidates: list[Path] = [Path(__file__).resolve().parents[1] / "tools" / "7z.exe"]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "tools" / "7z.exe")

    for candidate in candidates:
        if candidate.exists():
            return candidate

    in_path = shutil.which("7z")
    return Path(in_path) if in_path else None


def _extract_7z_command(archive_path: Path, dest_dir: Path, password: str | None) -> None:
    seven_zip = _find_7z_executable()
    if not seven_zip:
        raise FileNotFoundError("未找到 7z，请把 7z.exe 放到 tools 目录，或加入系统 PATH。")

    threads = max(2, os.cpu_count() or 4)
    command = [str(seven_zip), "x", str(archive_path), f"-o{dest_dir}", "-y", f"-mmt={threads}"]
    if password:
        command.append(f"-p{password}")
    subprocess.run(command, check=True, capture_output=True, text=True)


def _extract_7z_or_rar_python(archive_path: Path, dest_dir: Path, password: str | None) -> None:
    suffix = archive_path.suffix.lower()
    if suffix == ".7z":
        import py7zr  # type: ignore

        with py7zr.SevenZipFile(archive_path, mode="r", password=password) as z:
            z.extractall(path=dest_dir)
        return

    if suffix == ".rar":
        import rarfile  # type: ignore

        with rarfile.RarFile(archive_path) as rf:
            if password:
                rf.setpassword(password)
            rf.extractall(path=dest_dir)


def prepare_target(
    source_path: Path,
    password: str | None = None,
    antivirus_name: str = "",
    extract_root: Path | None = None,
    progress_callback: ProgressCallback | None = None,
) -> tuple[Path, Path | None]:
    if source_path.is_dir():
        return source_path, None

    if not is_archive(source_path):
        raise ValueError("仅支持文件夹或 zip/rar/7z 压缩包。")

    extract_dir = _make_extract_dir(source_path, antivirus_name, extract_root=extract_root)
    try:
        suffix = source_path.suffix.lower()
        if suffix in {".zip", ".rar", ".7z"}:
            try:
                # 优先使用 7z 多线程解压，速度更快。
                _extract_7z_command(source_path, extract_dir, password)
            except Exception:
                # 回退到 Python 解压，保证兼容性。
                if suffix == ".zip":
                    _extract_zip(source_path, extract_dir, password, progress_callback)
                else:
                    _extract_7z_or_rar_python(source_path, extract_dir, password)
        else:
            raise ValueError("仅支持文件夹或 zip/rar/7z 压缩包。")
    except Exception:
        shutil.rmtree(extract_dir, ignore_errors=True)
        raise

    return extract_dir, extract_dir
