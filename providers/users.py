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

""" Code to provide access to user accounts from multiple sources.

The following classes are exported:
  UserProvider: Gives access to locally registered users.
  TwoLeggedProvider: Gives access to Friend Connect users on behalf of the app.
  FCAuthProvider: Gives access to Friend Connect users on behalf of a FC user.
"""

# Python imports
import logging
import hashlib

# App Engine imports
from google.appengine.ext import db

# Local imports
import opensocial
import utils
import settings
import models
import controller
  
class UserProvider(object):
  """ Gives access to locally registered users.
  
  Provides methods to register, authenticate, and fetch data about local 
  users.  
  """
  def __init__(self, session):
    """ Initialize with a session object for storing data. 
    
    Args:
      A sessions.SessionProvider object which can be used to persist data.
    """
    self._session = session
        
  def __hash_password(self, password):
    """ Converts a password into a hashed value.
    
    We don't want to store plaintext passwords in the database, so hash 
    comparisons are done instead.  In a production site, this password would
    be hashed with a nonce to prevent dictionary attacks against a compromised
    data store.  Here, it's not really an issue (existing sites should have
    their own auth systems already in place).  
    
    Args:
      password:  The plaintext password to hash.
      
    Returns:
      A hexadecimal string that corresponds to the password but cannot be used
      to determine what the original password was.
    """
    return hashlib.sha1(password).hexdigest()
    
  def _set_viewer(self, viewer):
    """ Registers the current viewer with the session.
    
    Args: 
      viewer: The models.User object corresponding to the person logged in to 
          the site for the current request.
    """
    self._session["viewer"] = viewer
    
  def get_viewer(self):
    """ Returns the viewer if available.
    
    Returns:
      If the viewer has been registered with the session using the _set_viewer
      method, this method will return the stored user object.  Otherwise, this
      method returns None.
    """
    if self._session.has_key("viewer"):
      return self._session["viewer"]
    return None
    
  def get_user_by_user_name(self, user_name):
    """ Fetches a user by their user name.
    
    Args:
      user_name: The user name of the User to fetch.
      
    Returns:
      The models.User object corresponding with the user name, or None if no
      user was found.
    """
    return models.User.gql("where user_name = :1", user_name).get()
    
  def get_user_by_key_name(self, key_name):
    """ Returns a user by their database key name.
    
    Args:
      key_name: A string that can be used to fetch a user from the data store.
    
    Returns:
      The corresponding user or None if the key did not match a user in the
      data store.
    """
    users = self.get_users_by_key_name([key_name]).values()
    if users:
      return users[0]
    return None
    
  def get_users_by_key_name(self, key_names):
    """ Returns several users by their database key names.
    
    Args:
      key_names: A collection of database keys representing users.
      
    Returns:
      A dict where the key corresponds with the user's provider ID and the
      value is the user object itself.  Invalid keys are not represented
      in the returned object.
    """
    users = models.User.get_by_key_name(key_names)
    result = {}
    for user in users:
      if user:
        result[user.provider_id] = user
      
    return result
    
  def authenticate(self, user_name, password):
    """ Authenticates user credentials and registers a viewer if valid.
    
    If the username and password match a user in the data store, that user
    is registered with the current session.
    
    Args:
      user_name: The user name of the user to authenticate.
      password:  A password to authenticate the user.
      
    Raises:
      controller.UserVisibleError: If the user name or password were invalid.
      
    Returns:
      The viewer if the credentials were valid."""
    user = self.get_user_by_user_name(user_name)
    if not user or not user.password_hash:
      raise controller.UserVisibleError("You did not specify a valid user.")
    
    if self.__hash_password(password) == user.password_hash:
      return self._set_viewer(user)
    else:
      raise controller.UserVisibleError("The password you gave was not correct.")

  def register(self, user_name, password, password_again, thumbnail_image=None):
    """ Creates a new local user.
    
    If a user is created successfully, the new user will be registered with 
    the current session.
    
    A user cannot be created if the user_name is already in use.
    
    Args:
      user_name: The user name to register.
      password: The plaintext password the user wishes to use.
      password_again: A repeat of the password, to make sure it was entered  
          correctly.
          TODO: This check could be done in the appropriate views class.
      thumbnail_image: The filename of an icon to represent the user.
      
    Raises:
      UserVisibleError: If something was wrong with the registered data.

    Returns:
      A user object if created successfully.
    """
    user = self.get_user_by_user_name(user_name)
    if user is not None:
      raise controller.UserVisibleError("This name is already in use.")

    if password != password_again:
      raise controller.UserVisibleError("The passwords you specified do not match.")
      
    if thumbnail_image is None:
      thumbnail_image = "anon01.gif"

    params = {
      "user_name" : user_name,
      "provider_id" : user_name,
      "key_name" : models.User.create_key_name(user_name),
      "thumbnail_image" : thumbnail_image,
      "password_hash" : self.__hash_password(password)
    }
    user = models.User.get_or_insert(**params)
    return self._set_viewer(user)
   
  
