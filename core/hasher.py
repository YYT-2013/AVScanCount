import hashlib
from pathlib import Path
from typing import Literal


HashAlgo = Literal["md5", "sha1", "sha256"]


def calculate_file_hash(file_path: Path, algorithm: HashAlgo = "md5", chunk_size: int = 1024 * 1024) -> str:
    hasher = hashlib.new(algorithm)
    with file_path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()
