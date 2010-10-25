import datetime
import os
import sys

from google.appengine.ext import db
from google.appengine.tools.bulkloader import Loader

sys.path.append('../..')
import models

class ListingLoader(Loader):
  def __init__(self):
    fail_vals = ['M', 'N', '-1', '-2']
    grade_level_fail_vals = fail_vals + ['UG', '00']
    
    def unicode_str(s):
      return s.decode('utf8', 'ignore')
    
    def ccd_str(s):
      if s in fail_vals:
        return None
      
      return unicode_str(s)
    
    def ccd_int(s):
      if s in fail_vals:
        return None
      
      return int(s)
    
    def lat_lon(s):
      lat, lon = [float(v) for v in s.split(',')]
      return db.GeoPt(lat, lon)
      
      lo, hi = [_grade_level(v) for v in s.split(',')]
      return range(lo, hi + 1) if lo is not None and hi is not None else []
    
    dummy = lambda x: None
    
    Loader.__init__(self, 'Listing',
                    [('id', unicode_str),
                     ('title', unicode_str),
					 ('comments', unicode_str),
					 ('mainPhoto', unicode_str),
                     ('address', ccd_str),
                     ('city', ccd_str),
                     ('state', ccd_str),
                     ('zip_code', ccd_int),
                     ('_dummy', dummy), # skip zip+4
                     ('price', ccd_int),
                     ('phone_number', ccd_str),
                     ('locale_code', ccd_int),
                     ('property_type', ccd_int),
                     ('school_level', ccd_int),
                     ('_dummy', dummy), # skip highest_grade_level
                     ('location', lat_lon), # set lat and lon
                     ('_dummy', dummy), # skip longitude
                     ('_dummy', dummy), # skip accuracy
                     ])

  def create_entity(self, values, key_name=None, parent=None):
    return super(ListingLoader, self).create_entity(values, key_name)

  def handle_entity(self, entity):
    entity.update_location()
    return entity


l = ListingLoader()
l["address"] = "felipe"
l.create_entity(null,"id")