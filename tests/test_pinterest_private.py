import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('oauth', Path(__file__).resolve().parents[1]/'integracoes/pinterest/oauth_local.py')
oauth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oauth)


class PrivateStorageTests(unittest.TestCase):
    def test_atomic_roundtrip_and_no_plaintext_on_windows(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)/'private'
            target = folder/'oauth.json'
            with patch.object(oauth, 'PRIVATE_DIR', folder), patch.object(oauth, 'TOKEN_FILE', target):
                data = {'access_token': 'FAKE-TEST-ACCESS', 'refresh_token': 'FAKE-TEST-REFRESH'}
                oauth.store_private(data)
                self.assertEqual(oauth.read_private(), data)
                if os.name == 'nt':
                    self.assertNotIn(b'FAKE-TEST', target.read_bytes())
                else:
                    self.assertEqual(target.stat().st_mode & 0o777, 0o600)
                self.assertEqual(list(folder.iterdir()), [target])

    def test_repo_storage_is_rejected_before_write(self):
        folder = Path(__file__).resolve().parents[1]/'private-test'
        with patch.object(oauth, 'PRIVATE_DIR', folder):
            with self.assertRaisesRegex(RuntimeError, 'repositorio'):
                oauth.store_private({'access_token':'FAKE'})
        self.assertFalse(folder.exists())

    @unittest.skipUnless(os.name == 'nt', 'DPAPI is Windows only')
    def test_crypto_failure_never_writes_plaintext(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)/'private'
            with patch.object(oauth, 'PRIVATE_DIR', folder), patch.object(oauth.os, 'name', 'nt'), patch.object(oauth, 'protect_windows', side_effect=RuntimeError('failed')):
                with self.assertRaises(RuntimeError):
                    oauth.store_private({'access_token':'FAKE'})
            self.assertFalse(folder.exists())
