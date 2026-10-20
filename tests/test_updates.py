import unittest
from ccdastro_siril._updates import select_update,version_tuple,RELEASES_URL

class UpdateTests(unittest.TestCase):
    def test_semantic_order_and_drafts(self):
        releases=[{'tag_name':'v0.9.0'},{'tag_name':'v0.10.0','prerelease':True},{'tag_name':'v8.0.0','draft':True},{'tag_name':'bad'}]
        found=select_update(releases,'0.3.0')
        self.assertEqual(found['version'],'0.10.0');self.assertTrue(found['prerelease'])
        self.assertEqual(found['url'],RELEASES_URL+'/tag/v0.10.0')
    def test_no_update_or_untrusted_link(self):
        self.assertIsNone(select_update([{'tag_name':'v1.0.0'}],'1.0.0'))
        found=select_update([{'tag_name':'v1.1.0','html_url':'https://untrusted.invalid'}],'1.0.0')
        self.assertTrue(found['url'].startswith(RELEASES_URL))
        self.assertIsNone(version_tuple('v1.2.3/../../payload'))
    def test_invalid_response(self):
        with self.assertRaises(ValueError):select_update({'message':'error'})
