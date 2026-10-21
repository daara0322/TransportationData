import unittest
from src.candidate_facilities import compare, index_supply


class CandidateFacilityTests(unittest.TestCase):
    def test_dedup_self_exclusion_thresholds_and_missing_alternative(self):
        facilities = [
            {'facility_id': 'f1', 'route_ids_300': 'a;a', 'route_ids_500': 'a;b;b', 'route_ids_800': 'a;b'},
            {'facility_id': 'f2', 'route_ids_300': '', 'route_ids_500': 'a;c', 'route_ids_800': 'a;c'},
        ]
        supply = {'a': {'lower': 0, 'upper': .2}, 'b': {'lower': .5, 'upper': .7}}
        result = compare(facilities, {'f1': 'rehab', 'f2': 'day'},
                         [{'route_id': 'a', 'route_name': 'A'}], supply)
        r300, r500, _ = result['routes'][0]['by_radius']
        self.assertEqual(r300['linked_facilities'], 1)
        self.assertEqual(r300['alternative_checks'][0]['no_other_route'], 1)
        self.assertEqual(r500['linked_facilities'], 2)
        self.assertEqual(r500['by_type'], {'day': 1, 'rehab': 1})
        self.assertEqual(r500['alternative_checks'][0]['lower_meets'], 1)
        self.assertEqual(r500['alternative_checks'][0]['uncertain'], 1)
        self.assertEqual(r500['alternative_checks'][1]['all_upper_below'], 1)
        self.assertEqual(r500['alternative_checks'][1]['uncertain'], 1)
        self.assertEqual(r500['facilities_with_missing_alternative_supply'], 1)

    def test_duplicate_facility_rejected(self):
        row = dict(facility_id='f', route_ids_300='', route_ids_500='', route_ids_800='')
        with self.assertRaises(ValueError):
            compare([row, row], {'f': 'type'}, [], {})

    def test_duplicate_supply_route_must_not_silently_overwrite(self):
        with self.assertRaises(ValueError):
            index_supply([{'route_id': 'a'}, {'route_id': 'a'}])


if __name__ == '__main__':
    unittest.main()
