"""OIA v26.0 Alpha 2 — Test Suite"""
import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from batch_io import BatchIOEngine
from smart_cache import LRUFileCache, WriteCoalescer, CachedIO
from binary_inspector import BinaryInspector

class TestBatchIO(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.mkdtemp()
        self.engine = BatchIOEngine(base_dir=self.td, use_mmap=True, atomic_writes=True)
    
    def test_batch_write(self):
        r = self.engine.batch_write({'a.txt': 'hello', 'b.txt': 'world'})
        self.assertEqual(len(r), 2)
        self.assertTrue(all(v.success for v in r.values()))
    
    def test_batch_read(self):
        self.engine.batch_write({'a.txt': 'hello world'})
        pages = self.engine.batch_read(['**/*.txt'])
        self.assertIn('a.txt', pages)
        self.assertEqual(pages['a.txt'].content, 'hello world')
    
    def test_batch_delete(self):
        self.engine.batch_write({'del.txt': 'bye'})
        gs = self.engine.batch_delete(['del.txt'])
        self.assertEqual(sum(gs.values()), 1)
    
    def test_delete_updates_counter(self):
        self.engine.batch_write({'del.txt': 'bye'})
        self.engine.batch_delete(['del.txt'])
        self.assertEqual(self.engine._total_deletes, 1)
    
    def test_stats_has_counters(self):
        s = self.engine.get_stats()
        self.assertIn('total_pages', s)
        self.assertIn('total_writes', s)
        self.assertIn('total_reads', s)
        self.assertIn('total_deletes', s)

class TestLRUCache(unittest.TestCase):
    def test_eviction(self):
        c = LRUFileCache(max_size_mb=1, max_entries=3)
        for i in range(5):
            c.put(f'k{i}', f'v{i}')
        s = c.stats()
        self.assertLessEqual(s['entries'], 3)

class TestWriteCoalescer(unittest.TestCase):
    def test_flush_returns_errors(self):
        wc = WriteCoalescer(flush_interval_ms=60000)
        wc.queue_write('x.txt', 'XXX')
        flushed, total, errors = wc.flush()
        self.assertEqual(flushed, 1)
        self.assertIsInstance(errors, int)

class TestCachedIO(unittest.TestCase):
    def test_read_file(self):
        td = tempfile.mkdtemp()
        Path(td, 'test.txt').write_text('hello cached')
        cio = CachedIO(base_dir=td)
        r = cio.read_file('test.txt')
        self.assertEqual(r, 'hello cached')

class TestBinaryInspector(unittest.TestCase):
    def test_inspect_ls(self):
        bi = BinaryInspector()
        for p in ['/bin/ls', '/usr/bin/ls']:
            if Path(p).exists():
                info = bi.inspect(p)
                self.assertIsNotNone(info.format)
                break

if __name__ == '__main__':
    unittest.main(verbosity=2)
