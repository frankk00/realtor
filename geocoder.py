import re
import urllib
import logging
import time
from datetime import datetime
from google.appengine.api import urlfetch
from versioned_memcache import memcache
from google.appengine import api

def parse_geo_response(res):
  if "," not in res:
    return 999, 999, 999, 999
  try:
    code, zoom, lat, lng = res.split(",")
    return code, zoom, lat, lng
  except:
    logging.warning('geocode.geocode unparseable response: ' + res[0:80])
    return 999, 999, 999, 999


def is_latlong(instr):
  """check whether a string is a valid lat-long."""
  return (re.match(r'^\s*[0-9.+-]+\s*,\s*[0-9.+-]+\s*$', instr) != None)
  

def is_latlongzoom(instr):
  """check whether a string is a valid lat-long-zoom."""
  return (re.match(r'^\s*[0-9.+-]+\s*,\s*[0-9.+-]+\s*,\s*[0-9.+-]+\s*$', instr) != None)


def geocode(addr, usecache=False, retrying = False):
  """convert a human-readable address into a "lat,long" value (string)."""
  loc = addr.lower().strip()

  # already geocoded-- just return
  if is_latlongzoom(loc):
    return loc

  if is_latlong(loc):
    # regexp allow missing comma
    # TODO: pick a smart default zoom, depending on population density.
    return loc + ",4"

  loc = re.sub(r'^[^0-9a-z]+', r'', loc)
  loc = re.sub(r'[^0-9a-z]+$', r'', loc)
  loc = re.sub(r'\s\s+', r' ', loc)

  memcache_key = "geocode:" + loc
  val = memcache.get(memcache_key)
  if usecache and val:
    logging.info("geocode: cache hit loc=" + loc + " val=" + val)
    return val

  if not retrying:
    params = urllib.urlencode(
      {'q':loc.lower(), 'output':'csv', 'oe':'utf8', 'sensor':'false', 'gl':'us',
       'key':'ABQIAAAAPwa6P0RAONGDnDVWIoz60RS_XVdtR9vJUHoImLNBbcMuXbr6qRRCTJ1XM9Je76qJSqsr_4HKGKJ65A'})
    fetchurl = "http://maps.google.com/maps/geo?%s" % params
    logging.info("geocode: cache miss, trying " + fetchurl)
    fetch_result = urlfetch.fetch(fetchurl)
    if fetch_result.status_code != 200:
      # fail and also don't cache
      return ""

    res = fetch_result.content
    logging.info("geocode: maps responded %s" % res)
    respcode, zoom, lat, lng = parse_geo_response(res)
    if respcode == '200':
      logging.info("geocode: success " + loc)
      val = respcode +"," + zoom + "," + lat+","+lng
      memcache.set(memcache_key, val)
      return val

  if retrying or respcode == '620':
    params = urllib.urlencode(
      {'q':loc.lower(), 
      })
    fetchurl = "http://pipes.appspot.com/geo?%s" % params
    fetch_result = urlfetch.fetch(fetchurl, deadline = api.CONST_MAX_FETCH_DEADLINE)
    res = fetch_result.content
    logging.info("geocode: datastore responded %s" % res)
    respcode, zoom, lat, lng = parse_geo_response(res)
    if respcode == '200':
      val = lat+","+lng+","+zoom
      memcache.set(memcache_key, val)
      return val
    if respcode == '620' and not retrying:
      logging.info("geocode: retrying " + loc)
      return geocode(addr, usecache, True)

  logging.info("geocode: failed " + loc)
  return ""
 
class Geocoder():
	
	api_key = "ABQIAAAAPwa6P0RAONGDnDVWIoz60RS_XVdtR9vJUHoImLNBbcMuXbr6qRRCTJ1XM9Je76qJSqsr_4HKGKJ65A";
	
	root_url = "http://maps.google.com/maps/geo?"
	return_codes = {'200':'SUCCESS',
					'400':'BAD REQUEST',
					'500':'SERVER ERROR',
					'601':'MISSING QUERY',
					'602':'UNKOWN ADDRESS',
					'603':'UNAVAILABLE ADDRESS',
					'604':'UNKOWN DIRECTIONS',
					'610':'BAD KEY',
					'620':'TOO MANY QUERIES'
					}
	
	def geocode(self, address):
		x = geocode(address);
		y = parse_geo_response(x)
		return [ y[2], y[3] ]

	def query(self, address):
		return self.geocode(address)
        
def main():
	geocoder = Geocoder();
	x = geocoder.query("22192hh Majestic Woods Way Boca Raton, FL 33428");
	print "start";
	print x;
	print "end";
            
if __name__ == '__main__':
  main()