import unittest
from src.prepare_spatial import prepare_edges


def station(identifier='001', x='127', y='37.5', virtual='0'):
    return {'정류장ID':identifier, '정류장명':'정류장', '좌표X':x, '좌표Y':y,
            '가상정류장여부':virtual, '정류장이용여부':'1'}


class SpatialPreparationTests(unittest.TestCase):
    def test_duplicate_edges_virtual_and_invalid_coordinates_do_not_enter_coverage(self):
        nodes = [{'노선ID':'009', '노드ID':i, '사용여부':'1'}
                 for i in ['001','001','002','003','004']]
        stations = [station(), station('002',virtual='1'), station('003',x='nan')]
        edges, audit = prepare_edges(nodes, stations, {'009'})
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]['station_id'], '001')
        self.assertEqual(audit['duplicate_edges'], 1)
        self.assertEqual(audit['virtual_station_nodes'], 1)
        self.assertEqual(audit['invalid_coordinate_nodes'], 1)
        self.assertEqual(audit['nodes_not_in_station_master'], 1)

    def test_duplicate_station_ids_fail_instead_of_overwriting(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate station ID'):
            prepare_edges([], [station(),station()], set())
