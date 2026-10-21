# Cache Memory Mapping Simulator

A Python simulator for **CAMP: Direct Mapping of Cache Memory**, extended to also cover set-associative and fully associative caches, replacement and write policies, miss classification, and performance (AMAT) analysis.

---

## 1. What the project does

### The scenario
A processor has:

| Parameter | Value |
|---|---|
| Main memory | 16 KB |
| Cache memory | 1 KB |
| Block size | 16 bytes |

### The assignment tasks and their answers

| Task | Answer |
|---|---|
| Blocks in main memory | 16 KB / 16 B = **1024** (2¹⁰) |
| Cache blocks (lines) | 1 KB / 16 B = **64** (2⁶) |
| Address bits | **14** (16 KB = 2¹⁴) |
| Block offset bits | **4** (16 B = 2⁴) |
| Cache index bits | **6** (64 lines = 2⁶) |
| Tag bits | 14 − 6 − 4 = **4** |

Layout of the 14-bit address:

```
| Tag (4) | Index (6) | Offset (4) |
```

### How direct mapping works
Every main-memory block can live in exactly **one** cache line:

- block number = address / 16
- cache line = block number mod 64 (the index bits)
- tag = block number / 64 (says *which* of the 16 candidate blocks is in the line)

Since 1024 / 64 = 16, each cache line is shared by 16 memory blocks (blocks 0, 64, 128, … all go to line 0). On an access the cache uses the index to find the line, then compares the stored tag with the address tag:

- tag matches and the line is valid → **hit**
- otherwise → **miss**; the block is loaded and replaces whatever was there

### Worked example: address 1234
- Binary (14 bits): `0001 | 001101 | 0010`
- Tag = 1, Index = 13, Offset = 2
- Block number 1234 / 16 = 77, and 77 mod 64 = 13, 77 / 64 = 1 (both agree with the bit split)

Address 2258 also maps to line 13 but with tag 2, so 1234 and 2258 keep evicting each other. This is a **conflict miss**, the main weakness of direct mapping.

### What the extensions add
Beyond the assignment, the simulator lets you run real access traces and compare designs:

- **Associativity:** direct-mapped (1-way), 2/4/8/16-way, and fully associative. More ways means a block has more places to go, so fewer conflict misses.
- **Replacement policies:** LRU, FIFO, Random (choosing which line to evict in a set).
- **Write policies:** write-back (dirty bit, write to memory only on eviction) vs write-through; write-allocate on or off.
- **Miss classification:**
  - *Compulsory:* first ever access to a block.
  - *Capacity:* the cache is simply too small, so even a fully associative cache of the same size would miss.
  - *Conflict:* the block was evicted only because of the mapping restriction; a fully associative cache would have hit.
- **AMAT:** Average Memory Access Time = hit time + miss rate × miss penalty (defaults: 1 and 100 cycles).
- **Workloads:** realistic address patterns that expose different cache behaviours.

---

## 2. What each code file does

| File | Role |
|---|---|
| `cache_sim.py` | The core. The `Cache` class splits addresses into tag/index/offset, handles hits, misses, replacement and writes, and tracks all statistics. Everything else builds on it. |
| `workloads.py` | Generates address traces: `sequential`, `strided_1024`, `random`, `two_arrays`, `matrix_row`, `matrix_col`. |
| `analysis.py` | Runs experiments over the workloads and produces the comparison table and the 4 plots. |
| `main.py` | Command-line interface. Prints the configuration, a per-access trace table, final cache state, statistics and AMAT. |
| `test_cache.py` | Unit tests that check the hand-calculated answers (bit fields, 1234 → tag 1 / index 13 / offset 2), conflicts, LRU vs FIFO, write-back/through, and miss classification. |

### Workloads explained

| Workload | Pattern | What it demonstrates |
|---|---|---|
| `sequential` | Walk through memory 4 bytes at a time | Spatial locality: 75% hit ratio, since each 16 B block serves 4 accesses |
| `strided_1024` | Jump 1024 bytes each access | Worst case for direct mapping: every address has the same index |
| `random` | Random addresses over 16 KB | Little locality; hit ratio is about cache size / memory size (~6%) |
| `two_arrays` | `a[i]`, `b[i]` alternately, arrays 1 KB apart | Classic conflict: both map to the same line in direct mapping |
| `matrix_row` | 32×32 int matrix, row by row | Good locality (75%) |
| `matrix_col` | Same matrix, column by column | Poor locality: large stride causes thrashing |

