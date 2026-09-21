"""Offline regression tests. Every mutation uses an isolated temporary directory."""
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'integracoes'))
sys.path.insert(0, str(ROOT / 'integracoes/mercadolivre'))
import catalogo
import rebuild_catalog


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ('dados', 'catalogo', '_data'):
            shutil.copytree(ROOT / name, self.root / name)
        for name in ('produtos.js', 'links-afiliados.json'):
            shutil.copy2(ROOT / name, self.root / name)
        self.original = catalogo.load(self.root)

    def files(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes()
                for p in self.root.rglob('*') if p.is_file()}

    def test_current_artifacts_match_source(self):
        self.assertEqual(catalogo.check(self.root), len(self.original['publishedIds']))

    def test_generation_is_repeatable_and_preserves_all_fields(self):
        expected = json.loads((self.root / 'produtos.js').read_text(encoding='utf-8').split('window.MIRA_DATA = ',1)[1].rstrip(';\n'))
        catalogo.generate(self.root)
        before = self.files()
        catalogo.generate(self.root)
        self.assertEqual(before, self.files())
        self.assertEqual(expected, catalogo.public_data(catalogo.load(self.root)))

    def test_preview_does_not_change_source(self):
        before = self.files()
        with tempfile.TemporaryDirectory() as output:
            catalogo.generate(self.root, Path(output))
            self.assertTrue((Path(output) / 'produtos.js').exists())
        self.assertEqual(before, self.files())

    def test_edited_public_price_detected(self):
        path = self.root / 'catalogo/produtos-001.json'
        rows = catalogo.read_json(path)
        rows[0]['price'] += 1
        path.write_text(json.dumps(rows), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'divergentes'):
            catalogo.check(self.root)

    def test_duplicate_unknown_and_invalid_price_rejected_without_writes(self):
        for mutation in ('duplicate', 'unknown', 'nan', 'bool', 'zero', 'few', 'link', 'image'):
            with self.subTest(mutation=mutation):
                data = catalogo.public_data(self.original)
                first = data['products'][0]
                if mutation == 'duplicate': data['products'].append(copy.deepcopy(first))
                elif mutation == 'unknown': first['id'] = 'MLB999999999999'
                elif mutation == 'nan': first['price'] = float('nan')
                elif mutation == 'bool': first['price'] = True
                elif mutation == 'zero': first['price'] = 0
                elif mutation == 'few': data['products'] = data['products'][:10]
                elif mutation == 'link': first['affiliateUrl'] = 'https://meli.la/incorrect'
                elif mutation == 'image': first['imageUrl'] = 'https://example.com/other.png'
                before = self.files()
                with self.assertRaises(ValueError): catalogo.apply_snapshot(data, self.root)
                self.assertEqual(before, self.files())

    def test_partial_snapshot_retains_unpublished_records(self):
        data = catalogo.public_data(self.original)
        removed = data['products'].pop()
        data['products'][0]['price'] += 1
        # This simulated edit has no matching observation from the provider.
        data['products'][0].pop('priceCheck', None)
        with patch.object(catalogo, 'MIN_PRODUCTS', len(data['products'])):
            catalogo.apply_snapshot(data, self.root)
            result = catalogo.load(self.root)
            self.assertEqual(len(result['products']), len(self.original['products']))
            self.assertEqual(next(p for p in result['products'] if p['id']==removed['id']), removed)
            self.assertNotIn(removed['id'], result['publishedIds'])
            self.assertEqual(catalogo.check(self.root), len(data['products']))

    def test_archive_link_mismatch_blocks_generation(self):
        path = self.root / catalogo.SOURCE
        self.original['products'][0]['affiliateUrl'] = 'https://meli.la/incorrect'
        path.write_text(catalogo.dumps(self.original), encoding='utf-8')
        before = self.files()
        with self.assertRaisesRegex(ValueError, 'registro de afiliados'):
            catalogo.generate(self.root)
        self.assertEqual(before, self.files())

    def test_inactive_editorial_record_is_not_available(self):
        data = catalogo.public_data(self.original)
        data['products'][0]['available'] = False
        # The separate inactive-status scenario has no public-card evidence.
        data['products'][0].pop('priceCheck', None)
        catalogo.apply_snapshot(data, self.root)
        editorial = catalogo.read_json(self.root / '_data/produtos.json')
        self.assertFalse(editorial[data['products'][0]['id']]['available'])

    def test_extra_chunk_is_detected_and_removed_by_generation(self):
        stale = self.root / 'catalogo/produtos-999.json'
        stale.write_text('[]', encoding='utf-8')
        with self.assertRaises(ValueError): catalogo.check(self.root)
        catalogo.generate(self.root)
        self.assertFalse(stale.exists())
        catalogo.check(self.root)

    def simulate_collection(self, success_count, dry=False):
        source = {'products': copy.deepcopy(self.original['products'])}
        accepted = {p['id'] for p in source['products'][:success_count]}
        def refresh(p, date):
            return (copy.deepcopy(p), None) if p['id'] in accepted else (None, {'id':p['id'],'reason':'test_failure'})
        args = ['--max-products','500','--min-products','450'] + (['--dry-run'] if dry else [])
        with patch.object(rebuild_catalog, 'refresh_one', side_effect=refresh), \
             patch.object(rebuild_catalog.base, 'ROOT', self.root), \
             patch.object(rebuild_catalog.base, 'now_sp', return_value=datetime(2026,9,20,tzinfo=timezone.utc)), \
             patch.object(rebuild_catalog.base, 'write_report'):
            return rebuild_catalog.main(argv=args, source=source)

    def test_collection_failure_keeps_all_files(self):
        before = self.files()
        with self.assertRaises(RuntimeError): self.simulate_collection(20)
        self.assertEqual(before, self.files())

    def test_collection_dry_run_keeps_all_files(self):
        before = self.files()
        self.simulate_collection(500, dry=True)
        self.assertEqual(before, self.files())

    def test_collection_success_keeps_registry_and_all_derivatives_consistent(self):
        # Use eligible published products, including stable registration order.
        registered_count = len(self.original['products'])
        original = copy.deepcopy(self.original)
        original['products'] = catalogo.public_data(original)['products']
        self.original = original
        published_count = len(original['products'])
        self.simulate_collection(published_count)
        self.assertEqual(catalogo.check(self.root),published_count)
        self.assertEqual(len(catalogo.load(self.root)['products']),registered_count)

    def test_legacy_import_cannot_overwrite_production(self):
        sys.path.insert(0, str(ROOT))
        import atualizar_produtos
        with self.assertRaisesRegex(ValueError, 'Importação direta desativada'):
            atualizar_produtos.convert('nonexistent.xlsx', ROOT)


if __name__ == '__main__':
    unittest.main()
