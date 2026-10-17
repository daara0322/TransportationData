import io
import unittest
from src.link_positions import summarize_linkage


class LinkageTests(unittest.TestCase):
    def test_unknown_and_other_route_cannot_become_regular_bus(self):
        source = io.StringIO('기준일,운행순번,버스ID,노선ID,運行\n20261013,1,001,009,1\n20261013,2,002,009,1\n20261013,3,003,009,1\n20261013,1,001,010,1\n')
        snapshot = {'statuses': [{'route_id':'009','status':'ok'}, {'route_id':'010','status':'no_data'}],
                    'records': [{'vehicle_id':'001','route_id':'009','low_floor':True},
                                {'vehicle_id':'002','route_id':'009','low_floor':None}]}
        result = summarize_linkage(source, snapshot)
        routes = {r['route_id']: r for r in result['routes']}
        self.assertEqual(routes['009']['historical_vehicles'], 3)
        self.assertEqual(routes['009']['classified_vehicles'], 1)
        self.assertEqual(routes['009']['low_floor_vehicles'], 1)
        self.assertEqual(routes['009']['regular_vehicles'], 0)
        self.assertEqual(routes['009']['unclassified_vehicles'], 2)
        self.assertEqual(routes['010']['classified_vehicles'], 0)

    def test_conflicting_classifications_are_not_silently_selected(self):
        source = io.StringIO('기준일,운행순번,버스ID,노선ID\n20261013,1,001,009\n')
        snapshot = {'statuses':[{'route_id':'009','status':'ok'}], 'records':[
            {'vehicle_id':'001','route_id':'009','low_floor':True},
            {'vehicle_id':'001','route_id':'009','low_floor':False}]}
        result = summarize_linkage(source, snapshot)
        self.assertEqual(result['conflicting_pairs'], 1)
        self.assertEqual(result['routes'][0]['classified_vehicles'], 0)


if __name__ == '__main__':
    unittest.main()