### Usage

```
python main.py                              # demo trace, direct-mapped
python main.py --ways 2 --policy FIFO       # 2-way set-associative, FIFO
python main.py --workload matrix_col        # run a named workload
python main.py --trace my_trace.txt         # your own trace (lines like "1234" or "W 1234")
python main.py --compare                    # hit-ratio table: workloads x associativity
python main.py --plots                      # regenerate the PNGs in plots/
python -m unittest                          # run the tests
```

Other options: `--mem`, `--cache`, `--block` (sizes in bytes, powers of two), `--write-policy`, `--no-write-allocate`, `--hit-time`, `--miss-penalty`.

Requirements: Python 3; `matplotlib` only for `--plots`.

---

## 3. The four PNG files (`plots/`)

All four are generated by `analysis.py` with the default configuration (16 KB memory, 1 KB cache, 16 B blocks, direct-mapped unless the plot varies it). The x-axis of the first three is the thing being varied, and the y-axis is hit ratio (%). Each line is one workload.

| File | What it shows | How to read it |
|---|---|---|
| `hit_vs_ways.png` | Hit ratio vs associativity (1, 2, 4, 8, 16, 64/full ways) | Lines that jump upward show workloads whose misses were conflicts. `two_arrays` jumps at 2-way, `strided_1024` at 16-way, `matrix_col` only at fully associative. Flat lines (`sequential`, `matrix_row`, `random`) don't benefit from more ways. |
| `hit_vs_cache_size.png` | Hit ratio vs cache size (256 B to 8 KB) | Shows how much a bigger cache helps each workload. Workloads limited by capacity improve with size; ones limited by conflicts or by a lack of locality respond differently. |
| `hit_vs_block_size.png` | Hit ratio vs block size (4 B to 128 B), cache size fixed | Shows the spatial-locality trade-off: larger blocks help sequential-style access, but fewer lines fit in the cache, which can hurt others. |
| `miss_breakdown.png` | Stacked bars per workload splitting misses into compulsory / capacity / conflict (% of all accesses), for the chosen configuration | Tells you *why* each workload misses, which is what justifies the choice of associativity or cache size. |

### Key results (direct-mapped to fully associative)

| Workload | 1-way | 2-way | 4-way | 16-way | Full |
|---|---|---|---|---|---|
| sequential | 75% | 75% | 75% | 75% | 75% |
| strided_1024 | 0% | 0% | 0% | 99% | 99% |
| random | 6% | 6% | 6% | 6% | 6% |
| two_arrays | 0% | 75% | 75% | 75% | 75% |
| matrix_row | 75% | 75% | 75% | 75% | 75% |
| matrix_col | 0% | 0% | 0% | 0% | 75% |

---

## 4. Other things worth knowing

- **Why 75% is the ceiling for several workloads:** with 4-byte accesses and 16-byte blocks, only the first access to each block misses (1 in 4). That is the compulsory-miss floor.
- **Why `strided_1024` needs 16 ways:** that pattern cycles through 16 blocks that all map to the same set. They only fit once the set can hold all 16.
- **Why `matrix_col` only fixes at fully associative:** the 128-byte column stride lands on very few sets in any partially associative layout, so those sets overflow.
- **Demo trace:** the default run mixes reads and writes to show a hit, cold misses, conflict misses, and dirty blocks being written back on eviction.
- **Miss classification method:** a hidden fully associative LRU cache of the same size runs alongside the real one. A miss that the shadow cache would have hit is a conflict miss; one it would also miss (on a previously seen block) is a capacity miss.
- **Limitations:** the model tracks tags only (no actual data), assumes a single cache level, and treats every access as one byte-address reference. AMAT ignores write-buffer effects.
- **Suggested report structure:** (1) calculations table and address layout, (2) mapping explanation with the 1234 / 2258 example, (3) simulator trace output, (4) the four plots and the key-results table, (5) conclusions on when associativity helps.
