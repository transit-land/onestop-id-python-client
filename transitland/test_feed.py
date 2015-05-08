"""Test Feed."""
import unittest
import tempfile

import util
from feed import Feed

class TestFeed(unittest.TestCase):
  expect = {
    'feedFormat': 'gtfs',
    'name': 'test',
    'onestopId': 'f-9qs-test',
    'operatorsInFeed': [
      {'gtfsAgencyId': 'demotransitauthority',
      'onestopId': 'o-9qs-demotransitauthority'}
    ],
    'sha1': '4e5e6a2668d12cca29c89a969d73e05e625d9596',
    'tags': {},
    'url': None
  }
  
  def _sanity(self, entity):
    """Sanity check after load from_json() / from_gtfs()"""
    assert entity.onestop() == self.expect['onestopId']
    assert entity.id() == self.expect['onestopId']
    assert entity.url() == self.expect['url']
    assert entity.sha1() == self.expect['sha1']
    assert entity.feedFormat() == self.expect['feedFormat']
    assert entity.name() == self.expect['name']
  
  # Feed implementes geohash(), so we will test many Entity base methods here.
  def test_id(self):
    entity = util.example_feed()
    assert entity.id() == self.expect['onestopId']
  
  def test_onestop(self):
    entity = util.example_feed()
    assert entity.onestop() == self.expect['onestopId']

  def test_onestop_maxlen(self):
    entity = util.example_feed()
    entity.data['name'] = 'maximumlength' * 10
    assert len(entity.data['name']) > util.ONESTOP_LENGTH
    assert len(entity.onestop()) <= util.ONESTOP_LENGTH

  # Other Entity base methods that only make sense to test here...
  def test_json(self):
    # Check result looks like self.expect.
    entity = util.example_feed()
    data = entity.json()
    for k in ('onestopId','name','url','sha1','feedFormat'):
      assert data[k] == self.expect[k]
    assert len(data['operatorsInFeed']) == 1
    assert 'o-9qs-demotransitauthority' in data['operatorsInFeed']
  
  def test_from_json(self):
    # TODO: more thorough testing here...
    entity = util.example_feed()
    roundtrip = Feed.from_json(entity.json())
    self._sanity(roundtrip)

  def test_json_datastore(self):
    # Alternate JSON representation, for datastore...
    entity = util.example_feed()
    data = entity.json_datastore()
    assert 'identifiers' not in data
    assert 'features' not in data
    # assert data['tags']
    assert data['operatorsInFeed']
    # check without rels...
    data = entity.json_datastore(rels=False)
    assert 'serves' not in data
    assert 'doesNotServe' not in data
    assert 'servedBy' not in data
    assert 'notServedBy' not in data

  # Geometry and point are not implemented...
  def test_geometry(self):
    # TODO: Feed doesn't have geometry... convex hull like operator?
    entity = util.example_feed()
    assert entity.geometry() is None
    
  def test_point(self):
    entity = util.example_feed()
    with self.assertRaises(NotImplementedError):
      entity.point()
      
  def test_bbox(self):
    entity = util.example_feed()
    with self.assertRaises(NotImplementedError):
      entity.bbox()
  
  # Test OnestopFeed methods
  def test_url(self):
    # TODO: feed doesn't have url...
    entity = util.example_feed()
    assert entity.url() == self.expect['url']
    
  def test_sha1(self):
    entity = util.example_feed()
    assert entity.sha1() == self.expect['sha1']

  def test_feedFormat(self):
    entity = util.example_feed()
    assert entity.feedFormat() == self.expect['feedFormat']    
  
  # Test fetching...
  def test_download(self):
    # TODO: feed doesn't have url...
    entity = util.example_feed()
    f = tempfile.NamedTemporaryFile()
    with self.assertRaises(ValueError):
      entity.download(f.name)
  
  # Load / dump
  def test_from_gtfs(self):
    entity = util.example_feed()
    self._sanity(entity)
    # Check operators...
    assert len(entity.operators()) == 1
    o = list(entity.operators())[0]
    assert o.onestop() == 'o-9qs-demotransitauthority'
    assert len(o.routes()) == 5
    assert len(o.stops()) == 9

  # Graph
  def test_operators(self):
    entity = util.example_feed()
    assert len(entity.operators()) == len(self.expect['operatorsInFeed'])

  def test_operator(self):
    entity = util.example_feed()
    for i in self.expect['operatorsInFeed']:
      assert entity.operator(i['onestopId'])
    with self.assertRaises(ValueError):
      entity.operator('none')

  def test_operatorsInFeed(self):
    entity = util.example_feed()
    o = entity.operatorsInFeed()
    assert len(o) == 1
    assert 'o-9qs-demotransitauthority' in o
    
  def test_routes(self):
    entity = util.example_feed()
    routes = entity.routes()
    assert len(routes) == 5

  def test_route(self):
    entity = util.example_feed()
    for i in entity.routes():
      assert entity.route(i.onestop())
    with self.assertRaises(ValueError):
      entity.route('none')
    
  def test_stops(self):
    entity = util.example_feed()
    stops = entity.stops()
    assert len(stops) == 9

  def test_stop(self):
    entity = util.example_feed()
    for i in entity.stops():
      assert entity.stop(i.onestop())
    with self.assertRaises(ValueError):
      entity.stop('none')
    