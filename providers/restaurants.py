# Copyright 2009 Google Inc.
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

""" Code related to the fetching and bookmarking of restaurant information.

The following classes are exported:
  LabelProvider: Provides methods to work with saving bookmarks and invites.
  RestaurantProvider: Delivers restaurant data from a web service.
"""

# Python imports
import urllib
import logging

# AppEngine imports
from google.appengine.ext import db
from google.appengine.api import urlfetch

# Django imports
from django.utils import simplejson

# Local imports
import utils
import models
import hashlib
import settings

class LabelProvider(object):
  """ Provides methods to work with saving bookmarks and invites.
  
  Provides some convenience methods for working with label data structures.
  It may be desirable to refactor this class to be static methods on the 
  Label data model sometime in the future.
  """
  def get_by_user(self, user):
    """ Get labels created by the specified user.
    
    Currently this method only returns the last 100 labels.  This could be 
    refactored to be more flexible and allow paging.
    
    Args:
      user: A models.User object.
      
    Returns:
      A list of models.Label objects, created by the specified user and sorted
      by last modified first.
    """
    query = models.Label.gql("where user=:1 order by updated desc", user)
    return query.fetch(100)
    
  def get_by_invitee(self, user):
    """ Get labels where the specified user has been marked as an invitee.
    
    Currently this method only returns the last 100 labels. This could be
    refactored to be more flexible and allow paging.
    
    Args:
      user: A models.User object.
      
    Returns:
      A list of models.Label objects, where the specified user is in the 
      invited user list.  
      TODO: Sort this list by updated date.
    """
    if hasattr(user, "guid"):
      query = models.Label.gql("where invited_guids = :1", user.guid)
      return query.fetch(100)
    return None
    
  def get_by_key(self, key):
    """ Gets a label by its data store key.
    
    Returns:
      The data store entry corresponding with the specified key.  
    """
    return db.get(key)

  def set(self, user, restaurant, text):
    """ Creates a new label if one does not already exist.
    
    If the restaurant passed in to this method has not been saved to the data
    store (only cached in memory), it will be stored to enforce the reference
    property on the resulting label.
    
    Args:
      user: The user who created this label.
      restaurant: The restaurant which is being labeled.
      text: A text description for the label.  
      
    Returns:
      If a label with the same user, restaurant, and text exists, the data 
      store entry for that label.  Otherwise, the newly created label. 
    """
    label = models.Label.gql("where user=:1 and restaurant=:2 and text=:3",
                             user, restaurant, text).get()
    if label:
      return label
                             
    key_name = "label|%s|%s|%s" % (user.provider_id, restaurant.restaurant_id,
                                   hashlib.sha1(text).hexdigest())
    params = {
      "key_name" : key_name,
      "restaurant" : restaurant,
      "user" : user,
      "text" : text,              
    }
    db.put(restaurant)  # May just be locally cached
    return models.Label.get_or_insert(**params) 
    
  def move_user_data(self, from_user, to_user):
    """ Moves all label data from one user to another user account.
    
    Used in cases where two accounts merge, this migrates all label data
    from the first account to the second account.  This includes changing 
    the owner on any labels created by the first user, and updating any
    invites which specify the first user, to the second user.
    
    Args:
      from_user: The user where data is being migrated from.
      to_user: The user who data will be migrated to.
    """
    query = models.Label.gql("where user=:1", from_user)
    for label in query:
      if label.invited_guids:
        label.invited_guids.remove(to_user.guid)
      label.user = to_user
      label.put()
    
    query = models.Label.gql("where invited_guids = :1", from_user.guid)
    for label in query:
      label.invited_guids.remove(from_user.guid)
      label.invited_guids.append(to_user.guid)
      label.put()
    
    
