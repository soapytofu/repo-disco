"""Offline setup/recording safety checks, not mathematical evidence."""
import io,json,os,subprocess,tempfile,unittest,zipfile
from pathlib import Path
from unittest import mock
import baseline as b

class BaselineTests(unittest.TestCase):
    def test_source_and_runtime_pins(self):b.pins()
    def test_capture_records_nonzero_without_inventing_success(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            def fake(args,**kw):
                self.assertEqual(args[0:2],['/usr/bin/time','-v']);self.assertIn('timeout',args)
                Path(args[3]).write_text('Maximum resident set size (kbytes): 10\n')
                kw['stdout'].write(b'proof failed');return subprocess.CompletedProcess(args,4)
            with mock.patch.object(b.subprocess,'run',fake):r=b.capture('one',['fake'],root,root,{},15)
            self.assertEqual(r['exit_code'],4);self.assertEqual(r['attempts'],1);self.assertEqual(r['model_calls'],0)
            with self.assertRaises(FileExistsError):b.capture('one',['fake'],root,root,{},15)
    def test_checked_stops_failure(self):
        with mock.patch.object(b,'capture',return_value={'exit_code':1}):
            with self.assertRaises(RuntimeError):b.checked('bad',[],Path('.'),Path('.'),{})
    def test_no_native_execution_outside_compute(self):
        with mock.patch.dict(os.environ,{},clear=True):
            with self.assertRaises(AssertionError):b.main('dafny-vmc')
    def test_archive_traversal_and_symlink_rejected(self):
        for name,mode in [('../escape',0),('/absolute',0),('link',0o120777<<16)]:
            with tempfile.TemporaryDirectory() as d:
                root=Path(d);archive=root/'a.zip'
                with zipfile.ZipFile(archive,'w') as z:
                    item=zipfile.ZipInfo(name);item.external_attr=mode;z.writestr(item,b'test')
                with self.assertRaises(AssertionError):b.unpack(archive,root/'output')
    def test_digest_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);dest=root/'download'
            def fake(*a,**k):dest.write_bytes(b'wrong')
            with mock.patch.object(b,'checked',fake):
                with self.assertRaises(AssertionError):b.download('artifact','https://example.invalid',dest,root,{},'0'*64)

if __name__=='__main__':unittest.main(verbosity=2)