class TwoLeggedProvider(UserProvider):
  """ Gives access to Friend Connect users on behalf of the app.
  
  Used when a locally registered user logs into the site.  This uses 
  two-legged OAuth to request users in cases where details about a 
  Friend Connect user need to be shown (e.g. display_name, thumbnail_url, etc).
  """
  def __init__(self, session):
    """ Constructor.
    
    Args:
      A sessions.SessionProvider object which can be used to persist data.
    """
    super(TwoLeggedProvider, self).__init__(session)
    params = {
      "server_rpc_base" : settings.FRIENDCONNECT_RPC_URL,
      "oauth_consumer_key" : settings.FRIENDCONNECT_CONSUMER_KEY,
      "oauth_consumer_secret" : settings.FRIENDCONNECT_CONSUMER_SECRET,
    }
    config = opensocial.ContainerConfig(**params)
    self.__container = opensocial.ContainerContext(config)
    
  def _cache_user(self, user):
    """ Stores a Friend Connect user in the cache.
    
    Args:
      user: User to store in the cache.  The user's provider id is used as the
          cache key.
    """
    utils.cache_set(user, "fcuser", user.provider_id)
    
  def _cache_get_user(self, user_id):
    """ Gets a Friend Connect user from the cache.
    
    Args:
      user_id: The ID of the user to fetch from the cache.
      
    Returns:
      The user with the specified ID if they exist in the cache, None otherwise.
    """
    utils.cache_get("fcuser", user_id)
    
  def get_profile_fields(self):
    """ Returns a list of profile fields to request from Friend Connect.
    
    Specifies additional profile fields to fetch when requesting users from
    Friend Connect's OpenSocial implementation.
    
    Returns:
      A list of profile fields to fetch.
    """
    return [ "profileUrl" ]

  def get_users_by_key_name(self, user_keys):
    """ Returns a list of users given their database keys.
    
    The base class implements this function by pulling models.User instances
    from the data store by their database key.  However, in the case of 
    Friend Connect users, the models.FriendConnectUser instances returned
    will not have profile information attached because that information is
    not stored in the data store.  This method extends the base implementation
    by seeing which FriendConnectUsers have been returned and then creating
    a batch OpenSocial request to pull each record from the Friend Connect
    servers.  Caching is used to limit the amount of requests that have to
    be made to the remote servers.
    
    Args:
      user_keys: A collection of database keys representing users.
      
    Returns:
      A dict where the key corresponds with the user's provider ID and the
      value is the user object itself.  Invalid keys are not represented
      in the returned object.  FriendConnectUser objects are populated with
      data from the Friend Connect servers.
    """
    users = super(TwoLeggedProvider, self).get_users_by_key_name(user_keys)
    
    batch_added = False
    batch = opensocial.RequestBatch()
    for user_id, user in users.iteritems():
      if isinstance(user, models.FriendConnectUser):
        cached_user = self._cache_get_user(user.provider_id)
        if cached_user:
          users[cached_user.provider_id] = cached_user
        else:
          batch_added = True
          params = [ user_id, self.get_profile_fields() ]
          request = opensocial.request.FetchPersonRequest(*params)       
          batch.add_request("user%s" % user_id, request)

    try:
      if batch_added:
        batch.send(self.__container)
        for user_id, user in users.iteritems():
          person = batch.get("user%s" % user_id)
          parsed_user = models.FriendConnectUser.from_person(person)
          users[user_id] = parsed_user
          self._cache_user(parsed_user)
    except:
      logging.exception("OpenSocial Exception")
      
    return users
    
  def get_viewer_friends(self, start=0, count=20):
    """ Returns friends for the given user.
    
    Since the two legged auth provider is only used for locally registered users
    and the is no native friend functionality in this app, an empty list is 
    returned.
    
    Args:
      start: Start index for the friends to return.
      count: Max number of friends to return.
    
    Returns:
      An empty list.
    """
    return []
    
