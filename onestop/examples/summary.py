import sys
import os
import json

import onestop.gtfs

def summarize(filename):
  d = os.path.dirname(filename)
  if os.path.exists(os.path.join(d, 'status.txt')):
    print "Exists, skipping."
    continue

  # Create OnestopIds for each agency.
  g = onestop.gtfs.GTFSReader(filename)
  for agency in g.agencies():
    try:
      o = agency.onestop()
      print agency['agency_name'], o
    except Exception, e:
      print "Error on agency:", e
      continue

    # Write geojson agency data.
    data = agency.geojson()
    with open(os.path.join(d, '%s.geojson'%o), 'w') as f:
      f.write(json.dumps(data))

  # Write status file.
  with open(os.path.join(d, 'status.txt'), 'w') as f:
    f.write('done')
      
if __name__ == __main__:
  for filename in sys.argv[1:]:
    print "==== %s ===="%filename
    summarize(filename)