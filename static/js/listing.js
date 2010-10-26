var PAGE_PATH = document.location.href.replace(/#.*/, '')
                                      .replace(/\/[^\/]*$/, '/');

var MILES_TO_METERS = 1609.344;

var TYPES = {
  'Multi-Family Home': 'Multi-Family Home',
  'Townhome': 'Townhome',
  'Condo': 'Condo',
  'Other': 'Other'
};

// Only perform proximity searches on 
// geocode accuracy.
var MIN_PROXIMITY_SEARCH_GEOCODE_ACCURACY = 6;

var MAX_PROXIMITY_SEARCH_MILES = 50;
var MAX_PROXIMITY_SEARCH_RESULTS = 10;
var MAX_BOUNDS_SEARCH_RESULTS = 25;

var MIN_GRADE_TAUGHT = -1; // PK
var MAX_GRADE_TAUGHT = 12; // 12th grade


var map;

/**
 * @type google.maps.ClientGeocoder
 */
var geocoder = new google.maps.Geocoder();

var g_listView = false; // Whether or not we're in list view.

/**
 * An array of the current search result data objects.
 * Result object properties are:
 *   {Number} lat
 *   {Number} lng
 *   {String} name
 *   {String} icon
 *   {google.maps.Marker} marker
 *   {Number} [distance] The distance in meters from the search center.
 *   {jQuery object} listItem The list view item for the result.
 *   ...
 * Along with any other properties returned by the search service.
 */
var g_searchResults = null;

var g_currentSearchXHR = null; // For cancelling current XHRs.
var g_searchOptions = null; // Last options passed to doSearch.
var g_searchCenterMarker = null;

var g_mapAutoScrollInterval = null;
var g_programmaticPanning = false; // Temporary moveend disable switch.
var g_mapPanListener = null;


function Listing(mapId) {
  this.mapDiv_ = document.getElementById(mapId);
  var options = {
    zoom: 13,
    center: new google.maps.LatLng(-33.86681373718802, 151.19591345512868),
    mapTypeId: google.maps.MapTypeId.ROADMAP,
    mapTypeControl: false
  };

  if (document.location.href.indexOf('?mobile') !== -1) {
    options.navigationControlOptions = {
      style: google.maps.NavigationControlStyle.ANDROID,
      position: google.maps.ControlPosition.BOTTOM
    }
  }

  this.shopIcon_ = new google.maps.MarkerImage('/static/images/markers/simple.png', new google.maps.Size(32, 37));
  this.shopActiveIcon_ = new google.maps.MarkerImage('/static/images/markers/simple.png', new google.maps.Size(32, 37));

  this.shopMarkers_ = {};

  this.setMapHeight();
  this.map_ = new google.maps.Map(this.mapDiv_, options);

  var that = this;
  google.maps.event.addDomListener(window, 'resize', function() {
    that.setMapHeight();
  });

  google.maps.event.addListener(this.map_, 'idle', function() {
    that.findStores_();
  });

  $('a', '#store-info-close').click(function() {
    that.showMap();
    return false;
  });

  var icon = new google.maps.MarkerImage('/static/images/my-location.png',
    new google.maps.Size(14, 14),
    new google.maps.Point(0, 0),
    new google.maps.Point(7, 7));

  this.userLocationMarker_ = new google.maps.Marker({
    icon: icon,
    clickable: false,
    zIndex: 200
  });

  this.locationAccuracy_ = new google.maps.Circle({
    fillColor: '#0000ff',
    fillOpacity: 0.1,
    strokeColor: '#0000ff',
    strokeOpacity: 0.3,
    strokeWeight: 1,
    clickable: false,
    zIndex: 199
  });

  this.locationAccuracy_.bindTo('center', this.userLocationMarker_, 'position');

  this.shopInfoWindow_ = new google.maps.InfoWindow();

  this.addActions_();
  this.getUserPosition_();

  window.setTimeout(function() {
    window.scrollTo(0, 1);
  }, 100);
};

Listing.prototype.addActions_ = function() {
  this.setupAddNew_();
  this.setupGetUserPosition_();
};

Listing.prototype.getPlaces_ = function() {
  var that = this;
  var pos = this.addNewMarker_.getPosition()
  
  doGeocodeAndSearch();
};

Listing.prototype.populatePlaces_ = function(places) {
  var hasOne = false;
  var html = '<select id="places-options">';
  if (places.status == 'OK') {
    for (var i = 0, result; result = places.results[i]; i++) {
      if (result.types.indexOf('establishment') != -1) {
        hasOne = true;
        html += '<option value="' + result.name + '">' + result.name + '</option>';
      }
    }
  }
  html += '<option value="">Other</option></select>';

  if (!hasOne) {
    return;
  }

  $('#new-shop-name').hide();

  $('#new-shop-name-options').html(html);
  this.setMapHeight();

  var options = $('#places-options', '#new-shop-name-options');

  var that = this;
  $(options).change(function() {
    if ($(this).val() == '') {
      $('#new-shop-name').show();
      that.setMapHeight();
    } else {
      $('#new-shop-name').hide();
      that.setMapHeight();
    }
  });

  $(options).keypress(function() {
    if ($(this).val() == '') {
      $('#new-shop-name').show();
    } else {
      $('#new-shop-name').hide();
    }
  });
};

Listing.prototype.setupGetUserPosition_ = function() {
  var that = this;
  $('#my-location').click(function() {
    that.getUserPosition_();
    return false;
  });
};

Listing.prototype.setUsersPosition_ = function(position) {
  var pos = new google.maps.LatLng(position.coords.latitude,
    position.coords.longitude);
  this.userPosition_ = pos;
  this.userLocationMarker_.setPosition(pos);
  if (!this.userLocationMarker_.getMap()) {
    this.userLocationMarker_.setMap(this.map_);
  }

  this.locationAccuracy_.setRadius(position.coords.accuracy);
  if (!this.locationAccuracy_.getMap()) {
    this.locationAccuracy_.setMap(this.map_);
  }
};

Listing.prototype.getUserPosition_ = function() {
  var that = this;
  if (navigator.geolocation) {
    navigator.geolocation.watchPosition(function(position) {
      that.setUsersPosition_(position);
    });
    navigator.geolocation.getCurrentPosition(function(position) {
      var pos = new google.maps.LatLng(position.coords.latitude,
          position.coords.longitude);
      that.setUsersPosition_(position);
      that.map_.panTo(pos);
    }, function() {
      // HACK FOR THE TALK
      that.map_.panTo(new google.maps.LatLng(-33.86681373718802, 151.19591345512868));
      that.userLocationMarker_.setPosition(new google.maps.LatLng(-33.86681373718802, 151.19591345512868));
      that.userLocationMarker_.setMap(that.map_);
    }, {timeout: 2000});
  } else {
    that.map_.panTo(new google.maps.LatLng(-33.86681373718802, 151.19591345512868));
    that.userLocationMarker_.setPosition(new google.maps.LatLng(-33.86681373718802, 151.19591345512868));
    that.userLocationMarker_.setMap(that.map_);
  }
};

function updateObject(dest, src) {
	  dest = dest || {};
	  src = src || {};
	  
	  for (var k in src)
	    dest[k] = src[k];
	  
	  return dest;
	}

Listing.prototype.findStores_ = function() {
	
	options = {
		'type' : 'proximity',
		'center' : ''
	};
	
	  var searchParameters = {
			    type: options.type
			  };
			  
			  if (options.type == 'proximity') {
			    searchParameters = updateObject(searchParameters, {
			      maxresults: MAX_PROXIMITY_SEARCH_RESULTS,
			      maxdistance: MAX_PROXIMITY_SEARCH_MILES * MILES_TO_METERS
			    });
			  } else if (options.type == 'bounds') {
			    searchParameters = updateObject(searchParameters, {
			      north: options.bounds.getNorthEast().lat(),
			      east: options.bounds.getNorthEast().lng(),
			      south: options.bounds.getSouthWest().lat(),
			      west: options.bounds.getSouthWest().lng(),
			      maxresults: MAX_BOUNDS_SEARCH_RESULTS
			    });
			  }
			  
			  // Add in advanced options.
			  if (options.gradeRange) {
			    searchParameters = updateObject(searchParameters, {
			      mingrade: options.gradeRange[0],
			      maxgrade: options.gradeRange[1]
			    });
			  }

			  if (options.schoolType) {
			    searchParameters.property_type = options.property_type;
			  }
	
  var bounds = this.map_.getBounds();
  var that = this;
  var data = {
    url: '/s/search',
    type: 'get',
    data: searchParameters,
    dataType: 'json',
    bounds: bounds.toUrlValue()
  };
  // $.post('/stores', data, function(data) {
    // that.addStores_(data);
  // });
  
 doGeocodeAndSearch();
  
};

Listing.prototype.addStoreMarker_ = function(shop) {
  var position = new google.maps.LatLng(shop.lat, shop.lng);
  var marker = new google.maps.Marker({
    position: position,
    map: this.map_,
    title: shop.name,
    icon: this.shopIcon_,
    zIndex: 100
  });

  marker.key = shop.key;
  var that = this;
  var listener = google.maps.event.addListener(marker, 'click', function() {
    that.loadShop(this);
  });

  marker.listener = listener;
  return marker;
};

Listing.prototype.addStores_ = function(shops) {
  var d = new Date();
  var added = '_' + d.getTime();
  for (var i = 0, shop; shop = shops[i]; i++) {
    if (this.shopMarkers_[shop.key]) {
      this.shopMarkers_[shop.key].added = added;
    } else {
      var marker = this.addStoreMarker_(shop);
      marker.added = added;
      this.shopMarkers_[shop.key] = marker;
    }
  }

  for (var key in this.shopMarkers_) {
    if (this.shopMarkers_[key].added != added) {
      google.maps.event.removeListener(this.shopMarkers_[key].listener);
      this.shopMarkers_[key].setMap(null);
      delete this.shopMarkers_[key];
    }
  }

  if (this.activeMarkerKey_ && this.shopMarkers_[this.activeMarkerKey_]) {
    this.shopMarkers_[this.activeMarkerKey_].setIcon(this.shopActiveIcon_);
  }
};

Listing.prototype.loadShop = function(marker) {
  var data = {
    action: 'load',
    key: marker.key
  }

  this.shopIcon_ = new google.maps.MarkerImage('/static/images/listing.png', new google.maps.Size(32, 37));
  marker.setIcon(this.shopActiveIcon_);

  if (this.activeMarker_ ) {
    this.activeMarker_.setIcon(this.shopIcon_);
  }

  this.activeMarker_ = marker;
  this.activeMarkerKey_ = marker.key;

  var that = this;
  $.post('/stores', data, function(data) {
    that.showShop(marker, data);
  });
};

Listing.prototype.showShop = function(marker, shop) {
  if (this.addNewMarker_) {
    this.addNewMarker_.setMap(null);
  }
  this.newInfoWindowIsOpen_ = true;

  var html = '<div id="shop-info">' +
    '<div><h1>' + shop.name + ' ';
  for (var i = 1; i < 6; i++) {
    if (i <= shop.rating) {
      html += '<span class="star-full"></span>';
    } else {
      html += '<span class="star-empty"></span>';
    }
  }

  html += '</h1></div>' +
    '<div class="row">' + shop.address + '</div>' +
    '<div class="row"><button id="get-directions">Directions</button> ' +
    '<button id="close-shop-info">Close</button>' +
    '</div>' +
    '</div>';

  var html = $(html);

  var directions = $('#get-directions', html);

  var that = this;
  $(directions).click(function() {
    that.getDirectionsTo(shop);
    return false;
  });

  var close = $('#close-shop-info', html);
  $(close).click(function() {
    that.closeInfo_();
  });

  $('#info').html(html);
  $('#info').show();
  this.setMapHeight();
};

Listing.prototype.getDirectionsTo = function(shop) {
  if (!this.directionsService_) {
    this.directionsService_ = new google.maps.DirectionsService();
    this.directionsRenderer_ = new google.maps.DirectionsRenderer({
      suppressMarkers: true,
      polylineOptions: {
        strokeColor: '#cc00ff'
      }
    });
    this.directionsRenderer_.setMap(this.map_);
  }

  var request = {
    origin: this.userLocationMarker_.getPosition(),
    destination: shop.address,
    travelMode: google.maps.DirectionsTravelMode.WALKING
  };

  var that = this;
  this.directionsService_.route(request, function(result, status) {
    if (status == google.maps.DirectionsStatus.OK) {
      that.directionsRenderer_.setDirections(result);
    }
  });
};

Listing.prototype.setupAddNew_ = function() {
  var that = this;
  $('#add-new').click(function(e) {
    if (this.newShopForm_) {
      $('#new-shop-name').val('');
      $('#new-shop-address').val('');
      $('#new-shop-rating').val('');
    }
    that.addNew_(e);
    return false;
  });
};

Listing.prototype.NEW_SHOP_FORM_HTML = '<div id="add-new-shop-form">' +
  '<h1>Add a new Listing Shop</h1>' +
  '<div class="row"><label>Name:</label>' +
  '<span id="new-shop-name-options"></span> ' +
  '<input type="text" id="new-shop-name"/></div>' +
  '<div class="row"><label>Address:</label><input type="text" id="new-shop-address"/></div>' +
  '<div class="row"><label>Rating:</label>' +
  '<select id="new-shop-rating">' +
  '<option value="1">1</option>' +
  '<option value="2">2</option>' +
  '<option value="3">3</option>' +
  '<option value="4">4</option>' +
  '<option value="5">5</option>' +
  '</select>' +
  '</div>' +
  '<div class="row"><button id="new-shop-save">Add!</button> ' +
  '<button id="new-shop-close">Close</button></div>' +
  '</div>';

Listing.prototype.NEW_SHOP_FORM_HTML = '<div id="add-new-shop-form">' +
'<h1>Add a new Listing</h1>' +
'<form method="POST" action="/add"><table><tr><th><label for="id_address">Address:</label></th><td><input type="text" name="address" id="id_address" /></td></tr>' +
'<tr><th><label for="id_price">Price:</label></th><td><input type="text" name="price" id="id_price" /></td></tr>' +
'<tr><th><label for="id_baths">Baths:</label></th><td><input type="text" name="baths" id="id_baths" /></td></tr>' +
'<tr><th><label for="id_beds">Beds:</label></th><td><input type="text" name="beds" id="id_beds" /></td></tr>' +
'<tr><th><label for="id_size">Size:</label></th><td><input type="text" name="size" id="id_size" /></td></tr>' +
'<tr><th><label for="id_phone_number">Phone number:</label></th><td><input type="text" name="phone_number" id="id_phone_number" /></td></tr>' +
'<tr><th><label for="id_comments">Comments:</label></th><td><input type="text" name="comments" id="id_comments" /></td></tr>' +
'<tr><th><label for="id_property_type">Property type:</label></th><td><input type="text" name="property_type" id="id_property_type" /></td></tr>' +
'<tr><th><label for="id_amenities">Amenities:</label></th><td><input type="text" name="amenities" id="id_amenities" /></td></tr>' +
'<tr><th><label for="id_author">Author:</label></th><td><input type="text" name="author" id="id_author" /></td></tr>' +
'<tr><th><label for="id_createDate">CreateDate:</label></th><td><input type="text" name="createDate" id="id_createDate" /></td></tr>' +
'<tr><th><label for="id_lastUpdateDate">LastUpdateDate:</label></th><td><input type="text" name="lastUpdateDate" id="id_lastUpdateDate" /></td></tr>' +
'<tr><th><label for="id_status">Status:</label></th><td><input type="text" name="status" id="id_status" /></td></tr>' +
'<tr><th><label for="id_tag">Tag:</label></th><td><input type="text" name="tag" id="id_tag" /></td></tr></table><input type="submit"></form>' +
'</div>' +
'<div class="row"><button id="new-shop-save">Add!</button> ' +
'<button id="new-shop-close">Close</button></div>' +
'</div>';


Listing.prototype.saveNewShop_ = function() {
  if ($('#new-shop-name').css('display') == 'none') {
    var name = $.trim($('#places-options').val());
  } else {
    var name = $.trim($('#new-shop-name').val());
  }

  var address = $.trim($('#new-shop-address').val());
  var rating = $.trim($('#new-shop-rating').val());
  var pos = this.addNewMarker_.getPosition();

  $('#new-shop-name').val('');
  $('#new-shop-address').val('');
  $('#new-shop-rating').val('');

  if (name == '' || address == '') {
    window.alert('Name and address are required');
    return;
  }

  var data = {
    action: 'new',
    name: name,
    address: address,
    rating: rating,
    lat: pos.lat(),
    lng: pos.lng()
  };

  var that = this;
  $.post('/stores', data, function(data) {
    that.newStoreComplete_(data);
  });
};

Listing.prototype.newStoreComplete_ = function(shop) {
  var marker = this.addStoreMarker_(shop);
  this.shopMarkers_[shop.key] = marker;
  this.addNewMarker_.setMap(null);
  this.newInfoWindowIsOpen_ = false;
  this.closeInfo_();
};

Listing.prototype.setupNewShopForm_ = function() {
  this.newShopForm_ = $(this.NEW_SHOP_FORM_HTML);
  var saveForm = $('#new-shop-save', this.newShopForm_);

  var that = this;
  $(saveForm).click(function() {
    that.saveNewShop_();
    return false;
  });

  var closeForm = $('#new-shop-close', this.newShopForm_);

  $(closeForm).click(function() {
    that.closeInfo_();
    return false;
  });
};

Listing.prototype.closeInfo_ = function() {
  $('#info').hide();
  this.newInfoWindowIsOpen_ = false;
  if (this.addNewMarker_) {
    this.addNewMarker_.setMap(null);
  }

  if (this.activeMarker_ ) {
    this.activeMarker_.setIcon(this.shopIcon_);
    this.activeMarkerKey_ = false;
  }

  this.setMapHeight();
};

Listing.prototype.addNew_ = function(e) {
  if (!this.addNewMarker_) {
    this.addNewMarker_ = new google.maps.Marker({
      zIndex: 190,
      clickable: false
    });
    var that = this;
    google.maps.event.addListener(this.map_, 'click', function(e) {
      that.addNewMarker_.setPosition(e.latLng);
      if (that.newInfoWindowIsOpen_ && that.addNewMarker_.getMap()) {
        that.reverseGeocodeNewStore_();
        that.getPlaces_();
      }
    });
    this.setupNewShopForm_();
  }
  $('#info').html(this.newShopForm_);
  this.setupNewShopForm_()
  this.addNewMarker_.setMap(this.map_);
  this.addNewMarker_.setPosition(this.map_.getCenter());
  this.newInfoWindowIsOpen_ = true;
  $('#info').show();

  if (this.activeMarker_ ) {
    this.activeMarker_.setIcon(this.shopIcon_);
    this.activeMarkerKey_ = false;
  }

  this.setMapHeight();
  this.reverseGeocodeNewStore_();
  this.getPlaces_();
};


Listing.prototype.reverseGeocodeNewStore_ = function() {
  if (!this.geocoder_) {
    this.geocoder_ = new google.maps.Geocoder();
  }

  var that = this;
  var request = {latLng: this.addNewMarker_.getPosition()};
  this.geocoder_.geocode(request, function(results, status) {
    that.handleNewStoreGeocode_(results, status);
  });
};

Listing.prototype.handleNewStoreGeocode_ = function(results, status) {
  var formattedAddress;
  if (status == google.maps.GeocoderStatus.OK) {
    if (results[0]) {
      formattedAddress = results[0].formatted_address;
    }
  }

  if (formattedAddress) {
    $('#new-shop-address').val(formattedAddress);
  }
};

Listing.prototype.setMapHeight = function() {
  var windowHeight = $(window).height();
  var footerHeight = $('#footer').height();
  var contentPos = $('#content').offset();
  var availableHeight = windowHeight - footerHeight - contentPos.top - 2;

  var mapDiv = $(this.mapDiv_);

  if (this.newInfoWindowIsOpen_) {
    var infoHeight = $('#info').height();
    availableHeight -= (infoHeight + 1);
  }
  mapDiv.css('height', availableHeight);
  if (this.map_) {
    google.maps.event.trigger(this.map_, 'resize');
  }
};

google.maps.event.addDomListenerOnce(window, 'load', function() {
  var listing = new Listing('map');
});


















var PAGE_PATH = document.location.href.replace(/#.*/, '')
.replace(/\/[^\/]*$/, '/');

var MILES_TO_METERS = 1609.344;

var TYPES = {
'Multi-Family Home': 'Multi-Family Home',
'Townhome': 'Townhome',
'Condo': 'Condo',
'Other': 'Other'
};

//Only perform proximity searches on 
//geocode accuracy.
var MIN_PROXIMITY_SEARCH_GEOCODE_ACCURACY = 6;

var MAX_PROXIMITY_SEARCH_MILES = 50;
var MAX_PROXIMITY_SEARCH_RESULTS = 10;
var MAX_BOUNDS_SEARCH_RESULTS = 25;

var MIN_GRADE_TAUGHT = -1; // PK
var MAX_GRADE_TAUGHT = 12; // 12th grade

/**
* @type google.maps.Map2
*/
var map;

/**
* @type google.maps.ClientGeocoder
*/
//var geocoder;

var g_listView = false; // Whether or not we're in list view.

/**
* An array of the current search result data objects.
* Result object properties are:
*   {Number} lat
*   {Number} lng
*   {String} name
*   {String} icon
*   {google.maps.Marker} marker
*   {Number} [distance] The distance in meters from the search center.
*   {jQuery object} listItem The list view item for the result.
*   ...
* Along with any other properties returned by the search service.
*/
var g_searchResults = null;

var g_currentSearchXHR = null; // For cancelling current XHRs.
var g_searchOptions = null; // Last options passed to doSearch.
var g_searchCenterMarker = null;

var g_mapAutoScrollInterval = null;
var g_programmaticPanning = false; // Temporary moveend disable switch.
var g_mapPanListener = null;

/**
* On body/APIs ready callback.
*/
function init() {
initMap();
initUI();
}

/**
* Creates the Google Maps API instance.
*/
function initMap() {
map = new google.maps.Map2($('#map').get(0));
map.setCenter(new google.maps.LatLng(39,-96), 4);

geocoder = new google.maps.Geocoder();

// anything besides default will not work in list view
map.setUIToDefault();
}

/**
* Initializes various UI features.
*/
function initUI() {
$("#search-grade-slider").slider({
orientation: 'horizontal',
min: -1,
max: 12,
range: true,
step: 1,
values: [-1, 12],
slide: function(event, ui) {
if (ui.values[0] == ui.values[1])
$("#search-grade-display").text(formatGradeLevel(ui.values[0]));
else
$("#search-grade-display").text(
formatGradeLevel(ui.values[0]) + ' to ' +
formatGradeLevel(ui.values[1]));
},
change: function(event, ui) {
if (!g_searchOptions)
return;

doSearch(updateObject(g_searchOptions, {
gradeRange: (ui.values[0] != MIN_GRADE_TAUGHT ||
ui.values[1] != MAX_GRADE_TAUGHT) ? ui.values : null,
retainViewport: true,
clearResultsImmediately: false
}));
}
});

$("#search-grade-display").text(
formatGradeLevel(10000) + ' to ' +
formatGradeLevel(20000000));

for (var property_type in TYPES) {
var option = $('<option value="' + property_type + '">' +
TYPES[property_type] + '</option>');
$('#search-property-type').append(option);
}

$('#search-property-type').change(function() {
doSearch(updateObject(g_searchOptions, {
property_type: $(this).val(),
retainViewport: true,
clearResultsImmediately: false
}));
});

$('#view-toggle a').click(function() {
g_programmaticPanning = true;
var center = map.getCenter();

if (g_listView) {
$(this).html('List view &raquo;');
$('#content').removeClass('list-view');
enableSearchOnPan(g_searchOptions != null);
} else {
$(this).html('&laquo; Map view');
$('#content').addClass('list-view');
enableSearchOnPan(false);
}

g_listView = !g_listView;
map.checkResize();

enableMapAutoScroll(g_listView);

map.setCenter(center);
g_programmaticPanning = false;
return false;
});

var advancedOptionsVisible = false;

$('#advanced-options-toggle').click(function() {
if (advancedOptionsVisible) {
$('#advanced-options').hide();
} else {
$('#advanced-options').show();
}

advancedOptionsVisible = !advancedOptionsVisible;
return false;
});

var resetError = function() {
$('#search-error').css('visibility', 'hidden');
};

$('#search-query').change(resetError);
$('#search-query').keypress(resetError);
}

/**
* Enables or disables search-on-pan, which performs new queries upon panning
* of the map.
* @param {Boolean} enable Set to true to enable, false to disable.
*/
function enableSearchOnPan(enable) {
if (typeof(enable) == 'undefined')
enable = true;

if (!enable) {
if (g_mapPanListener)
google.maps.Event.removeListener(g_mapPanListener);
g_mapPanListener = null;
} else if (!g_mapPanListener) {
g_mapPanListener = google.maps.Event.addListener(map, 'moveend',
function() {
if (g_programmaticPanning ||
(map.getInfoWindow() && !map.getInfoWindow().isHidden()))
return;

// Determine whether or not to do a proximity query or
// a bounds query.
var bounds = map.getBounds();
var searchType = 'bounds';

if (g_searchOptions.center &&
bounds.containsLatLng(g_searchOptions.center))
searchType = 'proximity';

// On pan, no need to re-do a proximity search.
if (searchType == 'proximity' &&
g_searchOptions.type == 'proximity')
return;

doSearch(updateObject(g_searchOptions, {
type: searchType,
bounds: bounds,
retainViewport: true,
clearResultsImmediately: false
}));
});
}
}

/**
* Enables or disables map auto scrolling.
* @param {Boolean} enable Set to true to enable, false to disable.
*/
function enableMapAutoScroll(enable) {
if (typeof(enable) == 'undefined')
enable = true;

if (g_mapAutoScrollInterval) {
window.clearTimeout(g_mapAutoScrollInterval);
g_mapAutoScrollInterval = null;
}

var mapContainer = $('#map-container');
var mapContainerOffsetParent = $($('#map-container').get(0).offsetParent)

var TOP_PADDING = 8;

if (enable) {
g_mapAutoScrollInterval = window.setInterval(function() {
var scrollOffset = window.pageYOffset || document.body.scrollTop;
mapContainer.animate({
top: Math.max(0, scrollOffset -
mapContainerOffsetParent.position().top +
TOP_PADDING)
}, 'fast');
}, 1000);
} else {
mapContainer.css('top', '');
}
}

/**
* Geocodes the location text in the search box and performs a spatial search
* via doSearch.
*/
function doGeocodeAndSearch() {
$('#loading').css('visibility', 'visible');
geoParams = {
					 address: 'Boca Raton, FL'	
};
geocoder.geocode(geoParams, function(response) {
if (response == null || response.formatted_address == null ) {
$('#search-error').text('Location not found.');
$('#search-error').css('visibility', 'visible');
$('#loading').css('visibility', 'hidden');
} else {
$('#search-query').val(response.formatted_address);
var bounds = response.geometry.bounds;

map.setCenter(bounds.getCenter(), map.getBoundsZoomLevel(bounds));

var proximitySearch = false;

var commonOptions = {
clearResultsImmediately: true
};

var searchGradeRange = $('#search-price-slider').slider('values');
if (searchGradeRange[0] < searchGradeRange[1]) {
commonOptions.gradeRange = searchGradeRange;
}

commonOptions.property_type = $('#search-property_type').val();

if (proximitySearch) {
doSearch(updateObject(commonOptions, {
type: 'proximity',
centerAddress: response.formatted_address,
center: bounds.getCenter()
}));
} else {
doSearch(updateObject(commonOptions, {
type: 'bounds',
bounds: bounds
}));
}
}
});
}

/**
* Performs an asynchronous school search using the search service.
* @param {Object} options Search options.
* @param {String} type The type of spatial query to perform; either
*     'proximity' or 'bounds'.
* @param {google.maps.LatLng} [center] For proximity searches, the search
*     center.
* @param {String} [centerAddress] For proximity searches, an optional address
*     string representing the search center.
* @param {google.maps.LatLngBounds} [bounds] For bounds searches, the bounding
*     box to constrain results to.
* @param {Boolean} [retainViewport=false] Whether or not to maintain the
*     map viewport after retrieving search results.
* @param {Boolean} [clearResultsImmediately=false] Whether or not to clear
*     search results immediately, as opposed to clearing them only upon a
*     successful completion of the search.
*/
function doSearch(options) {
options = options || {};

var oldSearchOptions = g_searchOptions;
g_searchOptions = options;

if (g_currentSearchXHR && 'abort' in g_currentSearchXHR) {
g_currentSearchXHR.abort();
}

$('#search-error').css('visibility', 'hidden');
$('#loading').css('visibility', 'visible');

if (g_searchCenterMarker) {
map.removeOverlay(g_searchCenterMarker);
g_searchCenterMarker = null;
}

if (options.type == 'proximity') {
// Set up search center marker.
var centerIcon = new google.maps.Icon(G_DEFAULT_ICON); 
centerIcon.image = '/static/images/markers/arrow.png';
centerIcon.shadow = '/static/images/markers/arrow-shadow.png';
centerIcon.iconSize = new google.maps.Size(23, 34);
centerIcon.iconAnchor = new google.maps.Point(11, 34);

g_searchCenterMarker = new google.maps.Marker(options.center, {
icon: centerIcon,
draggable: true,
zIndexProcess: function(){ return 1000; }
});

google.maps.Event.addListener(g_searchCenterMarker, 'dragend', function() {
// Perform a new search but persist some old parameters.
doSearch(updateObject(g_searchOptions, {
type: 'proximity',
centerAddress: '', // TODO: reverse geocode?
center: g_searchCenterMarker.getLatLng(),
retainViewport: true,
clearResultsImmediately: false
}));
});

map.addOverlay(g_searchCenterMarker);
}

var newBounds = new google.maps.LatLngBounds(
options.type == 'proximity' ? options.center : null);

var listView = $('#list-view');

if (options.clearResultsImmediately)
clearSearchResults();

$('#list-view-status').html('Searching...');

var searchParameters = {
type: options.type
};

if (options.type == 'proximity') {
searchParameters = updateObject(searchParameters, {
lat: options.center.lat(),
lon: options.center.lng(),
maxresults: MAX_PROXIMITY_SEARCH_RESULTS,
maxdistance: MAX_PROXIMITY_SEARCH_MILES * MILES_TO_METERS
});
} else if (options.type == 'bounds') {
searchParameters = updateObject(searchParameters, {
north: options.bounds.getNorthEast().lat(),
east: options.bounds.getNorthEast().lng(),
south: options.bounds.getSouthWest().lat(),
west: options.bounds.getSouthWest().lng(),
maxresults: MAX_BOUNDS_SEARCH_RESULTS
});
}

// Add in advanced options.
if (options.gradeRange) {
searchParameters = updateObject(searchParameters, {
mingrade: options.gradeRange[0],
maxgrade: options.gradeRange[1]
});
}

if (options.schoolType) {
searchParameters.property_type = options.property_type;
}

// Perform proximity or bounds search.
g_currentSearchXHR = $.ajax({
url: '/s/search',
type: 'get',
data: searchParameters,
dataType: 'json',
error: function(xhr, textStatus) {
// TODO: parse JSON instead of eval'ing
var responseObj;
eval('responseObj=' + xhr.responseText);
$('#search-error, #list-view-status').text(
'Internal error: ' + responseObj.error.message);
$('#search-error').css('visibility', 'visible');
$('#loading').css('visibility', 'hidden');
},
success: function(obj) {
g_currentSearchXHR = null;

$('#loading').css({ visibility: 'hidden' });

if (!options.clearResultsImmediately)
clearSearchResults();

if (obj.status && obj.status == 'success') {
for (var i = 0; i < obj.results.length; i++) {
var result = obj.results[i];

result.icon = '/static/images/markers/simple.png';
if (options.type == 'proximity' && i <= 10) {
result.icon = '/static/images/markers/' +
String.fromCharCode(65 + i) + '.png';
}

var resultLatLng = new google.maps.LatLng(result.lat, result.lng);

if (options.type == 'proximity')
result.distance = resultLatLng.distanceFrom(options.center);

newBounds.extend(resultLatLng);

// Create result marker.
result.marker = createResultMarker(result);
map.addOverlay(result.marker);

// Create result list view item.
result.listItem = createListViewItem(result);
listView.append(result.listItem);

g_searchResults.push(result);
}

if (newBounds.getNorthEast() &&
!newBounds.getNorthEast().equals(newBounds.getSouthWest()) &&
!options.retainViewport &&
obj.results.length) {
g_programmaticPanning = true;
map.panTo(newBounds.getCenter());
map.setZoom(map.getBoundsZoomLevel(newBounds));
g_programmaticPanning = false;
}

if (!obj.results.length) {
$('#search-error, #list-view-status').text(
(options.type == 'proximity')
? 'No results within ' + MAX_PROXIMITY_SEARCH_MILES + ' miles.'
: 'No results in view.');
$('#search-error').css('visibility', 'visible');
} else {
$('#list-view-status').html(
'Found ' + obj.results.length + ' result(s)' +
(options.centerAddress
? ' near ' + options.centerAddress + ':'
: ':'));
}
} else {
$('#search-error, #list-view-status').text(
'Internal error: ' + obj.error.message);
$('#search-error').css('visibility', 'visible');
}
}
});

enableSearchOnPan();
}

/**
* Clears search results from memory, the list view, and the map view.
*/
function clearSearchResults() {
if (g_searchResults) {
$('#list-view').html('');
$('#list-view-status').text('Enter a search location to search');
for (var i = 0; i < g_searchResults.length; i++) {
map.removeOverlay(g_searchResults[i].marker);
}
}

g_searchResults = [];
}

/**
* Creates a search result marker from the given result object.
* @param {Object} result The search result data object.
* @type google.maps.Marker
*/
function createResultMarker(result) {
var icon = new google.maps.Icon(G_DEFAULT_ICON);
icon.image = result.icon;
icon.iconSize = new google.maps.Size(21, 34);

var resultLatLng = new google.maps.LatLng(result.lat, result.lng);

var marker = new google.maps.Marker(resultLatLng, {
icon: icon,
title: result.name
});

google.maps.Event.addListener(marker, 'click', (function(result) {
return function() {
if (g_listView && result.listItem) {
$.scrollTo(result.listItem, {duration: 1000});
} else {
var infoHtml = tmpl('tpl_result_info_window', { result: result });

map.openInfoWindowHtml(marker.getLatLng(), infoHtml, {
pixelOffset: new GSize(icon.infoWindowAnchor.x - icon.iconAnchor.x,
icon.infoWindowAnchor.y - icon.iconAnchor.y)});
}
};
})(result));

return marker;
}

/**
* Creates a list view item from the given result object.
* @param {Object} result The search result data object.
* @type jQuery object
*/
function createListViewItem(result) {
var item = $('<li class="result">');
item.html(tmpl('tpl_result_list_item', { result: result }));
return item;
}

/**
* Helper method to update one object's properties with another's.
*/
function updateObject(dest, src) {
dest = dest || {};
src = src || {};

for (var k in src)
dest[k] = src[k];

return dest;
}

/**
* Formats a grade level for display purposes; i.e. returns 'PK' for level=-1,
* 'K' for level=0, etc.
* @param {Number} level The grade level code; -1 for PK, 0 for K,
*     n for grade n.
* @type String
*/
function formatGradeLevel(level) {
if (level === null || typeof(level) == 'undefined')
return '';

if (level == -1) return 'PK';
else if (level == 0) return 'K';

return level.toString();
}

/**
* Formats a distance in meters to a human readable distance in miles.
* @param {Number} distance The distance in meters.
* @type String
*/
function formatDistance(distance) {
return (distance / MILES_TO_METERS).toFixed(1) + ' mi';
}