class FCAuthProvider(TwoLeggedProvider):
  """ Gives access to Friend Connect users on behalf of a FC user.
  
  The current user is logged in with Friend Connect, so we can perform actions
  on their behalf, such as fetching friends or posting activities.
  """
  def __init__(self, security_token, session):
    """ Constructor. 
    
    Args:
      security_token: The security token passed to the website via a cookie.
      session: The session provider used to persist this user's data.
    """
    super(FCAuthProvider, self).__init__(session)
    params = {
      "server_rpc_base" : settings.FRIENDCONNECT_RPC_URL,
      "security_token" : security_token,
      "security_token_param" : "fcauth",
    }
    config = opensocial.ContainerConfig(**params)
    self.__container = opensocial.ContainerContext(config)
    
  def get_viewer_friends(self, start=0, count=20):
    """ Returns friends for the given user.
    
    Args:
      start: Start index for the friends to return.
      count: Max number of friends to return.
    
    Returns:
      A list of models.FriendConnectUser objects corresponding to the requested
      page of the current viewer's friends.
    """
    start = max(int(start), 0)
    count = min(int(count), 50)
    
    friends = self._session["viewer_friends|%s|%s" % (start, count)]
    if friends is not None:  
      return friends
      
    batch = opensocial.RequestBatch()
    params = { "count" : count, "startIndex" : start }
    args = [ "@me", "@friends", self.get_profile_fields(), params ]
    request = opensocial.request.FetchPeopleRequest(*args)       
    batch.add_request("friends", request)

    try:
      batch.send(self.__container)
      friends_list = map(models.FriendConnectUser.from_person, batch.get("friends"))
      if friends_list:
        friends = models.UserList(friends_list)
        friends.total = int(batch.get("friends").totalResults)
        friends.start = int(start)
        friends.end = int(start) + len(friends)
        self._session["viewer_friends|%s|%s" % (start, count)] = friends
        for friend in friends:
          self._cache_user(friend)
    except:
      logging.exception("OpenSocial Exception")
      friends = None

    return friends
    
  def get_viewer(self):
    """ Returns the current viewer.
    
    Returns:
      The viewer who matches the security token which this object was 
      initialized with.
    """
    viewer = super(FCAuthProvider, self).get_viewer()
    if viewer is not None:  
      if isinstance(viewer, models.FriendConnectUser):
        return viewer         # We have a cached viewer (may be false)

    batch = opensocial.RequestBatch()
    args = [ "@me", self.get_profile_fields() ]
    request = opensocial.request.FetchPersonRequest(*args)  
    batch.add_request("viewer", request)

    try:
      batch.send(self.__container)
      friendconnect_viewer = models.FriendConnectUser.from_person(batch.get("viewer"))
      self._set_viewer(friendconnect_viewer)
    except:
      logging.exception("Problem getting the viewer")
      viewer = False

    return viewer
  