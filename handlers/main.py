import os
import os.path
import wsgiref.handlers
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
import appengine_admin
from handlers import restful
from google.appengine.api import users
from google.appengine.api import oauth
from handlers import site, api
import locale
import sys

sys.path.append(".")

template.register_template_library(
    'django.contrib.humanize.templatetags.humanize')
template.register_template_library('templatelib')







def get_current_user():
    user = users.get_current_user();
    logging.info("User (users): %s" % user)
    if not user:
        ouser = oauth.get_current_user();
        logging.info("User (oauth): %s" % user)
    return user

class NotFoundHandler(restful.Controller):
    def get(self):
        logging.debug("NotFoundHandler#get")
        template_data = {}
        self.render(template_data, '404.html')

class UnauthorizedHandler(webapp.RequestHandler):
    def get(self):
        logging.debug("UnauthorizedHandler#get")
        self.error(403)

def make_static_handler(template_file):
  """Creates a webapp.RequestHandler type that renders the given template
  to the response stream."""
  class StaticHandler(webapp.RequestHandler):
    def get(self):
      self.response.out.write(template.render(
          os.path.join(os.path.dirname(__file__), template_file),
          {'current_user': get_current_user()}))
  
  return StaticHandler
  
  
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
          
          
class ListingDetailsPage(webapp.RequestHandler):
    def get (self):
        template_file = '../templates/listing.html'
        id = int(self.request.get('id'))
        listing = Listing.get(db.Key.from_path('Listing', id))
        self.response.out.write(template.render(
          os.path.join(os.path.dirname(__file__), template_file),
          {'current_user': get_current_user(), 'listing' : listing}))
    
        
    
class AdminListing(appengine_admin.ModelAdmin):
    model = Listing
    listFields = ('address', 'price', 'createDate', 'lastUpdate')
    editFields = ('address', 'price', 'baths', 'beds', 'size', 'description', 'propertyType', 'amenities', 'portfolio', 'listingAgentName', 'listingAgentPhone', 'listingAgentPhone', 'listingAgentCompany', 'listingAgentEmail')
    readonlyFields = ('createDate', 'lastUpdate', 'author')

# Register to admin site
appengine_admin.register(AdminListing)


def main():
  application = webapp.WSGIApplication([
      ('/', make_static_handler('../templates/index.html')),
      ('/listing', ListingDetailsPage),      
      (r'^(/ui)(.*)$', appengine_admin.Admin),

        #API
        ('/403.html', site.UnauthorizedHandler),
        ('/404.html', site.NotFoundHandler),
        (r'/api/(.+)/services', api.ServicesListHandler),
        (r'/api/(.+)/services/(.+)/events', api.EventsListHandler),
        (r'/api/(.+)/services/(.+)/events/current', api.CurrentEventHandler),
        (r'/api/(.+)/services/(.+)/events/(.+)', api.EventInstanceHandler),
        (r'/api/(.+)/services/(.+)', api.ServiceInstanceHandler),
        (r'/api/(.+)/statuses', api.StatusesListHandler),
        (r'/api/(.+)/statuses/(.+)', api.StatusInstanceHandler),
        (r'/api/(.+)/status-images', api.ImagesListHandler),
        (r'/api/(.+)/levels', api.LevelsListHandler),
        (r'/api/', api.NotFoundHandler),
        (r'/api/', api.NotFoundHandler),
        
        #SITE
        #(r'/services/(.+)/(.+)/(.+)/(.+)', serviceHandler),
        #(r'/services/(.+)/(.+)/(.+)', serviceHandler),
        #(r'/services/(.+)/(.+)', serviceHandler),
        #(r'/services/(.+)', serviceHandler),
        (r'/documentation/credentials', site.ProfileHandler),
        (r'/documentation/verify', site.VerifyAccessHandler),
        (r'/documentation/(.+)', site.DocumentationHandler),

      ],
      debug=('Development' in os.environ['SERVER_SOFTWARE']))
  wsgiref.handlers.CGIHandler().run(application)
  
  


if __name__ == '__main__':
  main()
