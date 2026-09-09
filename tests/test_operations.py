import importlib.util
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import time
import unittest

PROJECT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('branding', PROJECT / 'scripts/branding.py')
branding = importlib.util.module_from_spec(spec)
spec.loader.exec_module(branding)

class BrandingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        branding.ROOT = Path(self.tmp.name)
        self.files = {name: (b'\x00\x00\x01\x00\x01\x00' if n is None else
            b'\x89PNG\r\n\x1a\n' + b'\x00' * 8 + struct.pack('>II', n, n)) for name, n in branding.FILES.items()}

    def test_updates_are_visible_through_existing_native_link(self):
        branding.sync(self.files.__getitem__)
        native = branding.ROOT / 'native.png'
        native.symlink_to(branding.ROOT / 'current/axi_logo_new2_32x32.png')
        old = native.read_bytes()
        self.files['axi_logo_new2_32x32.png'] += b'changed'
        branding.sync(self.files.__getitem__)
        self.assertNotEqual(native.read_bytes(), old)

    def test_failed_download_keeps_complete_previous_generation(self):
        branding.sync(self.files.__getitem__)
        previous = os.readlink(branding.ROOT / 'current')
        def broken(name):
            if name.endswith('32x32.png'):
                raise OSError('network unavailable')
            return self.files[name]
        with self.assertRaises(OSError):
            branding.sync(broken)
        self.assertEqual(os.readlink(branding.ROOT / 'current'), previous)

    def test_wrong_dimensions_rejected_before_activation(self):
        self.files['axi_logo_new2_32x32.png'] = self.files['axi_logo_new2_16x16.png']
        with self.assertRaises(ValueError):
            branding.sync(self.files.__getitem__)
        self.assertFalse((branding.ROOT / 'current').exists())

if __name__ == '__main__':
    unittest.main()
