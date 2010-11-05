from google.appengine.api import users
from google.appengine.api import oauth
import logging

def get_current_user():
    user = users.get_current_user();
    logging.info("User (users): %s" % user)
    if not user:
        ouser = oauth.get_current_user();
        logging.info("User (oauth): %s" % user)
    return user

def role(role):
    def wrapper(handler_method):
        def check_login(self, *args, **kwargs):
            """
            user = users.get_current_user()
            if not user:
                if self.request.method != 'GET':
                    self.error(403)
                else:
                    self.redirect(users.create_login_url(self.request.uri))
            elif role == "user" or (role == "admin" and
                                    users.is_current_user_admin()):
                handler_method(self, *args, **kwargs)
            else:
                if self.request.method == 'GET':
                    self.redirect("/403.html")  # Some unauthorized feedback
                else:
                    self.error(403) # User didn't meet role.
            """
            user = get_current_user()
            logging.info("User: %s" % user)
            if user:
                handler_method(self, *args, **kwargs)

            else:
                logging.warn("ERROR: %s" % e)
                
        return check_login
    return wrapper
