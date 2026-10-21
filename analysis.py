"""Experiments and plots built on cache_sim + workloads."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from cache_sim import Cache
from workloads import WORKLOADS

OUT_DIR = "plots"
WAYS = [1, 2, 4, 8, 16, 64]          # 64 = fully associative for a 1 KB / 16 B cache


def run_workload(name, **cfg):
    c = Cache(**cfg)
    c.run(WORKLOADS[name]())
    return c


def _save(fig, name):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def _line_plot(xs, labels, series_fn, title, xlabel, fname):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for w in WORKLOADS:
        ax.plot(labels, [series_fn(w, x) * 100 for x in xs], marker="o", label=w)
    ax.set(title=title, xlabel=xlabel, ylabel="Hit ratio (%)", ylim=(-3, 103))
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    return _save(fig, fname)


def plot_associativity(cfg):
    labels = [str(w) if w < 64 else "64 (full)" for w in WAYS]
    return _line_plot(WAYS, labels,
                      lambda w, x: run_workload(w, **{**cfg, "ways": x}).hit_ratio,
                      "Hit ratio vs associativity", "Ways", "hit_vs_ways.png")


def plot_cache_size(cfg):
    sizes = [256, 512, 1024, 2048, 4096, 8192]
    return _line_plot(sizes, [str(s) for s in sizes],
                      lambda w, x: run_workload(w, **{**cfg, "cache_size": x}).hit_ratio,
                      "Hit ratio vs cache size", "Cache size (bytes)", "hit_vs_cache_size.png")


def plot_block_size(cfg):
    blocks = [4, 8, 16, 32, 64, 128]
    return _line_plot(blocks, [str(b) for b in blocks],
                      lambda w, x: run_workload(w, **{**cfg, "block_size": x}).hit_ratio,
                      "Hit ratio vs block size", "Block size (bytes)", "hit_vs_block_size.png")


def plot_miss_breakdown(cfg):
    names = list(WORKLOADS)
    caches = [run_workload(n, **cfg) for n in names]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bottom = [0] * len(names)
    for kind in ("compulsory", "capacity", "conflict"):
        vals = [c.miss_kinds[kind] / c.accesses * 100 for c in caches]
        ax.bar(names, vals, bottom=bottom, label=kind)
        bottom = [b + v for b, v in zip(bottom, vals)]
    ax.set(title=f"Miss breakdown ({caches[0].mode})", ylabel="% of accesses")
    ax.legend()
    plt.setp(ax.get_xticklabels(), rotation=20)
    return _save(fig, "miss_breakdown.png")


def all_plots(cfg):
    return [plot_associativity(cfg), plot_cache_size(cfg),
            plot_block_size(cfg), plot_miss_breakdown(cfg)]


def comparison_table(cfg):
    head = f"{'workload':<14}" + "".join(f"{('full' if w == 64 else str(w) + '-way'):>8}" for w in WAYS)
    rows = [head, "-" * len(head)]
    for name in WORKLOADS:
        vals = [run_workload(name, **{**cfg, "ways": w}).hit_ratio * 100 for w in WAYS]
        rows.append(f"{name:<14}" + "".join(f"{v:>7.1f}%" for v in vals))
    return "\n".join(rows)
