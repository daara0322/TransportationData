import unittest

from src.building_sensitivity import compare_candidates


def candidate(identifier,latitude='37.5'):
    return dict(facility_id=identifier,address='서울 중구 동호로 10',matched_address='서울 중구 동호로 10',
                longitude='127',latitude=latitude,review_status='candidate_unreviewed')


def route(identifier,low,regular):
    return dict(route_id=identifier,route_name=identifier,date='20261013',records=low+regular,
                low_floor_records=low,regular_records=regular,unknown_records=0)


class BuildingSensitivityTests(unittest.TestCase):
    def test_two_points_are_one_facility_and_can_change_radius_classification(self):
        candidates=[candidate('f_main_scenario'),candidate('f_annex_scenario','37.5004')]
        edges=[dict(route_id='low',station_id='a',longitude='127',latitude='37.5'),
               dict(route_id='high',station_id='b',longitude='127',latitude='37.5029')]
        result=compare_candidates('f',candidates,edges,[route('low',2,8),route('high',8,2)])
        self.assertEqual(result['reference_facilities'],1)
        self.assertEqual(result['scenario_count'],2)
        self.assertTrue(40<result['coordinate_separation_metres']<50)
        main,annex=result['scenarios']
        self.assertEqual(main['by_radius'][0]['best_route_share_upper'],.2)
        self.assertEqual(annex['by_radius'][0]['best_route_share_lower'],.8)
        self.assertFalse(result['verified_building_or_entrance'])
        self.assertEqual(candidates[0]['latitude'],'37.5')

    def test_wrong_reference_duplicate_or_invalid_candidate_is_rejected(self):
        edge=dict(route_id='low',station_id='a',longitude='127',latitude='37.5')
        cases=[[candidate('other_main_scenario'),candidate('f_annex_scenario')],
               [candidate('f_main_scenario'),candidate('f_main_scenario')],
               [candidate('f_main_scenario'),dict(candidate('f_annex_scenario'),latitude='nan')]]
        for candidates in cases:
            with self.assertRaises(ValueError):
                compare_candidates('f',candidates,[edge],[route('low',2,8)])


if __name__=='__main__':unittest.main()