class RestaurantProvider(object):
  """ Provides data about restaurants from the YQL web service.
  
  The public interface from this class could be adopted to support other
  restaurant providers.  Yahoo! local search was chosen because it provides
  rating data and has fairly permissive quota limits.
  """
  def __init__(self):
    """ Constructor.
    
    Sets which fields will be requested from the YQL query.
    """
    self.restaurant_fields = ", ".join([
        "id", "Title", "Address", "City", "State", "Rating.AverageRating", 
        "Rating.TotalRatings", "BusinessUrl", "Categories", "Latitude", 
        "Longitude"])
        
  def _cache_restaurant(self, restaurant):
    """ Stores a restaurant in the memory cache.
    
    Args:
      restaurant: The object to store in the cache.  The restaurant id is used
          as a cache key.
    """
    utils.cache_set(restaurant, "restaurant", restaurant.restaurant_id)
    
  def _cache_get_restaurant(self, restaurant_id):
    """ Gets a restaurant from the cache.
    
    Args:
      restaurant_id: The id of the restaurant to retrieve from the cache.
      
    Returns:
      The data for the restaurant with the corresponding ID, if it existed in
      the cache, else None.
    """
    return utils.cache_get("restaurant", restaurant_id)
    
  def _convert_result_to_restaurant(self, result):
    """ Converts a YQL search result to a models.Restaurant object.
    
    Args:
      result: The dict returned by a YQL search.
      
    Returns:
      An initialized (but not saved) models.Restaurant instance with the 
      appropriate properties set to the data from the search result.
    """
    try:
      rating_average = float(result["Rating"]["AverageRating"])
    except ValueError:
      rating_average = -1.0
      
    try:
      rating_count = int(result["Rating"]["TotalRatings"])
    except ValueError:
      rating_count = 0
      
    location = db.GeoPt(result["Latitude"], result["Longitude"])
    
    categories = []
    if isinstance(result["Categories"]["Category"], list):
      for category in result["Categories"]["Category"]:
        categories.append(category["content"])
    else:
      categories.append(result["Categories"]["Category"]["content"])
      
    params = {
      "key_name" : "restaurant|%s" % result["id"],
      "restaurant_id" : result["id"],
      "name" : result["Title"],
      "address" : result["Address"],
      "city" : result["City"],
      "state" : result["State"],
      "rating_average" : rating_average,
      "rating_count" : rating_count,
      "url" : result["BusinessUrl"],
      "location" : location,
      "categories" : categories,
    }
    
    return models.Restaurant(**params)
    
  def _yql_query(self, query):
    """ Performs a query on the YQL web service interface.
    
    Args:
      query: A string query in the YQL query syntax.
      
    Returns:
      If a result was returned, a dict representing the data structure which
      was passed back.  None otherwise.
    """
    query_hash = hashlib.sha1(query).hexdigest()
    result = utils.cache_get("yql_query", query_hash)
    if result is None:
      logging.info("Fetching yql query: %s" % query)
      query = urllib.quote_plus(query)
      url = "http://query.yahooapis.com/v1/public/yql?q=%s&format=json" % query
      response = simplejson.loads(urlfetch.fetch(url).content)["query"]

      if response is None or int(response["count"]) == 0:
        return None
        
      # Result set is inconsistent if there is only one result
      if int(response["count"]) == 1:
        result = [response["results"]["Result"]]
      else:
        result = response["results"]["Result"]
        
      utils.cache_set(result, "yql_query", query_hash) 
    return result
    
  def _yql_restaurant_search(self, term, location):
    """ Performs a Yahoo! local search, limiting results to restaurants only.
    
    This uses the category code for "Restaurants" in the Yahoo! local search
    API to limit results, otherwise searching would return all kinds of local
    businesses.
    
    The number of search results are limited to keep this code simple.  A 
    more sophisticated implementation would allow paging.
    
    Args:
      term: The search term to use.
      location: A string representing the location to search in.
    
    Returns:
      A list of models.Restaurant objects corresponding to the results of the
      query, or None if no restaurants were found.
    """
    query_params = {
      "query" : term,
      "location" : location,
      "category" : "96926236", # Code for 'Restaurants'
      "limit" : settings.SEARCH_RESULTS,
      "offset" : 0,
      "fields" : self.restaurant_fields,
    }
          
    query = " ".join([
      'select %(fields)s from local.search where',
      'query="%(query)s"',
      'and location="%(location)s"',
      'and category="%(category)s"',
      'limit %(limit)s',
      'offset %(offset)s',
    ]) % query_params
         
    result = self._yql_query(query)
    if result is None:
      restaurants = None
    else:
      restaurants = map(self._convert_result_to_restaurant, result)
    return restaurants
    
  def _yql_restaurant_get(self, restaurant_id):
    """ Gets a single restaurant's data.
    
    This method performs a query for a single restaurant, returning the results
    from the Yahoo! local search.
    
    Args:
      The ID of the restaurant to fetch.
      
    Returns:
      The models.Restaurant object with the data corresponding to the restaurant
      with the given ID number, or None if no results were found.
    """
    params = {
      "id" : restaurant_id,
      "fields" : self.restaurant_fields,
    }
    
    query = 'select %(fields)s from local.search(1) where id=%(id)s' % params      
    result = self._yql_query(query)
    if result:
      return self._convert_result_to_restaurant(result)
    return None
    
  def search(self, term, location):
    """ Performs a search for restaurants in a specific location.
    
    Results returned from this method will be models.Restaurant instances, but
    not necessarily written to the data store, to prevent the store being
    flooded with every search result.  This way, we only store restaurants that
    have been bookmarked by at least one user.
    
    Args:
      term: The search term to use.
      location: A string representing the location to search in.
    
    Returns:
      A list of models.Restaurant objects corresponding to the results of the
      query, or None if no restaurants were found.
    """
    restaurants = self._yql_restaurant_search(term, location)
    if restaurants:
      for restaurant in restaurants:
        self._cache_restaurant(restaurant)
    return restaurants
    
  def get_restaurant(self, restaurant_id):
    """ Gets a single restaurant by ID.
    
    Args:
      The ID of the restaurant to fetch.
      
    Returns:
      The models.Restaurant object with the data corresponding to the restaurant
      with the given ID number, or None if no results were found.
    """
    restaurant = self._cache_get_restaurant(restaurant_id)
    if restaurant is None:
      restaurant = self._yql_restaurant_get(restaurant_id)
      self.cache_restaurant(restaurant)
    return restaurant