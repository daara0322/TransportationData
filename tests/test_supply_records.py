import unittest

from src.supply_records import summarize_supply


def route(route_id='009', name='100', route_type='3', master_name=None):
    return dict(route_id=route_id, candidate_name=name, master_name=master_name or name,
                master_found=True, route_type=route_type)


def record(vehicle='001', run='1', distance='1000', route_id='009'):
    return {'기준일': '\ufeff20261013', '노선ID': route_id, '버스ID': vehicle,
            '운행순번': run, 'SSTTN_DT': '20261013060000', '운행거리': distance,
            '출발정류장ID': '01', '최종정류장ID': '02'}


class SupplyRecordTests(unittest.TestCase):
    def test_dedup_unknown_bounds_and_distance_flags_do_not_change_denominator(self):
        rows = [record(), record(), record('002', '2', '0'), record('003', '3', '-1')]
        snapshot = {'records': [dict(route_id='009', vehicle_id='001', low_floor=True),
                                dict(route_id='009', vehicle_id='002', low_floor=False),
                                dict(route_id='010', vehicle_id='003', low_floor=True)]}
        result = summarize_supply(rows, snapshot, {'routes': [route()]})
        totals = result['totals']
        self.assertEqual(result['source_rows'], 4)
        self.assertEqual(result['duplicate_candidate_rows_excluded'], 1)
        self.assertEqual(totals['records'], 3)
        self.assertEqual(totals['low_floor_records'], 1)
        self.assertEqual(totals['regular_records'], 1)
        self.assertEqual(totals['unknown_records'], 1)
        self.assertAlmostEqual(totals['low_floor_record_share_lower_bound'], 1/3)
        self.assertAlmostEqual(totals['low_floor_record_share_upper_bound'], 2/3)
        self.assertEqual(totals['distance_positive_records'], 1)
        self.assertEqual(totals['distance_zero_records'], 1)
        self.assertEqual(totals['distance_negative_records'], 1)

    def test_scope_excludes_missing_mismatched_and_other_types(self):
        missing = dict(route('010'), master_found=False)
        mismatch = route('011', master_name='101')
        routes = [route(), missing, mismatch, route('012', route_type='6')]
        rows = [record(route_id=x) for x in ['009', '010', '011', '012', '013']]
        result = summarize_supply(rows, {'records': []}, {'routes': routes})
        self.assertEqual(result['eligible_routes'], 1)
        self.assertEqual(result['outside_scope_rows'], 4)
        self.assertEqual(result['totals']['unknown_records'], 1)

    def test_conflicting_types_unknown_and_night_tag_is_retained(self):
        snapshot = {'records': [dict(route_id='009', vehicle_id='001', low_floor=True),
                                dict(route_id='009', vehicle_id='001', low_floor=False)]}
        result = summarize_supply([record()], snapshot, {'routes': [route(name='N10')]})
        self.assertEqual(result['totals']['unknown_records'], 1)
        self.assertEqual(result['by_route_day'][0]['service_group'], 'night_name')

    def test_missing_identity_does_not_create_a_match(self):
        result = summarize_supply([record(vehicle='')], {'records': []}, {'routes': [route()]})
        self.assertEqual(result['invalid_identity_rows_excluded'], 1)
        self.assertEqual(result['totals']['records'], 0)
        self.assertIsNone(result['totals']['low_floor_record_share_lower_bound'])
