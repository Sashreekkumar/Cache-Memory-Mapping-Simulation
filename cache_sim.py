"""Configurable cache simulator: direct-mapped, set-associative, fully associative."""
import math
import random
from collections import OrderedDict


def _log2(x, name):
    if x <= 0 or x & (x - 1):
        raise ValueError(f"{name} must be a power of two, got {x}")
    return int(math.log2(x))


class Cache:
    def __init__(self, mem_size=16 * 1024, cache_size=1024, block_size=16,
                 ways=1, policy="LRU", write_policy="write-back",
                 write_allocate=True, hit_time=1, miss_penalty=100, seed=0):
        self.mem_size = mem_size
        self.cache_size = cache_size
        self.block_size = block_size
        self.mem_blocks = mem_size // block_size
        self.lines = cache_size // block_size
        self.ways = min(ways, self.lines)          # ways >= lines -> fully associative
        self.num_sets = self.lines // self.ways
        self.policy = policy.upper()
        self.write_policy = write_policy.lower()
        self.write_allocate = write_allocate
        self.hit_time = hit_time
        self.miss_penalty = miss_penalty
        self.seed = seed

        if self.policy not in ("LRU", "FIFO", "RANDOM"):
            raise ValueError("policy must be LRU, FIFO or RANDOM")
        if self.write_policy not in ("write-back", "write-through"):
            raise ValueError("write_policy must be write-back or write-through")

        self.addr_bits = _log2(mem_size, "mem_size")
        self.offset_bits = _log2(block_size, "block_size")
        _log2(self.ways, "ways")
        self.index_bits = _log2(self.num_sets, "number of sets")
        self.tag_bits = self.addr_bits - self.index_bits - self.offset_bits
        self.reset()

    # ---------- setup ----------
    def reset(self):
        self.sets = [[] for _ in range(self.num_sets)]   # each line: {"tag", "dirty"}
        self.rng = random.Random(self.seed)
        self.seen = set()                                # blocks ever referenced
        self.shadow = OrderedDict()                      # fully-assoc LRU of same size
        self.accesses = self.hits = self.misses = 0
        self.miss_kinds = {"compulsory": 0, "capacity": 0, "conflict": 0}
        self.mem_reads = self.mem_writes = self.writebacks = 0

    @property
    def mode(self):
        if self.ways == 1:
            return "direct-mapped"
        if self.num_sets == 1:
            return "fully associative"
        return f"{self.ways}-way set-associative"

    # ---------- address handling ----------
    def split(self, addr):
        offset = addr & ((1 << self.offset_bits) - 1)
        index = (addr >> self.offset_bits) & ((1 << self.index_bits) - 1)
        tag = addr >> (self.offset_bits + self.index_bits)
        return tag, index, offset

    # ---------- internals ----------
    def _touch_shadow(self, block):
        present = block in self.shadow
        if present:
            self.shadow.move_to_end(block)
        else:
            self.shadow[block] = True
            if len(self.shadow) > self.lines:
                self.shadow.popitem(last=False)
        return present

    def _write_hit(self, line):
        if self.write_policy == "write-back":
            line["dirty"] = True
        else:
            self.mem_writes += 1

    def _evict(self, s, index):
        i = self.rng.randrange(len(s)) if self.policy == "RANDOM" else 0
        victim = s.pop(i)                  # LRU/FIFO: front of list is the victim
        if victim["dirty"]:
            self.writebacks += 1
            self.mem_writes += 1
        block = (victim["tag"] << self.index_bits) | index
        return {"block": block, "dirty": victim["dirty"]}

    # ---------- main access ----------
    def access(self, addr, op="R"):
        if not 0 <= addr < self.mem_size:
            raise ValueError(f"address {addr} outside memory (0..{self.mem_size - 1})")
        op = op.upper()
        tag, index, offset = self.split(addr)
        block = addr >> self.offset_bits
        s = self.sets[index]
        line = next((l for l in s if l["tag"] == tag), None)

        shadow_hit = self._touch_shadow(block)
        first_time = block not in self.seen
        self.seen.add(block)
        self.accesses += 1
        evicted = None

        if line:
            self.hits += 1
            result = "HIT"
            if self.policy == "LRU":
                s.remove(line)
                s.append(line)
            if op == "W":
                self._write_hit(line)
        else:
            self.misses += 1
            kind = "compulsory" if first_time else ("conflict" if shadow_hit else "capacity")
            self.miss_kinds[kind] += 1
            result = f"MISS ({kind})"
            if op == "W" and not self.write_allocate:
                self.mem_writes += 1
            else:
                self.mem_reads += 1
                if len(s) >= self.ways:
                    evicted = self._evict(s, index)
                line = {"tag": tag, "dirty": False}
                s.append(line)
                if op == "W":
                    self._write_hit(line)

        return {"addr": addr, "op": op, "tag": tag, "index": index,
                "offset": offset, "result": result, "evicted": evicted}

    def run(self, trace):
        """trace: iterable of addresses or (addr, 'R'/'W') tuples."""
        out = []
        for item in trace:
            addr, op = item if isinstance(item, tuple) else (item, "R")
            out.append(self.access(addr, op))
        return out

    # ---------- statistics ----------
    @property
    def hit_ratio(self):
        return self.hits / self.accesses if self.accesses else 0.0

    @property
    def miss_rate(self):
        return 1 - self.hit_ratio if self.accesses else 0.0

    @property
    def amat(self):
        """Average memory access time = hit time + miss rate * miss penalty."""
        return self.hit_time + self.miss_rate * self.miss_penalty

    def stats(self):
        return {"mode": self.mode, "accesses": self.accesses, "hits": self.hits,
                "misses": self.misses, "hit_ratio": self.hit_ratio,
                **self.miss_kinds, "writebacks": self.writebacks,
                "mem_reads": self.mem_reads, "mem_writes": self.mem_writes,
                "amat": self.amat}

    def dump(self):
        """Text view of occupied sets (tag, D = dirty)."""
        rows = []
        for i, s in enumerate(self.sets):
            if s:
                cells = " ".join(f"[tag={l['tag']}{' D' if l['dirty'] else ''}]" for l in s)
                rows.append(f"set {i:>3}: {cells}")
        return "\n".join(rows) if rows else "(cache empty)"
