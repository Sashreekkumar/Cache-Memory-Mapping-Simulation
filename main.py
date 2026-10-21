import argparse

from cache_sim import Cache


def parse_args():
    p = argparse.ArgumentParser(description="Cache mapping simulator")
    p.add_argument("--mem", type=int, default=16 * 1024, help="main memory bytes")
    p.add_argument("--cache", type=int, default=1024, help="cache bytes")
    p.add_argument("--block", type=int, default=16, help="block size bytes")
    p.add_argument("--ways", type=int, default=1, help="1=direct, N=N-way, >=lines=fully assoc.")
    p.add_argument("--policy", default="LRU", choices=["LRU", "FIFO", "RANDOM"])
    p.add_argument("--write-policy", default="write-back", choices=["write-back", "write-through"])
    p.add_argument("--no-write-allocate", action="store_true")
    p.add_argument("--hit-time", type=float, default=1)
    p.add_argument("--miss-penalty", type=float, default=100)
    p.add_argument("--trace", help="file with lines like '1234' or 'W 1234'")
    p.add_argument("--workload", help="run a named workload instead of the demo trace")
    p.add_argument("--compare", action="store_true", help="hit ratio table: workloads x ways")
    p.add_argument("--plots", action="store_true", help="save plots to ./plots")
    return p.parse_args()


def load_trace(path):
    trace = []
    with open(path) as f:
        for line in f:
            parts = line.split("#")[0].split()
            if not parts:
                continue
            trace.append((int(parts[-1]), parts[0]) if len(parts) > 1 else (int(parts[0]), "R"))
    return trace


def print_config(c):
    print(f"Mode          : {c.mode} ({c.policy}, {c.write_policy}"
          f"{'' if c.write_allocate else ', no-write-allocate'})")
    print(f"Memory blocks : {c.mem_blocks}")
    print(f"Cache lines   : {c.lines}  ({c.num_sets} sets x {c.ways} ways)")
    print(f"Bits          : address {c.addr_bits} = tag {c.tag_bits} + "
          f"index {c.index_bits} + offset {c.offset_bits}\n")


def print_results(c, results, verbose=True):
    if verbose:
        hdr = f"{'Op':>2} {'Addr':>5} {'Tag|Index|Offset':>18} {'T':>3} {'I':>3} {'O':>3}  {'Result':<18} Evicted"
        print(hdr)
        print("-" * len(hdr))
        for r in results:
            b = format(r["addr"], f"0{c.addr_bits}b")
            t, i = c.tag_bits, c.index_bits
            spaced = "|".join(x for x in (b[:t], b[t:t + i], b[t + i:]) if x)
            ev = r["evicted"]
            ev_s = "" if not ev else f"blk {ev['block']}" + (" (write-back)" if ev["dirty"] else "")
            print(f"{r['op']:>2} {r['addr']:>5} {spaced:>18} {r['tag']:>3} {r['index']:>3} "
                  f"{r['offset']:>3}  {r['result']:<18} {ev_s}")
        print()
    s = c.stats()
    print(f"Accesses {s['accesses']} | Hits {s['hits']} | Misses {s['misses']} | "
          f"Hit ratio {s['hit_ratio']:.2%}")
    print(f"Misses: compulsory {s['compulsory']}, capacity {s['capacity']}, conflict {s['conflict']}")
    print(f"Memory reads {s['mem_reads']}, writes {s['mem_writes']}, write-backs {s['writebacks']}")
    print(f"AMAT = {c.hit_time:g} + {c.miss_rate:.3f} x {c.miss_penalty:g} = {s['amat']:.2f} cycles")


DEMO = [(1234, "R"), (1236, "R"), (2258, "W"), (1234, "R"),
        (0, "R"), (1024, "W"), (0, "R"), (5000, "R")]


def main():
    a = parse_args()
    cfg = dict(mem_size=a.mem, cache_size=a.cache, block_size=a.block, ways=a.ways,
               policy=a.policy, write_policy=a.write_policy,
               write_allocate=not a.no_write_allocate,
               hit_time=a.hit_time, miss_penalty=a.miss_penalty)

    if a.compare or a.plots:
        import analysis
        if a.compare:
            print(analysis.comparison_table(cfg))
        if a.plots:
            for path in analysis.all_plots(cfg):
                print("saved", path)
        return

    cache = Cache(**cfg)
    print_config(cache)
    if a.workload:
        from workloads import WORKLOADS
        trace, verbose = WORKLOADS[a.workload](), False
    elif a.trace:
        trace, verbose = load_trace(a.trace), True
    else:
        trace, verbose = DEMO, True
    results = cache.run(trace)
    print_results(cache, results, verbose)
    if verbose:
        print("\nFinal cache state:")
        print(cache.dump())


if __name__ == "__main__":
    main()
