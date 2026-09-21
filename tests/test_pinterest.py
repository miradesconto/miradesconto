import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pinterest_drafts', ROOT / 'integracoes/pinterest/preparar.py')
drafts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(drafts)


class PinterestTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads(drafts.CONFIG.read_text(encoding='utf-8'))

    def test_three_drafts_are_deterministic_and_never_approved(self):
        queue = drafts.build()
        self.assertEqual(queue, drafts.build())
        self.assertEqual(len(queue['posts']), 3)
        self.assertFalse(queue['publishingEnabled'])
        for p in queue['posts']:
            self.assertFalse(p['approved'])
            self.assertIsNone(p['boardId'])
            self.assertIn('afiliados', p['description'])
            self.assertNotIn('price', p)

    def test_duplicates_and_previously_published_links_are_excluded(self):
        self.config['articles'] *= 2
        first = drafts.build()['posts'][0]['link']
        queue = drafts.build(config=self.config, published_links=[first])
        self.assertEqual(len(queue['posts']), 2)
        self.assertNotIn(first, [p['link'] for p in queue['posts']])

    def test_unpublished_article_and_unsafe_paths_fail(self):
        self.config['articles'] = ['cafeteira-electrolux-ecm10']
        with self.assertRaisesRegex(ValueError, 'não publicado'):
            drafts.build(config=self.config)
        self.config['articles'] = ['../../privacidade']
        with self.assertRaises(ValueError):
            drafts.build(config=self.config)

    def test_live_mode_and_external_destination_are_rejected(self):
        self.config['mode'] = 'live'
        with self.assertRaises(ValueError): drafts.build(config=self.config)
        self.config['mode'] = 'draft_only'
        self.config['siteUrl'] = 'https://example.com/'
        with self.assertRaises(ValueError): drafts.build(config=self.config)

    def test_preview_escapes_editorial_text(self):
        queue = drafts.build()
        queue['posts'][0]['title'] = '<script>alert(1)</script>'
        self.assertNotIn('<script>', drafts.render(queue))


if __name__ == '__main__':
    unittest.main()
