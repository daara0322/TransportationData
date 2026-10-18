import unittest

from src.facility_supply import aggregate_routes, link_supply


def supply(route='r',low=2,regular=3,unknown=5,date='20261013'):
    return dict(route_id=route,route_name=route,date=date,records=low+regular+unknown,
                low_floor_records=low,regular_records=regular,unknown_records=unknown)


def facility(identifier='f'):
    return dict(facility_id=identifier,address='서울 중구 동호로 10',matched_address='서울 중구 동호로 10',
                longitude='127',latitude='37.5',review_status='candidate_unreviewed')


def edge(route='r',station='s'):
    return dict(route_id=route,station_id=station,longitude='127',latitude='37.5')


class FacilitySupplyTests(unittest.TestCase):
    def test_counts_are_summed_before_bounds_and_duplicate_days_fail(self):
        result=aggregate_routes([supply(low=1,regular=0,unknown=0),
                                 supply(low=0,regular=8,unknown=1,date='20261014')])
        self.assertEqual(result['r']['lower'],.1)
        self.assertEqual(result['r']['upper'],.2)
        with self.assertRaises(ValueError):
            aggregate_routes([supply(),supply()])
        with self.assertRaises(ValueError):
            aggregate_routes([dict(supply(),records=100)])

    def test_nearby_routes_and_stations_do_not_duplicate_facility(self):
        rows=[supply('r',low=2,regular=3,unknown=5),supply('r2',low=6,regular=4,unknown=0)]
        summary,details=link_supply([facility()],[edge(),edge(),edge(station='s2'),edge('r2')],rows)
        group=summary['by_radius'][0]
        self.assertEqual(group['facilities_with_nearby_route'],1)
        self.assertEqual(group['threshold_checks'][1]['lower_bound_meets'],1)
        self.assertEqual(details[0]['nearby_routes_300'],2)
        self.assertAlmostEqual(details[0]['best_route_share_lower_300'],.6)
        self.assertAlmostEqual(details[0]['best_route_share_upper_300'],.7)

    def test_unknown_classification_remains_uncertain_and_no_stop_separate(self):
        summary,_=link_supply([facility(),dict(facility('far'),latitude='38')],[edge()],[supply()])
        group=summary['by_radius'][0]
        self.assertEqual(group['no_nearby_route'],1)
        self.assertEqual(group['threshold_checks'][1]['uncertain'],1)
        self.assertEqual(group['threshold_checks'][1]['upper_bound_below'],0)

    def test_missing_route_supply_cannot_prove_upper_bound_below(self):
        summary,details=link_supply([facility()],[edge(),edge('missing')],[supply(low=0,regular=10,unknown=0)])
        self.assertEqual(summary['by_radius'][0]['threshold_checks'][1]['uncertain'],1)
        self.assertEqual(details[0]['best_route_share_upper_300'],1)

    def test_unreviewed_street_only_and_unmatched_addresses_not_in_string_match_group(self):
        rows=[facility(),dict(facility('no'),review_status='no_result'),
              dict(facility('street'),address='서울 중구 동호로',matched_address='서울 중구 동호로')]
        summary,_=link_supply(rows,[edge()],[supply()])
        self.assertEqual(summary['source_facilities'],3)
        self.assertEqual(summary['address_matching_candidate_facilities'],1)
        self.assertFalse(summary['verified_local_low_floor_service'])


if __name__=='__main__':
    unittest.main()
