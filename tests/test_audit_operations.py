import csv
import io
import unittest

from src.audit_operations import audit_operations


class OperationsAuditTests(unittest.TestCase):
    def test_bom_ids_missing_distances_and_duplicate_candidates(self):
        stream = io.StringIO()
        writer = csv.writer(stream)
        writer.writerow(['기준일', '운행순번', '버스ID', '노선ID', '운행거리', 'SSTTN_DT'])
        writer.writerows([
            ['\ufeff20261013', '1', '\ufeff001', '009', '1000', '20261013060000'],
            ['20261013', '1', '001', '009', '1000', '20261013060000'],
            ['20261014', '2', '002', '010', '0', '20261014060000'],
            ['20261014', '3', '002', '010', '', '20261014070000'],
            ['20261014', '4', '002', '010', '-1', '20261014080000'],
            ['20261014', '5', '002', '010', 'bad', '20261014090000'],
        ])
        stream.seek(0)
        result = audit_operations(stream)
        self.assertEqual(result['row_count'], 6)
        self.assertEqual(result['vehicle_count'], 2)
        self.assertEqual(result['route_count'], 2)
        self.assertEqual(result['dates'], {'20261013': 2, '20261014': 4})
        self.assertEqual(result['duplicate_candidate_rows'], 1)
        self.assertEqual(result['distance']['positive_rows'], 2)
        self.assertEqual(result['distance']['zero_rows'], 1)
        self.assertEqual(result['distance']['negative_rows'], 1)
        self.assertEqual(result['distance']['missing_rows'], 1)
        self.assertEqual(result['distance']['invalid_rows'], 1)
        self.assertEqual(result['distance']['positive_sum_source_units'], 2000)
        self.assertEqual(result['distance']['unit_status'], 'unverified')

    def test_missing_required_column_fails_explicitly(self):
        with self.assertRaisesRegex(ValueError, 'Missing required columns'):
            audit_operations(io.StringIO('基準,other\n1,2\n'))


if __name__ == '__main__':
    unittest.main()
