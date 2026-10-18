import unittest
from pathlib import Path

from src.facility_catchments import address_check, diagnose, validate_paths


def facility(identifier='f1', **changes):
    row=dict(facility_id=identifier, district='중구', address='서울특별시 중구 동호로 10, 2층',
             matched_address='서울 중구 동호로 10', longitude='127', latitude='37.5',
             review_status='candidate_unreviewed')
    return dict(row, **changes)


class CatchmentTests(unittest.TestCase):
    def test_building_number_and_road_must_agree(self):
        self.assertEqual(address_check(facility()), 'road_building_match_unreviewed')
        self.assertEqual(address_check(facility(matched_address='서울 중구 동호로 100')), 'road_building_mismatch')
        self.assertEqual(address_check(facility(address='서울 중구 동호로')), 'not_comparable')
        self.assertEqual(address_check(facility(address='서울 중구 신당동 10')), 'not_comparable')

    def test_shared_stations_and_repeated_edges_do_not_duplicate_facilities(self):
        edge=dict(route_id='r1', station_id='s1', longitude='127', latitude='37.5')
        edges=[edge, edge, dict(edge, station_id='s2'), dict(edge, route_id='r2')]
        summary, details=diagnose([facility()], edges)
        self.assertEqual(summary['by_radius'][0]['candidate_facilities_near_any_station'], 1)
        self.assertEqual(len(summary['by_route']), 2)
        self.assertTrue(all(r['candidate_facilities_by_radius']['300']==1 for r in summary['by_route']))
        self.assertFalse(summary['confirmed_accessibility_analysis'])
        self.assertEqual(details[0]['nearest_station_metres'], 0)

    def test_invalid_and_missing_points_are_retained_in_denominator(self):
        rows=[facility(), facility('f2', review_status='no_result', longitude='', latitude=''),
              facility('f3', longitude='nan'), facility('f4', review_status='ambiguous')]
        summary, _=diagnose(rows, [dict(route_id='r', station_id='s', longitude='127', latitude='37.5')])
        self.assertEqual(summary['source_facilities'], 4)
        self.assertEqual(summary['usable_candidate_points'], 1)

    def test_inconsistent_station_or_duplicate_facility_fails(self):
        a=dict(route_id='r', station_id='s', longitude='127', latitude='37.5')
        with self.assertRaises(ValueError):
            diagnose([facility()], [a,dict(a,longitude='128')])
        with self.assertRaises(ValueError):
            diagnose([facility(),facility()], [a])

    def test_street_without_building_number_is_not_a_facility_point(self):
        row=facility(address='서울 중구 동호로', matched_address='서울 중구 동호로')
        summary, _=diagnose([row], [dict(route_id='r',station_id='s',longitude='127',latitude='37.5')])
        self.assertEqual(summary['usable_candidate_points'], 0)
        self.assertEqual(summary['coordinate_and_address_checks']['incomplete_road_address'], 1)

    def test_outputs_cannot_collide_with_inputs_or_each_other(self):
        base=Path.cwd()/'data'/'processed'/'path_validation_test'
        a,b,c,d=[base/name for name in ['facilities.csv','edges.csv','summary.json','review.csv']]
        for summary,details in [(a,d),(b,d),(c,a),(c,b),(c,c)]:
            with self.assertRaises(ValueError):
                validate_paths(a,b,summary,details)
        validate_paths(a,b,c,d)


if __name__=='__main__':
    unittest.main()
