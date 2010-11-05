# The MIT License
# 
# Copyright (c) 2008 William T. Katz
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to 
# deal in the Software without restriction, including without limitation 
# the rights to use, copy, modify, merge, publish, distribute, sublicense, 
# and/or sell copies of the Software, and to permit persons to whom the 
# Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER 
# DEALINGS IN THE SOFTWARE.

"""A simple RESTful status framework on Google App Engine

This app's API should be reasonably clean and easily targeted by other 
clients, like a Flex app or a desktop program.
"""

__author__ = 'Kyle Conroy'

import datetime
from datetime import timedelta
from datetime import date
from datetime import datetime
from datetime import time
from dateutil.parser import parse
import string
import re
import os
import cgi
import urllib
import logging
import jsonpickle
import status_images

from wsgiref.handlers import format_date_time
from time import mktime

from google.appengine.ext import webapp
from google.appengine.api import users
from google.appengine.ext import db

from handlers import restful
from utils import authorized
from utils import slugify
import config

def aware_to_naive(d):
    """Convert an aware date to an naive date, in UTC"""
    offset = d.utcoffset()
    if offset:
        d = d.replace(tzinfo=None)
        d = d - offset
    return d

class SearchService(webapp.RequestHandler):
  """Handler for search requests."""
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
      
      # Perform proximity or bounds fetch.
      if query_type == 'proximity':
        results = Listing.proximity_fetch(base_query, center, max_results=max_results, max_distance=max_distance)
      
      elif query_type == 'bounds':
        results = Listing.bounding_box_fetch(base_query, bounds, max_results=max_results)
        
      elif query_type == 'user':
          limit = self.request.get("limit")
          offset = self.request.get("offset")
          if not limit:
              limit = 1000
          else:
              limit = int(limit)
          if not offset:
              offset = 0
          else:
              offset = int(offset)
          results = base_query.fetch(limit, offset);
      
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
        'results': results_obj,
      }))
    except:
      return _simple_error(str(sys.exc_info()[1]), code=500)

class NotFoundHandler(restful.Controller):
    def get(self):
        logging.debug("NotFoundAPIHandler#get")
        self.error(404, "Can't find resouce")

class ServicesListHandler(restful.Controller):
    def get(self, version):
        logging.debug("ServicesListHandler#get")
        if (self.valid_version(version)):
            
            query = Service.all().order('name')
            data = []


            for s in query:
                data.append(s.rest(self.base_url(version)))

            data = { "services": data }

            self.json(data)
            
        else:
            self.error(404, "API Version %s not supported" % version)
            
    @authorized.api("admin")
    def post(self, version):
        logging.debug("ServicesListHandler#post")

        if (self.valid_version(version)):
            
            name = self.request.get('name', default_value=None)
            description = self.request.get('description', default_value=None)
            
            if name and description:
                slug = slugify.slugify(name)
                existing_s = Service.get_by_slug(slug)

                # Update existing resource
                if existing_s:
                    existing_s.description = description
                    existing_s.put()
                    self.json(existing_s.rest(self.base_url(version)))
                # Create new service
                else:
                    s = Service(name=name, slug=slug, description=description)
                    s.put()
                    self.json(s.rest(self.base_url(version)))
            else:
                self.error(400, "Bad Data: Name: %s, Description: %s" % (name, description))
        else:
            self.error(404, "API Version %s not supported" % version)

            
class ServiceInstanceHandler(restful.Controller):
    def get(self, version, service_slug):
        logging.debug("ServiceInstanceHandler#get")
        
        if (self.valid_version(version)):
            service = Service.get_by_slug(service_slug)

            if (service):
                self.json(service.rest(self.base_url(version)))
            else:
                self.error(404, "Service %s does not exist" % service_slug)
        else:
            self.error(404, "API Version %s not supported" % version)
        

    @authorized.api("admin")
    def post(self, version, service_slug):
        logging.debug("ServiceInstanceHandler#post")
        name = self.request.get('name', default_value=None)
        description = self.request.get('description', default_value=None)
        
        if (self.valid_version(version)):
            service = Service.get_by_slug(service_slug)
            if service:
                if description:
                    service.description = description
                
                if name:
                    service.name = name
                
                if name or description:
                    service.put()
                    
                self.json(service.rest(self.base_url(version)))   
            else:
                self.error(404, "Service %s does not exist" % service_slug)
        else:
            self.error(404, "API Version %s not supported" % version)
        
    @authorized.api("admin")
    def delete(self, version, service_slug):
        logging.debug("ServiceInstanceHandler#delete slug=%s" % service_slug)
        
        if (self.valid_version(version)):
            
            service = Service.get_by_slug(service_slug)
            
            if service:
                query = Event.all()
                query.filter('service =', service)
                if query:
                    for e in query:
                        e.delete()

                service.delete()
                self.json(service.rest(self.base_url(version)))
            else:
                self.error(404, "Service %s not found" % service_slug)
        else:
            self.error(404, "API Version %s not supported" % version)





