import unittest

from src.facility_types import audit_types


def master(identifier,kind):
    return {'시설코드':identifier,'시설종류명(시설유형)':kind}


def detail(identifier,lower='.2',upper='.8'):
    return dict(facility_id=identifier,**{prefix+str(radius):value for radius in [300,500,800]
                 for prefix,value in [('best_route_share_lower_',lower),('best_route_share_upper_',upper)]})


class FacilityTypeTests(unittest.TestCase):
    def test_unlinked_facilities_remain_in_each_type_denominator(self):
        result=audit_types([master('a','복지관'),master('b','복지관'),master('c','수어센터')],
                           [detail('a'),detail('c','.6','.9')])
        self.assertEqual(result['source_facilities'],3)
        group=next(g for g in result['by_type'] if g['facility_type']=='복지관')
        self.assertEqual((group['source_facilities'],group['linked_candidates'],group['not_linked']), (2,1,1))
        self.assertEqual(group['by_radius'][0]['uncertain'],1)

    def test_no_route_and_below_threshold_are_different(self):
        result=audit_types([master('a','복지관'),master('b','복지관')],
                           [detail('a','',''),detail('b','0','.49')])
        group=result['by_type'][0]['by_radius'][0]
        self.assertEqual(group['no_nearby_route'],1)
        self.assertEqual(group['upper_bound_below'],1)

    def test_duplicate_unknown_ids_and_invalid_bounds_fail(self):
        with self.assertRaises(ValueError):audit_types([master('a','복지관')],[detail('missing')])
        with self.assertRaises(ValueError):audit_types([master('a','복지관')],[detail('a'),detail('a')])
        with self.assertRaises(ValueError):audit_types([master('a','복지관')],[detail('a','.9','.2')])
        with self.assertRaises(ValueError):audit_types([master('a','복지관')],[detail('a','','.2')])

    def test_missing_bound_columns_are_not_no_route_observations(self):
        with self.assertRaises(ValueError):
            audit_types([master('a','복지관')],[{'facility_id':'a'}])
        for field in ['best_route_share_lower_300','best_route_share_upper_500']:
            row=detail('a','','')
            del row[field]
            with self.assertRaises(ValueError):
                audit_types([master('a','복지관')],[row])
        row=detail('a',None,None)
        with self.assertRaises(ValueError):
            audit_types([master('a','복지관')],[row])


if __name__=='__main__':unittest.main()
