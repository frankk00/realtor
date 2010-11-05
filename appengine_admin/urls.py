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

from django.conf.urls.defaults import *


urlpatterns = patterns('appengine_admin.views',
            (r'^/?$', 'listing_admin.index_get'),
            (r'^/ui/Listing/list/$', 'listing_admin.list_get'),
            (r'^/ui/Listing/new/$', 'listing_admin.new_get'),
            (r'^/ui/Listing/edit/ui/Listing/$', 'listing_admin.edit_get'),
            (r'^/ui/Listing/delete/ui/Listing/$', 'listing_admin.delete_get'),
            (r'^/ui/Listing/get_blob_contents/ui/Listing/ui/Listing/$', 'listing_admin.get_blob_contents'),
            (r'^/ui/Listing/new/$', 'listing_admin.new_post'),
            (r'^/ui/Listing/edit/ui/Listing/$', 'listing_admin.edit_post'),
)


handler404 = 'common.views.common_404'
handler500 = 'common.views.common_500'
