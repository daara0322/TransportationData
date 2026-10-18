import unittest
from src.audit_dispatch import audit_dispatch


def station(seq, arrival, departure):
    return {'기준일': '20261013', '노선ID': '009', '운행순번': '1',
            '운행계획ID': '01', '정류장순번': str(seq),
            '도착일시': arrival, '출발일시': departure}


class DispatchAuditTests(unittest.TestCase):
    def test_regular_steps_and_dwell_are_diagnostics_not_observed_headways(self):
        rows = [station(1, '20261013060000', '20261013060000'),
                station(2, '20261013061200', '20261013061220'),
                station(3, '20261013062400', '20261013062420')]
        vehicles = [{'기준일':'20261014', '노선ID':'009', '운행순번':'1', '운행계획ID':'01'}]
        result = audit_dispatch(rows, vehicles)
        self.assertEqual(result['matched_station_groups'], 0)
        self.assertEqual(result['constant_interval_groups_with_at_least_three_rows'], 1)
        self.assertEqual(result['adjacent_arrival_differences_seconds'], {'720':2})
        self.assertEqual(result['departure_minus_arrival_seconds'], {'0':1, '20':2})
        self.assertFalse(result['observed_headway_analysis_ready'])

    def test_backward_invalid_times_and_duplicate_vehicle_keys_stay_visible(self):
        rows = [station(1, '20261013061200', '20261013061220'),
                station(2, '20261013060000', '20261013060020'),
                station(3, 'bad', 'bad')]
        v = {'기준일':'20261013', '노선ID':'009', '운행순번':'1', '운행계획ID':'01'}
        result = audit_dispatch(rows, [v,v])
        self.assertEqual(result['backward_adjacent_arrivals'], 1)
        self.assertEqual(result['invalid_adjacent_time_pairs'], 1)
        self.assertEqual(result['vehicle_duplicate_run_keys'], 1)
        self.assertEqual(result['matched_station_groups'], 1)