class EventsListHandler(restful.Controller):
    def get(self, version, service_slug):
        logging.debug("StatusesListHandler#get")
        
        if (self.valid_version(version)):
            service = Service.get_by_slug(service_slug)

            if service:
                start = self.request.get('start', default_value=None)
                end = self.request.get('end', default_value=None)
                                 
                query = Event.all()
                query.filter('service =', service)
                        
                if start:
                    try:
                        _start = aware_to_naive(parse(start))
                        query.filter("start >= ", _start)
                    except:
                        self.error(400, "Invalid Date: %s" % start)
                        return

                if end:
                    try:
                        _end  = aware_to_naive(parse(end))
                        query.filter("start <=", _end)
                    except:
                        self.error(400, "Invalid Date: %s" % end)
                        return
                        
                query.order('-start')
                        
                if query:
                    data = []

                    for s in query:
                        data.append(s.rest(self.base_url(version)))

                    data = { "events": data }

                    self.json(data) 
                else:
                    self.error(404, "No events for Service %s" % service_slug)
            else:
                self.error(404, "Service %s not found" % service_slug)
        else:
            self.error(404, "API Version %s not supported" % version)
        

    @authorized.api("admin")
    def post(self, version, service_slug):
        logging.debug("EventsListHandler#post")
        
        if (self.valid_version(version)):
            status_slug = self.request.get("status", default_value=None)
            message = self.request.get("message", default_value=None)
            informational = self.request.get("informational", default_value=None)
            
            if message:
                service = Service.get_by_slug(service_slug)
                if service:
                    
                    if not status_slug:
                        event = service.current_event()
                        if event:
                            status = event.status
                        else:
                            status = Status.default()
                    else:
                        status = Status.get_by_slug(status_slug)

                    if status:
                        e = Event(status=status, service=service,
                                message=message)

                        e.informational = informational and informational == "true"

                        e.put()
                        self.json(e.rest(self.base_url(version)))
                    else:
                        self.error(404, "Status %s not found" % status_slug)
                else:
                    self.error(404, "Service %s not found" % service_slug)
            else:
                self.error(400, "Event message is required")
        else:
            self.error(404, "API Version %s not supported" % version)
        

        
class CurrentEventHandler(restful.Controller):
    def get(self, version, service_slug):
        logging.debug("CurrentStatusHandler#get")
        
        if (self.valid_version(version)):
        
            service = Service.get_by_slug(service_slug)
        
            if (service):
                event = service.current_event()
        
                if (event):
                    self.json(event.rest(self.base_url(version))) 
                else:
                    self.error(404, "No current event for Service %s" % service_slug)
            else:
                self.error(404, "Service %s not found" % service_slug)
        else:
            self.error(404, "Version %s not supported" % version)
    
class EventInstanceHandler(restful.Controller):
    def get(self, version, service_slug, sid):
        logging.debug("EventInstanceHandler#get sid=%s" % sid)
        
        if (self.valid_version(version)):
            service = Service.get_by_slug(service_slug)

            if (service):
                event = Event.get(db.Key(sid))
                if (event and service.key() == event.service.key()):
                    self.json(event.rest(self.base_url(version))) 
                else:
                    self.error(404, "No event for Service %s with sid = %s" % (service_slug,sid))
            else:
                self.error(404, "Service %s not found" % service_slug)
        else:
            self.error(404, "API Version %s not supported" % version)
        

    @authorized.api("admin")
    def delete(self, version, service_slug, sid):
        logging.debug("EventInstanceHandler#delete sid=%s" % sid)
        
        if (self.valid_version(version)):
            service = Service.get_by_slug(service_slug)

            if (service):
                event = Event.get(db.Key(sid))
                if (event and service.key() == event.service.key()):
                    event.delete()
                    self.success(event.rest(self.base_url(version)))
                else:
                    self.error(404, "No event for Service %s with sid = %s" % (service_slug,sid))
            else:
                self.error(404, "Service %s not found" % service_slug)
        else:
            self.error(404, "API Version %s not supported" % version)
        


