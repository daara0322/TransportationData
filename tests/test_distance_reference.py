import unittest
from src.distance_reference import audit_reference, coordinate_check


def node(seq, identifier, distance, route='009'):
    return {'노선ID':route,'노드순번':str(seq),'노드ID':identifier,
            '구간거리누계':str(distance)}


def record(start='01', end='02', start_seq='1', end_seq='2', distance='100'):
    return {'노선ID':'009','출발정류장ID':start,'최종정류장ID':end,
            '출발정류장순번':start_seq,'최종정류장순번':end_seq,'운행거리':distance}


class DistanceReferenceTests(unittest.TestCase):
    def test_identity_requires_route_sequence_and_node_id_and_ambiguity_is_visible(self):
        nodes=[node(1,'01',0),node(2,'02',100),node(2,'02',101),node(3,'03',200)]
        rows=[record(end='03',end_seq='3',distance='200'), record(),
              record(end='wrong',end_seq='3')]
        result=audit_reference(rows,nodes,{'009'})
        self.assertEqual(result['unique_reference_records'],1)
        self.assertEqual(result['ambiguous_reference_records'],1)
        self.assertEqual(result['missing_reference_records'],1)
        self.assertEqual(result['reported_matches_reference_within_one_source_unit'],1)

    def test_negative_and_stationary_distances_are_not_repaired_or_dropped(self):
        nodes=[node(1,'01',0),node(2,'02',100)]
        rows=[record(start='02',end='01',start_seq='2',end_seq='1',distance='-100'),
              record(end='01',end_seq='1',distance='0')]
        result=audit_reference(rows,nodes,{'009'})
        self.assertEqual(result['reported_negative_records'],1)
        self.assertEqual(result['negative_with_decreasing_reference'],1)
        self.assertEqual(result['reported_zero_same_endpoint_records'],1)
        self.assertEqual(result['reported_matches_reference_within_one_source_unit'],2)

    def test_coordinate_ratio_is_evidence_not_a_confirmed_unit(self):
        nodes=[node(1,'01',0),node(2,'02',90)]
        stations=[{'정류장ID':'01','좌표X':'127','좌표Y':'37.5'},
                  {'정류장ID':'02','좌표X':'127.001','좌표Y':'37.5'}]
        result=coordinate_check(nodes,stations,{'009'})
        self.assertEqual(result['positive_local_segments'],1)
        self.assertGreater(result['reference_units_per_geodesic_metre']['median'],.9)
        self.assertLess(result['reference_units_per_geodesic_metre']['median'],1.2)
        self.assertFalse(result['official_distance_unit_confirmed'])

    def test_zero_or_invalid_coordinate_segments_do_not_support_a_scale(self):
        nodes=[node(1,'01',0),node(2,'02',100)]
        stations=[{'정류장ID':'01','좌표X':'127','좌표Y':'37.5'},
                  {'정류장ID':'02','좌표X':'127','좌표Y':'37.5'}]
        result=coordinate_check(nodes,stations,{'009'})
        self.assertEqual(result['positive_local_segments'],0)
        self.assertIsNone(result['reference_units_per_geodesic_metre']['median'])
