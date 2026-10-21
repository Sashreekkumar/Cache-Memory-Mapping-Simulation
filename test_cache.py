import unittest
from cache_sim import Cache


class TestCache(unittest.TestCase):
    def test_bit_fields(self):
        c = Cache()
        self.assertEqual((c.mem_blocks, c.lines), (1024, 64))
        self.assertEqual((c.addr_bits, c.offset_bits, c.index_bits, c.tag_bits), (14, 4, 6, 4))
        self.assertEqual(c.split(1234), (1, 13, 2))

    def test_direct_mapped_conflict(self):
        c = Cache()
        r = [c.access(a)["result"] for a in (1234, 1236, 2258, 1234)]
        self.assertEqual(r, ["MISS (compulsory)", "HIT", "MISS (compulsory)", "MISS (conflict)"])

    def test_two_way_resolves_conflict(self):
        c = Cache(ways=2)
        r = [c.access(a)["result"] for a in (1234, 2258, 1234)]
        self.assertEqual(r[2], "HIT")

    def test_lru_vs_fifo(self):
        seq = [0, 512, 0, 1024, 512]            # same set in a 2-way, 1 KB cache
        lru, fifo = Cache(ways=2, policy="LRU"), Cache(ways=2, policy="FIFO")
        self.assertTrue(lru.run(seq)[-1]["result"].startswith("MISS"))
        self.assertEqual(fifo.run(seq)[-1]["result"], "HIT")

    def test_write_back_dirty_eviction(self):
        c = Cache()
        c.access(1234, "W")
        c.access(2258)
        self.assertEqual(c.writebacks, 1)

    def test_write_through(self):
        c = Cache(write_policy="write-through")
        c.access(0, "R")
        c.access(0, "W")
        self.assertEqual((c.mem_writes, c.writebacks), (1, 0))

    def test_capacity_misses(self):
        c = Cache(ways=64)                      # fully associative
        c.run([i * 16 for i in range(65)] * 2)
        self.assertEqual(c.miss_kinds, {"compulsory": 65, "capacity": 65, "conflict": 0})

    def test_out_of_range(self):
        with self.assertRaises(ValueError):
            Cache().access(16 * 1024)


if __name__ == "__main__":
    unittest.main()
