from __future__ import annotations


def evenly_sampled_indexes(item_count: int, limit: int) -> list[int]:
    sample_count = min(item_count, limit)
    if sample_count <= 0:
        return []
    if sample_count == 1:
        return [0]
    span = item_count - 1
    denominator = sample_count - 1
    return [
        (sample_index * span + denominator // 2) // denominator
        for sample_index in range(sample_count)
    ]
