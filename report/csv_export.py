import csv
from pathlib import Path


def export_compare_records_csv(output_path: Path, antivirus_name: str, records: list[dict[str, str]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["antivirus", "path", "hash", "status", "status_cn"])
        for item in records:
            writer.writerow(
                [
                    antivirus_name,
                    item.get("path", ""),
                    item.get("hash", ""),
                    item.get("status", ""),
                    item.get("status_cn", ""),
                ]
            )
