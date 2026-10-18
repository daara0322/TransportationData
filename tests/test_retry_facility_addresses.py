import unittest

from src.retry_facility_addresses import building_query, merge_retry


class RetryAddressTests(unittest.TestCase):
    def test_only_details_after_complete_building_address_are_removed(self):
        self.assertEqual(building_query('서울 중구 동호로 10-2, 3층 (신당동)'), '서울 중구 동호로 10-2')
        self.assertEqual(building_query('서울 중구 동호로 10 (신당동)'), '서울 중구 동호로 10')
        self.assertIsNone(building_query('서울 중구 동호로 (신당동)'))
        self.assertIsNone(building_query('서울 중구 동호로 10'))
        self.assertIsNone(building_query('서울 중구 동호로 10, 다른 주소'))

    def test_merge_preserves_original_address_and_candidate_status(self):
        original=dict(facility_id='a',address='서울 중구 동호로 10, 3층',review_status='no_result',name='기관',district='중구')
        retry=dict(original,address='서울 중구 동호로 10',longitude='127',latitude='37.5',
                   matched_address='서울 중구 동호로 10',review_status='candidate_unreviewed')
        merged=merge_retry([original],[retry])
        self.assertEqual(merged[0]['address'], original['address'])
        self.assertEqual(merged[0]['query_address'], retry['address'])
        self.assertEqual(merged[0]['review_status'],'candidate_unreviewed')
        self.assertEqual(original['review_status'],'no_result')

    def test_unrelated_query_or_existing_candidate_cannot_be_replaced(self):
        original=dict(facility_id='a',address='서울 중구 동호로 10, 3층',review_status='no_result')
        with self.assertRaises(ValueError):
            merge_retry([original],[dict(original,address='서울 중구 동호로 100')])
        with self.assertRaises(ValueError):
            merge_retry([dict(original,review_status='candidate_unreviewed')], [original])


if __name__=='__main__':
    unittest.main()
