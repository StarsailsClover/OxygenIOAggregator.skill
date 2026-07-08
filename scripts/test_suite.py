"""OIA v26.0 Alpha 2 — Test Suite"""
import hashlib, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from batch_io import BatchIOEngine
from smart_cache import LRUFileCache, WriteCoalescer, CachedIO
from binary_inspector import BinaryInspector, BinaryFormat

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
        self.engine.batch_write({'a.txt': 'hello', 'b.txt': 'world'})
        self.engine.batch_read(['**/*.txt'])
        self.engine.batch_delete(['b.txt'])
        s = self.engine.get_stats()
        self.assertEqual(s['total_pages'], 1)
        self.assertEqual(s['total_writes'], 2)
        self.assertEqual(s['total_reads'], 2)
        self.assertEqual(s['total_deletes'], 1)

class TestLRUCache(unittest.TestCase):
    def test_eviction(self):
        c = LRUFileCache(max_size_mb=1, max_entries=3)
        for i in range(5):
            c.put(f'k{i}', f'v{i}')
        s = c.stats()
        self.assertLessEqual(s['entries'], 3)

class TestWriteCoalescer(unittest.TestCase):
    def test_flush_returns_errors(self):
        td = tempfile.mkdtemp()
        wc = WriteCoalescer(base_dir=td, flush_interval_ms=60000)
        wc.queue_write('x.txt', 'XXX')
        flushed, total, errors = wc.flush()
        self.assertEqual(flushed, 1)
        self.assertEqual(total, 3)
        self.assertEqual(errors, 0)
    
    def test_empty_flush_returns_three_values(self):
        td = tempfile.mkdtemp()
        wc = WriteCoalescer(base_dir=td, flush_interval_ms=60000)
        self.assertEqual(wc.flush(), (0, 0, 0))

class TestCachedIO(unittest.TestCase):
    def test_read_file(self):
        td = tempfile.mkdtemp()
        Path(td, 'test.txt').write_text('hello cached')
        cio = CachedIO(base_dir=td)
        r = cio.read_file('test.txt')
        self.assertEqual(r, 'hello cached')
    
    def test_write_immediate(self):
        td = tempfile.mkdtemp()
        cio = CachedIO(base_dir=td, use_write_coalescing=False)
        cio.write_file('imm.txt', 'immediate', immediate=True)
        self.assertTrue(Path(td, 'imm.txt').exists())
        self.assertEqual(Path(td, 'imm.txt').read_text(), 'immediate')
    
    def test_write_deferred_not_on_disk(self):
        td = tempfile.mkdtemp()
        cio = CachedIO(base_dir=td, flush_interval_ms=60000)
        cio.write_file('def.txt', 'deferred', immediate=False)
        self.assertFalse(Path(td, 'def.txt').exists())
    
    def test_flush_writes_deferred(self):
        td = tempfile.mkdtemp()
        cio = CachedIO(base_dir=td, flush_interval_ms=60000)
        cio.write_file('def.txt', 'deferred', immediate=False)
        written, total, errors = cio.flush_writes()
        self.assertEqual(written, 1)
        self.assertEqual(errors, 0)
        self.assertTrue(Path(td, 'def.txt').exists())
        self.assertEqual(Path(td, 'def.txt').read_text(), 'deferred')
    
    def test_write_then_read_cache_hit(self):
        td = tempfile.mkdtemp()
        cio = CachedIO(base_dir=td, use_write_coalescing=False)
        cio.write_file('test.txt', 'cached content', immediate=True)
        r = cio.read_file('test.txt')
        self.assertEqual(r, 'cached content')
    
    def test_flush_marks_entries_clean(self):
        td = tempfile.mkdtemp()
        cio = CachedIO(base_dir=td, flush_interval_ms=60000)
        cio.write_file('def.txt', 'deferred', immediate=False)
        dirty_before = cio.cache.stats()['dirty_entries']
        self.assertEqual(dirty_before, 1)
        cio.flush_writes()
        dirty_after = cio.cache.stats()['dirty_entries']
        self.assertEqual(dirty_after, 0)
    
    def test_flush_empty_returns_zeros(self):
        td = tempfile.mkdtemp()
        cio = CachedIO(base_dir=td, flush_interval_ms=60000)
        self.assertEqual(cio.flush_writes(), (0, 0, 0))
    
    def test_shutdown_stops_background(self):
        td = tempfile.mkdtemp()
        cio = CachedIO(base_dir=td, flush_interval_ms=60000)
        # Deferred write
        cio.write_file('sd.txt', 'shutdown test', immediate=False)
        cio.shutdown()
        # After shutdown, file should be flushed
        self.assertTrue(Path(td, 'sd.txt').exists())
        self.assertEqual(Path(td, 'sd.txt').read_text(), 'shutdown test')

class TestBinaryInspector(unittest.TestCase):
    def setUp(self):
        self.bi = BinaryInspector()
    
    def test_inspect_missing_file(self):
        info = self.bi.inspect('/nonexistent/foo.bin')
        self.assertEqual(info.format, BinaryFormat.UNKNOWN)
        self.assertIsNotNone(info.error)
        self.assertFalse(info.success)
    
    def test_inspect_text_file(self):
        td = tempfile.mkdtemp()
        txt = Path(td, 'hello.txt')
        txt.write_text('hello world')
        info = self.bi.inspect(str(txt))
        self.assertEqual(info.format, BinaryFormat.UNKNOWN)
        self.assertTrue(info.success)
        self.assertEqual(info.sha256, hashlib.sha256(b'hello world').hexdigest())
    
    def test_inspect_pe_binary(self):
        pe = r'C:\WINDOWS\System32\cmd.exe'
        if not Path(pe).exists():
            self.skipTest('cmd.exe not found')
        info = self.bi.inspect(pe)
        self.assertEqual(info.format, BinaryFormat.PE)
        self.assertTrue(info.success)
        self.assertIsNotNone(info.architecture)
        self.assertGreater(info.size, 0)
        self.assertGreater(len(info.sha256), 0)
        self.assertGreater(len(info.md5), 0)
    
    def test_inspect_pe_deep(self):
        pe = r'C:\WINDOWS\System32\cmd.exe'
        if not Path(pe).exists():
            self.skipTest('cmd.exe not found')
        info = self.bi.inspect(pe, deep=True)
        self.assertEqual(info.format, BinaryFormat.PE)
        self.assertGreater(info.section_count, 0)
        self.assertGreater(len(info.sections), 0)
    
    def test_batch_inspect(self):
        td = tempfile.mkdtemp()
        a = Path(td, 'a.txt'); a.write_text('aaa')
        b = Path(td, 'b.txt'); b.write_text('bbb')
        results = self.bi.batch_inspect([str(a), str(b), '/nonexistent.bin'])
        self.assertEqual(len(results), 3)
        self.assertTrue(results[str(a)].success)
        self.assertTrue(results[str(b)].success)
        self.assertFalse(results['/nonexistent.bin'].success)

if __name__ == '__main__':
    unittest.main(verbosity=2)
