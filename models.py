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

"""Defines models for the PubSchool demo application."""

__author__ = 'api.roman.public@gmail.com (Roman Nurik)'

from google.appengine.ext import db

from geo.geomodel import GeoModel

import geocoder


class Listing(GeoModel):
  """A location-aware model entities.
  
  See http://nces.ed.gov/ccd/psadd.asp for details on attributes.
  """
  address = db.PostalAddressProperty()
  price = db.FloatProperty()
  baths = db.FloatProperty()
  beds = db.FloatProperty()
  size = db.FloatProperty()
  phone_number = db.StringProperty()
  comments = db.StringProperty(multiline=True)
  property_type =  db.StringProperty()
  amenities = db.StringProperty()
  author = db.UserProperty()
  createDate = db.DateTimeProperty(auto_now_add=True)
  lastUpdateDate = db.DateTimeProperty(auto_now_add=True)
  status = db.StringProperty()
  tag = db.CategoryProperty()
  photo = db.BlobProperty()
  
  @staticmethod
  def public_attributes():
    """Returns a set of simple attributes on listing entities."""
    return [
      'address', 'price', 'baths', 'beds', 'size', 'phone_number', 'comments', 'property_type', 'amenities', 'author', 'status'
    ]
    
  def set_location(self):
      if address:
          pts = geocoder.query()
          if pts and len(pts) >= 2:
              self.location = db.GeoPt()
              self.location.lat = pts[0]
              self.location.lon = pts[1]

  def _get_latitude(self):
    return self.location.lat if self.location else None

  def _set_latitude(self, lat):
    if not self.location:
      self.location = db.GeoPt()

    self.location.lat = lat

  latitude = property(_get_latitude, _set_latitude)

  def _get_longitude(self):
    return self.location.lon if self.location else None

  def _set_longitude(self, lon):
    if not self.location:
      self.location = db.GeoPt()

    self.location.lon = lon

  longitude = property(_get_longitude, _set_longitude)
