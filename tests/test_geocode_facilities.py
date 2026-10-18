import unittest
from src.geocode_facilities import parse_candidate, require_kakao_key


def payload(x='127.01',y='37.6',district='강북구',province='서울'):
    return {'documents':[{'x':x,'y':y,'road_address':{'address_name':'서울 강북구 도로 1',
              'region_1depth_name':province,'region_2depth_name':district}}]}


class GeocodingTests(unittest.TestCase):
    def test_unique_address_is_a_candidate_not_a_reviewed_building(self):
        result=parse_candidate(payload(),'강북구')
        self.assertEqual(result['review_status'],'candidate_unreviewed')
        self.assertEqual(result['longitude'],127.01)

    def test_ambiguous_empty_and_district_mismatch_never_become_confirmed_points(self):
        p=payload();p['documents']*=2
        self.assertEqual(parse_candidate(p,'강북구')['review_status'],'ambiguous')
        self.assertEqual(parse_candidate({'documents':[]},'강북구')['review_status'],'no_result')
        result=parse_candidate(payload(district='노원구'),'강북구')
        self.assertEqual(result['review_status'],'district_mismatch')
        self.assertIsNone(result['longitude'])

    def test_invalid_coordinates_and_api_errors_are_not_empty_successes(self):
        self.assertEqual(parse_candidate(payload(x='nan'),'강북구')['review_status'],'invalid_coordinates')
        with self.assertRaisesRegex(ValueError,'Unexpected geocoding response'):
            parse_candidate({'errorType':'AccessDeniedError'},'강북구')

    def test_bus_key_cannot_be_used_as_a_geocoding_credential(self):
        with self.assertRaisesRegex(ValueError,'KAKAO_REST_API_KEY'):
            require_kakao_key({'SEOUL_BUS_API_KEY':'fake-bus-key'})
        self.assertEqual(require_kakao_key({'KAKAO_REST_API_KEY':'fake-kakao-key'}),'fake-kakao-key')

    def test_more_total_candidates_than_returned_items_still_requires_review(self):
        p=payload();p['meta']={'total_count':2}
        self.assertEqual(parse_candidate(p,'강북구')['review_status'],'ambiguous')
