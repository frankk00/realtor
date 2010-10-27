import os

from google.appengine.api import users
from google.appengine.ext import webapp


JSAPI_KEYS = {
        'www.realtor.io' : 'ABQIAAAAPwa6P0RAONGDnDVWIoz60RSnKAnuZszvNyoGcWCK2TBOonWFTRQfrSoq8xFBhp3vDBO3lWoNnMifNg',
        'www.realtor.io:80' : 'ABQIAAAAPwa6P0RAONGDnDVWIoz60RSnKAnuZszvNyoGcWCK2TBOonWFTRQfrSoq8xFBhp3vDBO3lWoNnMifNg',
        'start.realtor.io' : 'ABQIAAAAPwa6P0RAONGDnDVWIoz60RQCaiKapeUJ_lNUjGkTAgDNsxunghTaSfQqEUOhYme_Fn50EYqy_agl2Q',
        'start.realtor.io:80' : 'ABQIAAAAPwa6P0RAONGDnDVWIoz60RQCaiKapeUJ_lNUjGkTAgDNsxunghTaSfQqEUOhYme_Fn50EYqy_agl2Q',
        'realtor-io.appspot.com:80' : 'ABQIAAAAPwa6P0RAONGDnDVWIoz60RSOO1af5Z7xW5CYEjDbA52Chjia3xT8SNkZCYmE4ivPJL-fzQZv_RouIg',
        'realtor.io:80' :'ABQIAAAAPwa6P0RAONGDnDVWIoz60RS_XVdtR9vJUHoImLNBbcMuXbr6qRRCTJ1XM9Je76qJSqsr_4HKGKJ65A',
        'localhost:8080': 'ABQIAAAAPwa6P0RAONGDnDVWIoz60RS_XVdtR9vJUHoImLNBbcMuXbr6qRRCTJ1XM9Je76qJSqsr_4HKGKJ65A',
        'geomodel-demo.appspot.com:80': 'ABQIAAAAKkfkHb2nXsD0o1OX2TbdkRTF1o4efM8vQJVwhtHQDLR3ZWMiYhT5A9y4YtISxJ2FetOMuCL1YkBiaw',
        '2.latest.geomodel-demo.appspot.com:80': 'ABQIAAAAKkfkHb2nXsD0o1OX2TbdkRTviFmNkNIQO8yqbxHmKO-CSduAsRR3q-4j7qE0AI6PhpvozLMFiXKlWg',
}


register = webapp.template.create_template_register()


@register.simple_tag
def jsapi_key():
  # the os environ is actually the current web request's environ
  server_key = '%s:%s' % (os.environ['SERVER_NAME'], os.environ['SERVER_PORT'])
  return JSAPI_KEYS[server_key] if server_key in JSAPI_KEYS else 'ABQIAAAAPwa6P0RAONGDnDVWIoz60RQCaiKapeUJ_lNUjGkTAgDNsxunghTaSfQqEUOhYme_Fn50EYqy_agl2Q'


def _current_request_uri():
  """Returns the current request URI."""
  return os.environ['PATH_INFO'] + (('?' + os.environ['QUERY_STRING'])
                                    if os.environ['QUERY_STRING'] else '')

@register.simple_tag
def login_url(dest_url=''):
  """Template tag for creating login URLs."""
  dest_url = dest_url or _current_request_uri()
  return users.create_login_url(dest_url)


@register.simple_tag
def logout_url(dest_url=''):
  """Template tag for creating logout URLs."""
  dest_url = dest_url or _current_request_uri()
  return users.create_logout_url(dest_url)
