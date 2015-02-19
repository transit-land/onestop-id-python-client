"""geohash unit tests."""
import unittest
import os
import json

import gtfs

class TestGTFSReader(unittest.TestCase):
  test_gtfs = os.path.join('examples', 'sample-feed.zip')
  
  def test_readcsv(self):
    expect = {
      'stop_lat': '36.425288', 
      'zone_id': '', 
      'stop_lon': '-117.133162', 
      'stop_url': '', 
      'stop_id': 'FUR_CREEK_RES', 
      'stop_desc': '', 
      'stop_name': 'Furnace Creek Resort (Demo)'
    }
    f = gtfs.GTFSReader(self.test_gtfs)
    stops = list(f.readcsv('stops.txt'))
    found = filter(lambda x:x['stop_id'] == expect['stop_id'], stops)[0]
    for k in expect:
      assert expect[k] == found[k]
    
  def test_stops_centroid(self):
    f = gtfs.GTFSReader(self.test_gtfs)
    centroid = f.stops_centroid()
    expect = (-116.77204833333333, 36.81966833333333)
    self.assertAlmostEqual(centroid[0], expect[0])
    self.assertAlmostEqual(centroid[1], expect[1])

if __name__ == '__main__':
    unittest.main()