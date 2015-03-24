"""Onestop entities."""
import collections
import json
import copy
import re

import util
import errors

import mzgtfs.entities
import mzgeohash

# Regexes
REPLACE_CHAR = [
  # replace &, @, and / with ~
  [r':','~'], 
  [r'&','~'], 
  [r'@','~'],
  [r'\/','~'],
  # replace every other special char
  [r'[^~0-9a-zA-Z]+', '']
]
REPLACE_CHAR = [[re.compile(i[0]), i[1]] for i in REPLACE_CHAR]

REPLACE_ABBR = [
  'street', 
  'st',
  'sts',
  'ctr',
  'center',
  'drive',
  'dr',
  'ave', 
  'avenue', 
  'av',
  'boulevard', 
  'blvd', 
  'road', 
  'rd', 
  'alley', 
  'aly', 
  'way', 
  'parkway', 
  'pkwy', 
  'lane',
  'ln',
  'hwy',
  'court',
  'ct',
]
REPLACE_ABBR = [[re.compile(r'\b%s\b'%i), ''] for i in REPLACE_ABBR]

##### Geohash utility functions #####

def geohash_features(features):
  # Filter stops without valid coordinates...
  points = [feature.point() for feature in features if feature.point()]
  if not points:
    raise errors.OnestopNoPoints("Not enough points.")
  c = centroid_points(points)
  return mzgeohash.neighborsfit(c, points)
  
def centroid_points(points):
  """Return the lon,lat centroid for features."""
  # Todo: Geographic center, or simple average?
  import ogr, osr
  multipoint = ogr.Geometry(ogr.wkbMultiPoint)
  # spatialReference = osr.SpatialReference() ...
  for point in points:
    p = ogr.Geometry(ogr.wkbPoint)
    p.AddPoint(point[1], point[0])
    multipoint.AddGeometry(p)
  point = multipoint.Centroid()
  return (point.GetY(), point.GetX())

##### Entities #####

class OnestopEntity(object):
  """A OnestopEntity."""  
  # OnestopID prefix.
  onestop_type = None

  def __init__(self, name=None, onestop=None, geometry=None, **kwargs):
    """Set name, OnestopID, and geometry."""
    self._name = name
    self._geometry = geometry
    self._onestop = onestop or kwargs.get('onestopId') # equivalent
    self.identifiers = kwargs.get('identifiers', [])
    self.tags = kwargs.get('tags', {})
    self.parents = set()
    self.children = set()
  
  @classmethod
  def from_json(cls, filename):
    raise NotImplementedError
    
  @classmethod
  def from_gtfs(cls, filename):
    raise NotImplementedError

  def pclink(self, parent, child):
    """Create a parent-child relationship."""
    parent.children.add(child)
    child.parents.add(parent)

  def name(self):
    """A reasonable display name for the entity."""
    return self._name
    
  def bbox(self):
    """Return a bounding box for this entity."""
    raise NotImplementedError
  
  def geometry(self):
    """Return a GeoJSON-type geometry for this entity."""
    return self._geometry

  def geohash(self):
    """Return the geohash for this entity."""
    raise NotImplementedError
  
  def json(self):
    """Return a GeoJSON representation of this entity."""
    raise NotImplementedError
    
  # References to GTFS entities.
  def add_identifier(self, identifier, tags):
    """Add original GTFS data."""    
    if identifier in [i['identifier'] for i in self.identifiers]:
      raise errors.OnestopExistingIdentifier(
        "Identifier already present: %s"%identifier
      )
    self.identifiers.append({
      'identifier': identifier,
      'tags': tags
    })
  
  def merge(self, item):
    """Merge identifiers."""
    for i in item.identifiers:
      self.add_identifier(identifier=i['identifier'], tags=i['tags'])
  
  # Onestop methods
  def mangle(self, s):
    """Mangle a string into an Onestop component."""
    s = s.lower()
    for a,b in REPLACE_CHAR:
      s = a.sub(b,s)
    return s    

  def onestop(self, cache=True):
    """Return the OnestopID for this entity."""
    # Cache...
    if cache and self._onestop:
      return self._onestop
    # Create if necessary.
    self._onestop = '%s-%s-%s'%(
      self.onestop_type, 
      self.geohash(), 
      self.mangle(self.name())
    )
    return self._onestop

class OnestopFeed(OnestopEntity):
  """Read and write Onestop Feeds."""
  onestop_type = 'f'
  
  def __init__(self, name=None, onestop=None, geometry=None, **kwargs):
    super(OnestopFeed, self).__init__(
      name=name, 
      onestop=onestop, 
      geometry=geometry,
      **kwargs
    )
    self.url = kwargs.get('url')
    self.sha1 = kwargs.get('sha1')
    self.feedFormat = kwargs.get('feedFormat', 'gtfs')

  def geohash(self):
    return geohash_features(self.stops())

  def json(self):
    return {
      "onestopId": self.onestop(),
      "url": self.url,
      "sha1": self.sha1,
      "feedFormat": self.feedFormat,
      "tags": self.tags,
      "operatorsInFeed": [
        {
          'onestopId': i.onestop(),
          'gtfsAgencyId': i.mangle(i.name())
        }
        for i in self.operators()
      ]
    }

  @classmethod
  def from_gtfs(cls, filename, debug=False, **kw):
    # Create feed
    kw['sha1'] = util.sha1(filename)
    feed = cls(**kw)
    g = mzgtfs.reader.Reader(filename, debug=debug)
    # Load and display information about agencies
    for agency in g.agencies():
      agency.preload()
      oagency = OnestopOperator.from_gtfs(agency, feedid=feed.name())
      feed.pclink(feed, oagency)
    return feed
  
  @classmethod
  def from_json(cls, filename):
    with open(filename) as f:
      data = json.load(f)
    return cls(**data)

  def operators(self):
    return self.children
  
  def operatorsInFeed(self):
    return [i.onestop() for i in self.operators()]

  def routes(self):
    routes = set()
    for i in self.operators():
      routes |= i.routes()
    return routes
  
  def stops(self):
    stops = set()
    for i in self.operators():
      stops |= i.stops()
    return stops

  def fetch(self, filename):
    """Download the GTFS feed to a file."""
    urllib.urlretrieve(self.url, filename)

