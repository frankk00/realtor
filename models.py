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
from appengine_admin import db_extensions
from google.appengine.api import users
import logging

propertyTypes = ["Single-Family", "Condo", "Loft", "Land", "Commercial", "Mobile"]

class Listing(GeoModel):
  """A location-aware model entities.
  
  See http://nces.ed.gov/ccd/psadd.asp for details on attributes.
  """
  address = db.PostalAddressProperty("Address", required=True)
  price = db.FloatProperty("Price", required=True)
  baths = db.FloatProperty("Baths")
  beds = db.FloatProperty("Beds")
  size = db.FloatProperty("Size")
  description = db.TextProperty("Description")
  propertyType =  db.StringProperty("Property Type", choices=propertyTypes)
  amenities = db.StringListProperty("Amenities")
  author = db.UserProperty("Author", required=True)
  createDate = db.DateTimeProperty("Create Date", required=True, auto_now_add=True)
  lastUpdate = db.DateTimeProperty("Last Update", required=True, auto_now=True)
  tags = db.StringListProperty("Tags")
  portfolio = db.StringProperty("Portfolio Url")
  photo = db.BlobProperty()
  listingAgentName = db.StringProperty("Listing Agent Name")
  listingAgentPhone = db.PhoneNumberProperty("Listing Agent Phone")
  listingAgentEmail = db.EmailProperty("Listing Agent Email");
  listingAgentAddress = db.PostalAddressProperty("Listing Agent Address")
  listingAgentCompany = db.StringProperty("Listing Agent Company")

  def __unicode__(self):
        return "%s %s/%s %s" % (self.address, self.beds. self.baths, self.price)
  
  @staticmethod
  def public_attributes():
    """Returns a set of simple attributes on listing entities."""
    return [
      'address', 'price', 'baths', 'beds', 'size', 'description', 'propertyType', 'listingAgentName', 'listingAgentPhone', 'listingAgentPhone', 'listingAgentCompany', 'listingAgentEmail'
    ]
      
  def _get_author(self):
      return users.get_current_user()
  
  def _set_author(self):
      self.author = users.get_current_user()
      
  author = property(_get_author, _set_author)
    
  def set_location(self):
      logging.info("Set Location for Address: %s" % self.address)
      if self.address:
          r = geocoder.geocode(self.address)
          if not r:
              raise "Cannot find geolocation for address: %s" %s
          pts = r.split(",")
          logging.info("Geocode Lookup Results: %s" % pts)
          if pts and len(pts) >= 2:
              self.location = db.GeoPt(pts[2], pts[3])
              logging.info("Geo Point: %s" % self.location)
              self.update_location()
              
  def getKeyName(self):
      return self.key.name()

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
  
  
class Profile(db.Model):
    owner = db.UserProperty(required=True)
    token = db.StringProperty(required=True)
    secret = db.StringProperty(required=True)

class AuthRequest(db.Model):
    owner = db.UserProperty(required=True)
    request_secret = db.StringProperty()

class Setting(db.Model):
    name = db.StringProperty(required=True)
