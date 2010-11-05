#!/usr/bin/python2.5
#
# Copyright 2010 Felipe Oliveira
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


__author__ = 'felipera@gmail.com Felipe Oliveira'

import os
import os.path
import wsgiref.handlers

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

from google.appengine.ext.db import djangoforms

from models import Listing

from google.appengine.ext import db

import logging

from urllib import quote
from google.appengine.api import urlfetch

import geocoder

import datetime
  
  
class ListingForm(djangoforms.ModelForm):
    class Meta:
        model = Listing
        exclude = ['added_by','location_geocells', 'location']
        
    """
    def save(self):
        if not self.key():
            self.createDate = datetime.date.today()
        self.updated = datetime.datetime.today()
        super(Listing, self).save()
    """

  
class ListingFormPage(webapp.RequestHandler):
    def get2(self):
        template_file = "../templates/add.html"
        self.response.out.write(template.render(
          os.path.join(os.path.dirname(__file__), template_file),
          {'current_user': users.get_current_user()}))
    
    def get(self):
        self.response.out.write('<html><body>'
                                '<form method="POST" '
                                'action="/add">'
                                '<table>')
        # This generates our shopping list form and writes it in the response
        self.response.out.write(ListingForm())
        self.response.out.write('</table>'
                                '<input type="submit">'
                                '</form></body></html>')
        
    def post(self):
        data = ListingForm(data=self.request.POST)
        if data:
            logging.info("Data: %s" % data)
            logging.info(vars(data))
            
            geoPoint = None
            g = geocoder.Geocoder()
            pts = g.query(self.request.POST.get('address'))
            if pts and len(pts) >= 2:
                geoPoint = db.GeoPt(pts[0], pts[1])
            logging.info( "Using lat %s and long %s" % (pts[0], pts[1]) )
            
            # Save the data, and redirect to the view page
            entity = None
            
            photo = self.request.get("photo")
            if photo:
                entity.photo = db.Blob(photo)
            
            entity = data.save(commit=False)
            entity.location = geoPoint
            entity.update_location()
            entity.author = users.get_current_user()
            entity.put()
            
            self.redirect('/?success=yes')
        else:
            # Reprint the form
            self.response.out.write('<html><body>'
                                    '<form method="POST" '
                                    'action="/listing/add">'
                                    '<table>')
            self.response.out.write(data)
            self.response.out.write('</table>'
                                    '<input type="submit">'
                                    '</form></body></html>')
            
class ListingEditPage(webapp.RequestHandler):
    def get(self):
        id = int(self.request.get('id'))
        item = Listing.get(db.Key.from_path('Listing', id))
        self.response.out.write('<html><body>'
                                '<form method="POST" '
                                'action="/edit">'
                                '<table>')
        self.response.out.write(ListingForm(instance=item))
        self.response.out.write('</table>'
                                '<input type="hidden" name="id" value="%s">'
                                '<input type="submit">'
                                '</form></body></html>' % id)
        
    def post(self):
      id = int(self.request.get('id'))
      item = Listing.get(db.Key.from_path('Listing', id))
      data = ListingForm(data=self.request.POST, instance=item)
      if data.is_valid():
          # Save the data, and redirect to the view page
          entity = data.save(commit=False)
          entity.added_by = users.get_current_user()
          entity.put()
          self.redirect('/list')
      else:
          # Reprint the form
          self.response.out.write('<html><body>'
                                  '<form method="POST" '
                                  'action="/edit">'
                                  '<table>')
          self.response.out.write(data)
          self.response.out.write('</table>'
                                  '<input type="hidden" name="id" value="%s">'
                                  '<input type="submit">'
                                  '</form></body></html>' % id)
          
          
class ListingDetailsPage(webapp.RequestHandler):
    def get (self):
        id = int(self.request.get('id'))
        item = Listing.get(db.Key.from_path('Listing', id))
        self.response.out.write('Listing: %s' % vars(item));
