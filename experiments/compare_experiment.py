"""Compare separate chaining and linear probing under the same load."""

import csv
from pathlib import Path
from random import Random
import sys
from typing import NamedTuple


OUTPUT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(OUTPUT_DIR.parent))

from experiments.probe_experiment import (
    BUCKETS, MISS_QUERIES, SEED, PlotSeries, mean_comparisons, random_urls, write_cost_graph,
)
from src.hash_table import HashTable
from src.linear_probing import LinearProbingHashTable


LOADS = tuple(tenth / 10 for tenth in range(1, 10))


class Comparison(NamedTuple):
    target_load: float
    actual_load: float
    entries: int
    hit_queries: int
    miss_queries: int
    chaining_hit: float
    chaining_hit_theory: float
    chaining_miss: float
    chaining_miss_theory: float
    linear_hit: float
    linear_hit_theory: float
    linear_miss: float
    linear_miss_theory: float


def measure() -> list[Comparison]:
    generator = Random(SEED)
    stored = random_urls(generator, "stored", round(BUCKETS * LOADS[-1]))
    missing = random_urls(generator, "missing", MISS_QUERIES)
    chained = HashTable[int](capacity=BUCKETS, max_load=None)
    linear = LinearProbingHashTable[int](capacity=BUCKETS, max_load=None)
    results = []

    for target_load in LOADS:
        entries = round(target_load * BUCKETS)
        for index in range(len(chained), entries):
            key = stored[index]
            chained.put(key, index)
            linear.put(key, index)

        load = chained.load_factor
        stored_keys = stored[:entries]
        empty_fraction = 1 - load
        results.append(Comparison(
            target_load=target_load,
            actual_load=load,
            entries=entries,
            hit_queries=len(stored_keys),
            miss_queries=len(missing),
            chaining_hit=mean_comparisons(chained, stored_keys, present=True),
            chaining_hit_theory=1 + load / 2,
            chaining_miss=mean_comparisons(chained, missing, present=False),
            chaining_miss_theory=load,
            linear_hit=mean_comparisons(linear, stored_keys, present=True),
            linear_hit_theory=(1 + 1 / empty_fraction) / 2,
            linear_miss=mean_comparisons(linear, missing, present=False),
            linear_miss_theory=(1 + 1 / empty_fraction**2) / 2,
        ))
    return results


def write_graph(rows: list[Comparison]) -> None:
    series = []
    for field, label, color in (
        ("chaining_hit", "Chaining hit", "#00599c"),
        ("chaining_miss", "Chaining miss", "#287251"),
        ("linear_hit", "Linear probing hit", "#a04316"),
        ("linear_miss", "Linear probing miss", "#702a87"),
    ):
        series.append(PlotSeries(f"{label} · measured", color, False,
                                 [(row.actual_load, getattr(row, field)) for row in rows]))
        series.append(PlotSeries(f"{label} · theory", color, True,
                                 [(row.actual_load, getattr(row, f"{field}_theory")) for row in rows]))

    write_cost_graph(
        OUTPUT_DIR / "comparison.svg",
        title="Chaining and linear probing lookup costs",
        description=("Measured and theoretical successful and unsuccessful lookup costs "
                     "at load factors 0.1 through 0.9. The vertical scale is logarithmic."),
        subtitle=f"{BUCKETS:,} slots per table · Same keys and lookups · Seed {SEED}",
        y_label="Nodes compared or slots probed (log scale)",
        x_ticks=(0, *LOADS),
        y_ticks=(0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100),
        series=tuple(series),
        log_scale=True,
    )


def main() -> None:
    rows = measure()
    with (OUTPUT_DIR / "comparison.csv").open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(Comparison._fields)
        writer.writerows(rows)
    write_graph(rows)

    print(f"Same {BUCKETS} slots, seed {SEED}, {MISS_QUERIES} shared misses per load")
    print(" Load  Chain hit/theory  Chain miss/theory  Linear hit/theory  Linear miss/theory")
    for row in rows:
        print(f"{row.actual_load:5.2f}  "
              f"{row.chaining_hit:6.3f}/{row.chaining_hit_theory:6.3f}  "
              f"{row.chaining_miss:7.3f}/{row.chaining_miss_theory:6.3f}  "
              f"{row.linear_hit:8.3f}/{row.linear_hit_theory:6.3f}  "
              f"{row.linear_miss:9.3f}/{row.linear_miss_theory:7.3f}")


if __name__ == "__main__":
    main()
