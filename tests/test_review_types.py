import unittest

from src.review_types import classify, analyse


class ReviewTypesTests(unittest.TestCase):
    def test_boundary_and_missingness(self):
        self.assertEqual(classify(0, 3, 10, 30), 'information_needed')
        self.assertEqual(classify(3, 0, 10, 30), 'lower_meets')
        self.assertEqual(classify(1, 1, 10, 30), 'low_composition')
        self.assertEqual(classify(1, 1, 10, 30, True), 'operational_constraint')
        with self.assertRaises(ValueError):
            classify(1, 2, 2, 50)

    def test_pool_counts_not_daily_percentages_and_keep_constraint_separate(self):
        source = {'by_route_day': [
            dict(route_id='a', route_name='A', records=1, low_floor_records=1, regular_records=0, unknown_records=0),
            dict(route_id='a', route_name='A', records=9, low_floor_records=0, regular_records=9, unknown_records=0),
            dict(route_id='b', route_name='B', records=10, low_floor_records=0, regular_records=9, unknown_records=1),
        ]}
        result = analyse(source, {'matched_routes': [{'route_id': 'b', 'primary_constraint': 'road'}]})
        self.assertEqual(result['route_count'], 2)
        self.assertEqual(result['thresholds'][0]['counts']['low_composition'], 1)
        self.assertEqual(result['thresholds'][0]['counts']['operational_constraint'], 1)
        self.assertEqual(result['routes'][0]['lower_bound'], .1)
        self.assertEqual(len(result['stable_low_below_30']), 2)


if __name__ == '__main__':
    unittest.main()
