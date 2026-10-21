"""Memory-access pattern generators. Each returns a list of byte addresses."""
import random

MEM = 16 * 1024


def sequential(n=1024, step=4, base=0):
    return [(base + i * step) % MEM for i in range(n)]


def strided(n=2048, stride=1024, base=0):
    """Wraps inside memory: stride 1024 hits only 16 addresses, all on one index."""
    return [(base + i * stride) % MEM for i in range(n)]


def random_access(n=2048, seed=1):
    rng = random.Random(seed)
    return [rng.randrange(MEM) for _ in range(n)]


def two_arrays(n=128, elem=4, a_base=0, b_base=1024):
    """c = a[i] + b[i]: arrays 1 KB apart collide in a 1 KB direct-mapped cache."""
    trace = []
    for i in range(n):
        trace += [a_base + i * elem, b_base + i * elem]
    return trace


def matrix_row_major(rows=32, cols=32, elem=4, base=0):
    return [base + (i * cols + j) * elem for i in range(rows) for j in range(cols)]


def matrix_col_major(rows=32, cols=32, elem=4, base=0):
    return [base + (i * cols + j) * elem for j in range(cols) for i in range(rows)]


WORKLOADS = {
    "sequential": sequential,
    "strided_1024": strided,
    "random": random_access,
    "two_arrays": two_arrays,
    "matrix_row": matrix_row_major,
    "matrix_col": matrix_col_major,
}
