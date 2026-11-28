"""Measure successful and unsuccessful lookups in a chained hash table."""

import csv
import math
from pathlib import Path
import random
import sys
from typing import NamedTuple


OUTPUT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(OUTPUT_DIR.parent))

from src.hash_table import HashTable


BUCKETS = 4093
SEED = 2026
MISS_QUERIES = 2000
LOADS = tuple(quarter / 4 for quarter in range(1, 17))


class Measurement(NamedTuple):
    target_load: float
    actual_load: float
    entries: int
    hit_queries: int
    miss_queries: int
    hit_mean: float
    hit_theory: float
    miss_mean: float
    miss_theory: float


def random_urls(generator: random.Random, group: str, count: int) -> list[str]:
    return [
        f"https://example.com/{group}/{generator.getrandbits(96):024x}-{index}"
        for index in range(count)
    ]


def mean_comparisons(table: HashTable[int], keys: list[str], *, present: bool) -> float:
    total = 0
    for key in keys:
        found, _, comparisons = table.find(key)
        if found != present:
            raise RuntimeError(f"unexpected lookup result for {key}")
        total += comparisons
    return total / len(keys)


def measure() -> list[Measurement]:
    generator = random.Random(SEED)
    stored = random_urls(generator, "stored", round(BUCKETS * LOADS[-1]))
    missing = random_urls(generator, "missing", MISS_QUERIES)
    table = HashTable[int](capacity=BUCKETS, max_load=None)
    results = []

    for target_load in LOADS:
        entries = round(target_load * BUCKETS)
        for index in range(len(table), entries):
            table.put(stored[index], index)

        actual_load = table.load_factor
        results.append(Measurement(
            target_load=target_load,
            actual_load=actual_load,
            entries=entries,
            hit_queries=entries,
            miss_queries=len(missing),
            hit_mean=mean_comparisons(table, stored[:entries], present=True),
            hit_theory=1 + actual_load / 2,
            miss_mean=mean_comparisons(table, missing, present=False),
            miss_theory=actual_load,
        ))
    return results


def write_graph(rows: list[Measurement], destination: Path) -> None:
    width, height = 960, 540
    left, right, top, bottom = 100, 920, 96, 410
    y_max = 1 + math.ceil(max(
        max(row.hit_mean, row.hit_theory, row.miss_mean, row.miss_theory)
        for row in rows
    ))

    def x(load: float) -> float:
        return left + (right - left) * load / LOADS[-1]

    def y(cost: float) -> float:
        return bottom - (bottom - top) * cost / y_max

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        'role="img" aria-labelledby="title description">',
        '<title id="title">Lookup cost in separate chaining</title>',
        '<desc id="description">Measured and theoretical node comparisons for '
        'successful and unsuccessful searches at load factors 0.25 through 4.</desc>',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        '<g font-family="system-ui, sans-serif" fill="#152337">',
        '<text x="100" y="44" font-size="27" font-weight="bold">'
        'Lookup cost in separate chaining</text>',
        '<text x="100" y="70" font-size="15">'
        f'{BUCKETS:,} fixed buckets · Seed {SEED} · {MISS_QUERIES:,} unsuccessful lookups per load</text>',
    ]

    for tick in range(y_max + 1):
        position = y(tick)
        svg.append(f'<line x1="{left}" y1="{position:.2f}" x2="{right}" '
                   f'y2="{position:.2f}" stroke="#dce3ea"/>')
        svg.append(f'<text x="{left - 12}" y="{position + 5:.2f}" '
                   f'text-anchor="end" font-size="14">{tick}</text>')

    for half in range(9):
        tick = half / 2
        position = x(tick)
        svg.append(f'<line x1="{position:.2f}" y1="{bottom}" x2="{position:.2f}" '
                   f'y2="{bottom + 6}" stroke="#536479"/>')
        svg.append(f'<text x="{position:.2f}" y="{bottom + 25}" '
                   f'text-anchor="middle" font-size="14">{tick:g}</text>')

    svg += [
        f'<path d="M {left} {top} V {bottom} H {right}" fill="none" stroke="#536479"/>',
        f'<text x="{(left + right) / 2:.0f}" y="{bottom + 55}" '
        'text-anchor="middle" font-size="16">Load factor (α)</text>',
        f'<text x="31" y="{(top + bottom) / 2:.0f}" transform="rotate(-90 31 {(top + bottom) / 2:.0f})" '
        'text-anchor="middle" font-size="16">Mean nodes compared</text>',
    ]

    series = (
        ("Successful · measured", "hit_mean", "#00599c", False),
        ("Successful · theory", "hit_theory", "#00599c", True),
        ("Unsuccessful · measured", "miss_mean", "#a04316", False),
        ("Unsuccessful · theory", "miss_theory", "#a04316", True),
    )
    for index, (label, field, color, theoretical) in enumerate(series):
        points = [(x(row.actual_load), y(getattr(row, field))) for row in rows]
        point_text = " ".join(f"{px:.2f},{py:.2f}" for px, py in points)
        dash = ' stroke-dasharray="7 5"' if theoretical else ""
        svg.append(f'<polyline points="{point_text}" fill="none" stroke="{color}" '
                   f'stroke-width="2"{dash}/>')
        if not theoretical:
            for px, py in points:
                svg.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="3" fill="{color}"/>')

        legend_x = left + (index % 2) * 380
        legend_y = 493 + (index // 2) * 23
        svg.append(f'<path d="M {legend_x} {legend_y} h 26" stroke="{color}" '
                   f'stroke-width="2"{dash}/>')
        svg.append(f'<text x="{legend_x + 34}" y="{legend_y + 5}" font-size="14">{label}</text>')

    svg += ["</g>", "</svg>"]
    destination.write_text("\n".join(svg) + "\n", encoding="utf-8")


def main() -> None:
    rows = measure()
    with (OUTPUT_DIR / "results.csv").open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(Measurement._fields)
        writer.writerows(rows)
    write_graph(rows, OUTPUT_DIR / "probe_costs.svg")

    print(f"Separate chaining: {BUCKETS} fixed buckets, seed {SEED}, "
          f"{MISS_QUERIES} unsuccessful lookups per load")
    print(f"{'Load':>7} {'Entries':>8} {'Hit mean':>10} {'Hit theory':>11} "
          f"{'Miss mean':>10} {'Miss theory':>12}")
    for row in rows:
        print(f"{row.actual_load:7.3f} {row.entries:8} {row.hit_mean:10.3f} "
              f"{row.hit_theory:11.3f} {row.miss_mean:10.3f} {row.miss_theory:12.3f}")


if __name__ == "__main__":
    main()
