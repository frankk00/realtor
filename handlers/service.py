#!/usr/bin/python2.5
#
# Copyright 2009 Roman Nurik
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Service /s/* request handlers."""

__author__ = 'api.roman.public@gmail.com (Roman Nurik)'

import os
import sys
import wsgiref.handlers

from django.utils import simplejson

from google.appengine.ext import db
from google.appengine.ext import webapp

from geo import geotypes

from models import Listing


def _merge_dicts(*args):
  """Merges dictionaries right to left. Has side effects for each argument."""
  return reduce(lambda d, s: d.update(s) or d, args)


class SearchService(webapp.RequestHandler):
  """Handler for public school search requests."""
  def get(self):
    def _simple_error(message, code=400):
      self.error(code)
      self.response.out.write(simplejson.dumps({
        'status': 'error',
        'error': { 'message': message },
        'results': []
      }))
      return None
      
    
    self.response.headers['Content-Type'] = 'application/json'
    query_type = self.request.get('type')
    user = self.request.get('user');
    
    if not query_type in ['proximity', 'bounds', 'user', 'default']:
      return _simple_error('type parameter must be '
                           'one of "proximity", "bounds", "user".',
                           code=400)
    
    if query_type == 'proximity':
      try:
        center = geotypes.Point(float(self.request.get('lat')),
                                float(self.request.get('lon')))
      except ValueError:
        return _simple_error('lat and lon parameters must be valid latitude '
                             'and longitude values.')
    elif query_type == 'bounds':
      try:
        bounds = geotypes.Box(float(self.request.get('north')),
                              float(self.request.get('east')),
                              float(self.request.get('south')),
                              float(self.request.get('west')))
      except ValueError:
        return _simple_error('north, south, east, and west parameters must be '
                             'valid latitude/longitude values.')
    
    max_results = 100
    if self.request.get('maxresults'):
      max_results = int(self.request.get('maxresults'))
    
    max_distance = 8000000 # 80 km ~ 50 mi
    if self.request.get('maxdistance'):
      max_distance = float(self.request.get('maxdistance'))

      
    results = []
    try:
      # Can't provide an ordering here in case inequality filters are used.
      base_query = Listing.all()
      
      #if property_type:
        #base_query.filter('property_type =', property_type)
      
      # Natural ordering chosen to be public school enrollment.
      #base_query.order('-')
      
      if query_type == 'user':
          query_type = 'bounds';
          maxresults = 2000;
          bounds = geotypes.Box(float(46.70973594407157),
                              float(-73.2568359375),
                              float(25.681137335685307),
                              float(-127.44140624999999))
      
      # Perform proximity or bounds fetch.
      if query_type == 'proximity':
        results = Listing.proximity_fetch(
            base_query,
            center, max_results=max_results, max_distance=max_distance)
      elif query_type == 'bounds':
        results = Listing.bounding_box_fetch(
            base_query,
            bounds, max_results=max_results)
      
      public_attrs = Listing.public_attributes()
      
      results_obj = [
          _merge_dicts({
            'lat': result.location.lat,
            'lng': result.location.lon,
            },
            dict([(attr, getattr(result, attr))
                  for attr in public_attrs]))
          for result in results]

      self.response.out.write(simplejson.dumps({
        'status': 'success',
        'results': results_obj
      }))
    except:
      return _simple_error(str(sys.exc_info()[1]), code=500)


def main():
  application = webapp.WSGIApplication([
      ('/s/search', SearchService),
      ],
      debug=('Development' in os.environ['SERVER_SOFTWARE']))
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()