class OnestopOperator(OnestopEntity):
  """Onestop Operator."""
  onestop_type = 'o'
  
  @classmethod
  def from_gtfs(cls, gtfs_agency, feedid='unknown'):
    """Load Onestop Operator from a GTFS Agency."""
    route_counter = 0
    agency = cls(name=gtfs_agency.name())
    agency.add_identifier(gtfs_agency.feedid(feedid), gtfs_agency.data)
    # Group stops
    stops = {}
    for i in gtfs_agency.stops():
      stop = OnestopStop(
        name=i.name(), 
        geometry=i.geometry()
      )
      key = stop.onestop()
      if key not in stops:
        stops[key] = stop
      # Hack to maintain ref to stop
      i._onestop_parent = stops[key]
      stops[key].add_identifier(i.feedid(feedid), i.data)
    # Routes
    routes = {}
    for i in gtfs_agency.routes():
      route = OnestopRoute(
        name=i.name(),
        geometry=i.geometry()
      )
      if not i.stops():
        print "Yikes! No stops! Skipping this route."
        continue
      for j in i.stops():
        route.pclink(route, j._onestop_parent)
      key = route.onestop()
      if key in routes:
        # raise KeyError("Route already exists!: %s"%key)
        # Hack
        print "Route already exists, setting temp fix..."
        route_counter += 1
        route._name = '%s~%s'%(route._name, route_counter)
        route._onestop = None
        key = route.onestop()
        print "set key to:", key
        assert key not in routes
      route.pclink(agency, route)
      route.add_identifier(i.feedid(feedid), i.data)
      routes[key] = route
    # Return agency
    return agency

  @classmethod
  def from_json(cls, filename):
    """Load Onestop Operator from GeoJSON."""
    with open(filename) as f:
      data = json.load(f)
    agency = cls(**data)
    # Add stops
    stops = {}
    for feature in data['features']:
      if feature['onestopId'].startswith('s'):
        stop = OnestopStop(**feature)
        stops[stop.onestop()] = stop
    # Add routes
    for feature in data['features']:
      if feature['onestopId'].startswith('r'):
        route = OnestopRoute(**feature)
        # Get stop by id, add as child.
        for stop in feature['serves']:
          route.pclink(route, stops[stop])
        agency.pclink(agency, route)
    return agency

  def geohash(self):
    return geohash_features(self.stops())
    
  def json(self):
    return {
      'type': 'FeatureCollection',
      'properties': {},
      'name': self.name(),
      'tags': self.tags,
      'identifiers': self.identifiers,
      'onestopId': self.onestop(),
      'serves': [i.onestop() for i in self.stops()],
      'features': [i.json() for i in self.routes() | self.stops()]
    }

  # Agency methods
  def routes(self):
    return self.children
  
  def stops(self):
    stops = set()
    for i in self.routes():
      stops |= i.stops()
    return stops  
        
class OnestopRoute(OnestopEntity):
  onestop_type = 'r'
  
  def geohash(self):
    """Return 10 characters of geohash."""
    return geohash_features(self.stops())

  def json(self):
    return {
      'type': 'Feature',
      'properties': {},
      'geometry': self.geometry(),
      'onestopId': self.onestop(),
      'name': self.name(),
      'tags': self.tags,
      'identifiers': self.identifiers,
      'operatedBy': [i.onestop() for i in self.agencies()][0],
      'serves': [i.onestop() for i in self.stops()],
    }
  
  # Route methods
  def agencies(self):
    return self.parents

  def stops(self):
    return self.children  

class OnestopStop(OnestopEntity):
  onestop_type = 's'
  
  def mangle(self,s):
    """Also replace common road abbreviations."""
    s = s.lower()
    for a,b in REPLACE_ABBR:
      s = a.sub(b,s)
    for a,b in REPLACE_CHAR:
      s = a.sub(b,s)
    return s    

  def geohash(self):
    """Return 10 characters of geohash."""
    return mzgeohash.encode(self.point())[:10]
    
  def json(self):
    return {
      'type': 'Feature',
      'properties': {},
      'geometry': self.geometry(),
      'onestopId': self.onestop(),
      'name': self.name(),
      'tags': self.tags,
      'identifiers': self.identifiers,
      'servedBy': [i.onestop() for i in self.agencies()],
    }

  # Work with other interfaces
  def point(self):
    """Return stop point."""
    return self.geometry()['coordinates']

  # Stop methods
  def agencies(self):
    agencies = set()
    for i in self.parents:
      agencies |= i.parents
    return agencies
