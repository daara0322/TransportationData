import unittest
from src.bus_positions import parse_positions, safe_error_message


class BusPositionsTests(unittest.TestCase):
    def test_types_and_ids_preserved_without_assuming_fuel(self):
        payload = b'''<ServiceResult><msgHeader><headerCd>0</headerCd></msgHeader>
        <msgBody><itemList><vehId>001</vehId><busType>1</busType><dataTm>20261017160000</dataTm></itemList>
        <itemList><vehId>002</vehId><busType>0</busType></itemList>
        <itemList><vehId>003</vehId><busType>9</busType></itemList></msgBody></ServiceResult>'''
        records = parse_positions(payload, '009')
        self.assertEqual([r['low_floor'] for r in records], [True, False, None])
        self.assertEqual(records[0]['vehicle_id'], '001')
        self.assertEqual(records[0]['route_id'], '009')
        self.assertNotIn('fuel', records[0])

    def test_service_failure_is_not_empty_success(self):
        with self.assertRaisesRegex(ValueError, 'API header code: 7'):
            parse_positions(b'<ServiceResult><msgHeader><headerCd>7</headerCd></msgHeader></ServiceResult>', '1')

    def test_no_data_code_four_has_no_classification(self):
        self.assertEqual(parse_positions(b'<ServiceResult><msgHeader><headerCd>4</headerCd></msgHeader></ServiceResult>', '1'), [])

    def test_missing_header_rejected(self):
        with self.assertRaises(ValueError):
            parse_positions(b'<html>gateway failure</html>', '1')

    def test_errors_cannot_print_request_or_credential(self):
        secret = 'secret-placeholder'
        result = safe_error_message(ValueError('http://example/?serviceKey=' + secret))
        self.assertEqual(result, 'Request failed (ValueError)')
        self.assertNotIn(secret, result)


if __name__ == '__main__':
    unittest.main()
