from dataclasses import dataclass


@dataclass
class CompareResult:
    total: int
    removed: int
    remaining: int
    removed_rate: float
    records: list[dict[str, str]]


def compare_snapshots(
    before_snapshot: dict[str, dict[str, str]],
    after_snapshot: dict[str, dict[str, str]],
) -> CompareResult:
    total = len(before_snapshot)
    removed_count = 0
    records: list[dict[str, str]] = []

    for rel_path, before_item in before_snapshot.items():
        before_hash = before_item["hash"]
        removed = True

        after_item = after_snapshot.get(rel_path)
        if after_item and after_item.get("hash") == before_hash:
            removed = False

        status_cn = "已查杀" if removed else "未查杀"
        status_en = "removed" if removed else "remaining"
        if removed:
            removed_count += 1

        records.append(
            {
                "path": rel_path,
                "hash": before_hash,
                "status": status_en,
                "status_cn": status_cn,
            }
        )

    remaining = total - removed_count
    removed_rate = (removed_count / total * 100) if total else 0.0

    return CompareResult(
        total=total,
        removed=removed_count,
        remaining=remaining,
        removed_rate=removed_rate,
        records=records,
    )
