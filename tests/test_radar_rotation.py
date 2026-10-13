"""Rotation must preserve qualified history and expire against wall-clock time."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from integracoes.automacao import gerar_radar as radar


class RadarRotationTests(unittest.TestCase):
    def test_rotation_diversity_and_stability(self):
        now = datetime(2026, 10, 13, 1, tzinfo=timezone.utc)
        items = [dict(id=str(i), category=('Setup', 'Gaming', 'Celulares', 'Áudio')[i % 4],
                      actionable=True, strength=3, deltaAveragePct=-9) for i in range(24)]
        first = radar.select_featured(items, now)
        self.assertEqual(len(first), 12)
        self.assertEqual(len(set(first)), 12)
        self.assertEqual(first, radar.select_featured(items, now + timedelta(minutes=1)))
        self.assertNotEqual(first, radar.select_featured(items, now + timedelta(hours=1)))
        self.assertNotIn('ineligible', radar.select_featured(items + [dict(id='ineligible', actionable=False)], now))

    def test_stopped_collector_does_not_freeze_freshness(self):
        now = datetime(2026, 10, 13, 1, tzinfo=timezone.utc)
        product = dict(id='MLB1234567890', category='Setup', name='Mouse', available=True,
                       affiliateUrl='https://meli.la/Ab123', imageUrl='https://example.com/photo.jpg',
                       price=90, oldPrice=None)
        product['priceCheck'] = dict(status='verified', method='poly-card-v1', currency='BRL',
                                    itemId=product['id'], price=90, oldPrice=None, checkedAt=now.isoformat())
        history = {'observations':[dict(at=(now - timedelta(days=10-i)).isoformat(), price=100,
                                        itemId=product['id'], variationId='') for i in range(10)]}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'catalog.json').write_text(json.dumps({'products':[product]}))
            (root / (product['id'] + '.json')).write_text(json.dumps(history))
            with patch.object(radar, 'CATALOG', root / 'catalog.json'), patch.object(radar, 'HISTORY', root), patch.object(radar, 'OUTPUT', root / 'radar.json'):
                radar.main(now + timedelta(minutes=1))
                self.assertEqual(json.loads((root / 'radar.json').read_text())['featured'], [product['id']])
                radar.main(now + timedelta(hours=3))
                result = json.loads((root / 'radar.json').read_text())
                self.assertEqual(result['featured'], [])
                self.assertEqual(result['byId'], {})


if __name__ == '__main__':
    unittest.main()
