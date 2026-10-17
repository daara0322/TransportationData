import unittest

from src.audit_route_master import summarize_master


class RouteMasterTests(unittest.TestCase):
    def test_missing_names_types_and_unknown_coverage_stay_visible(self):
        master = [{'노선ID': '\ufeff009', '노선명': '10', '노선유형': '3',
                   '지역ID': '-', '사용여부': '1', '운행여부': '1'}]
        linkage = {'routes': [dict(route_id='009', historical_vehicles=4,
                                  classified_vehicles=2, low_floor_vehicles=1,
                                  regular_vehicles=1, unclassified_vehicles=2),
                              dict(route_id='010', historical_vehicles=0,
                                   classified_vehicles=0, low_floor_vehicles=0,
                                   regular_vehicles=0, unclassified_vehicles=0)]}
        snapshot = {'records': [{'route_id': '009', 'vehicle_id': '001'},
                                {'route_id': '010', 'vehicle_id': '001'}]}
        vehicle_routes = [{'노선ID': '009', '차량ID': '001'}]
        result = summarize_master(master, {'009': '10A', '010': '11'}, linkage,
                                  snapshot, vehicle_routes)
        self.assertEqual(result['missing_master_ids'], ['010'])
        self.assertEqual(result['name_mismatches'][0]['master_name'], '10')
        self.assertEqual(result['candidate_type_counts'], {'3': 1, 'missing': 1})
        self.assertEqual(result['snapshot_pairs_in_vehicle_master'], 1)
        route = result['routes'][0]
        self.assertEqual(route['low_floor_share_lower_bound'], .25)
        self.assertEqual(route['low_floor_share_upper_bound'], .75)
        self.assertIsNone(result['routes'][1]['low_floor_share_lower_bound'])

    def test_duplicate_master_ids_are_rejected(self):
        rows = [{'노선ID': '009'}, {'노선ID': '\ufeff009'}]
        with self.assertRaisesRegex(ValueError, 'Duplicate master route ID'):
            summarize_master(rows, {}, {'routes': []}, {'records': []}, [])

    def test_inconsistent_denominators_are_rejected(self):
        linkage = {'routes': [dict(route_id='009', historical_vehicles=4,
                                  classified_vehicles=2, low_floor_vehicles=1,
                                  regular_vehicles=1, unclassified_vehicles=1)]}
        with self.assertRaisesRegex(ValueError, 'Inconsistent classification counts'):
            summarize_master([], {'009': '10'}, linkage, {'records': []}, [])