class StatusesListHandler(restful.Controller):
    def get(self, version):
        logging.debug("StatusesListHandler#get")
        
        if (self.valid_version(version)):
            query = Status.all().order('severity')

            if (query):
                data = []

                for s in query:
                    data.append(s.rest(self.base_url(version)))

                self.json({"statuses": data}) 
            else:
                self.error(404, "No statuses")
        else:
            self.error(404, "API Version %s not supported" % version)
        

    @authorized.api("admin")
    def post(self, version):
        
        if (self.valid_version(version)):
            name = self.request.get('name', default_value=None)
            description = self.request.get('description', default_value=None)
            image = self.request.get('image', default_value=None)
            level = self.request.get('level', default_value=None)
            severity = Level.get_severity(level)

            if name and description and severity and image:
                slug = slugify.slugify(name)
                status = Status.get_by_slug(slug)

                # Update existing resource
                if status:
                    status.description = description
                    status.severity = severity
                    status.image = image
                    status.name = name
                    status.put()
                    self.json(status.rest(self.base_url(version)))
                # Create new service
                else:
                    status = Status(name=name, slug=slug, description=description, 
                        severity=severity, image=image)
                    status.put()
                    self.json(status.rest(self.base_url(version)))
            else:
                self.error(400, "Bad Data")
        else:
            self.error(404, "API Version %s not supported" % version)
        


class StatusInstanceHandler(restful.Controller):
    def get(self, version, status_slug):
        logging.debug("CurrentStatusHandler#get")
        
        if (self.valid_version(version)):
            status = Status.get_by_slug(status_slug)

            if (status):
                self.json(status.rest(self.base_url(version))) 
            else:
                self.error(404, "No status %s for Service %s" % status_slug)
        else:
            self.error(404, "API Version %s not supported" % version)
        

    @authorized.api("admin")
    def post(self, version, status_slug):

        
        if (self.valid_version(version)):
            status = Status.get_by_slug(status_slug)
            if status:
                name = self.request.get('name', default_value=None)
                image = self.request.get('image', default_value=None)
                description = self.request.get('description', default_value=None)
                level = self.request.get('level', default_value=None)
                severity = Level.get_severity(level)
                
                if description:
                    status.description = description
                    
                if image:
                    status.image = image
                    
                if name:
                    status.name = name
                    
                if severity:
                    status.severity = severity
                
                if description or name or image or severity:
                    status.put()
                    
                self.json(status.rest(self.base_url(version)))
            else:
                self.error(404, "Status %s not found" % status_slug)
        else:
            self.error(404, "API Version %s not supported" % version)

    @authorized.api("admin")
    def delete(self, version, status_slug):
        logging.debug("StatusInstanceHandler#delete slug=%s" % status_slug)
        
        if (self.valid_version(version)):

            status = Status.get_by_slug(status_slug)            

            if status:
                # We may want to think more about this
                events = Event.all().filter('status =', status).fetch(1000)
                for event in events:
                    event.delete()
                status.delete()
                self.json(status.rest(self.base_url(version)))
            else:
                self.error(404, "Status %s not found" % service_slug)
        else:
            self.error(404, "API Version %s not supported" % version)

            

            
class ImagesListHandler(restful.Controller):
    def get(self, version):
        logging.debug("ImagesListHandler#get")
        host = self.request.headers.get('host', 'nohost')
        
        if (self.valid_version(version)):
        
            query = status_images.images
        
            for img in query:
                img["url"] = "http://" + host + img["url"]

            if (query):
                self.json({"images": query}) 
            else:
                self.error(404, "No images")
        else:
            self.error(404, "API Version %s not supported" % version)
            
class LevelsListHandler(restful.Controller):
    def get(self, version):
        logging.debug("LevelsListHandler#get")
        
        if (self.valid_version(version)):
            
            self.json({"levels": Level.all()})
            
        else:
            
            self.error(404, "API Version %s not supported" % version)



class SearchService(webapp.RequestHandler):
  """Handler for search requests."""
  @authorized.api("admin")
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
      
      # Perform proximity or bounds fetch.
      if query_type == 'proximity':
        results = Listing.proximity_fetch(base_query, center, max_results=max_results, max_distance=max_distance)
      
      elif query_type == 'bounds':
        results = Listing.bounding_box_fetch(base_query, bounds, max_results=max_results)
        
      elif query_type == 'user':
          limit = self.request.get("limit")
          offset = self.request.get("offset")
          if not limit:
              limit = 1000
          else:
              limit = int(limit)
          if not offset:
              offset = 0
          else:
              offset = int(offset)
          results = base_query.fetch(limit, offset);
      
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
        'results': results_obj,
      }))
    except:
      return _simple_error(str(sys.exc_info()[1]), code=500)