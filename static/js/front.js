/*
Copyright 2009 Roman Nurik

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

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
var MIN_PROXIMITY_SEARCH_GEOCODE_ACCURACY = 5;

var MAX_PROXIMITY_SEARCH_MILES = 100;
var MAX_PROXIMITY_SEARCH_RESULTS = 100;
var MAX_BOUNDS_SEARCH_RESULTS = 100;

var MIN_GRADE_TAUGHT = -1; // PK
var MAX_GRADE_TAUGHT = 12; // 12th grade

/**
 * @type google.maps.Map2
 */
var map;

/**
 * @type google.maps.ClientGeocoder
 */
var geocoder;

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
	mapOptions = {}
	  if (GBrowserIsCompatible()) {
		  var mapOptions = {
		    googleBarOptions : {
		      style : "new",
		      adsOptions: {
		        client: "partner-google-maps-api",
		        channel: "AdSense for Search channel",
		        adsafe: "high",
		        language: "en"
		      }
		    }
		  }
	  }
	
  map = new google.maps.Map2($('#map').get(0), mapOptions);
  http://code.google.com/apis/maps/documentation/javascript/v2/reference.html#GMap2.enableGoogleBar
  map.setCenter(new google.maps.LatLng(39,-96), 4);
  map.enableGoogleBar();
  geocoder = new google.maps.ClientGeocoder();
  
  // anything besides default will not work in list view
  map.setUIToDefault();
  
  var publisher_id = "partner-pub-6540327609469868";

  var adsManagerOptions = {
    maxAdsOnMap : 2,
    style: G_ADSMANAGER_STYLE_ADUNIT,
    // The channel field is optional - replace this field with a channel number 
    // for Google AdSense tracking
    channel: 'your_channel_id'  
  };

  adsManager = new GAdsManager(map, publisher_id, adsManagerOptions);
  adsManager.enable();
  
  if (geoip_city() != null && geoip_region() != null && geoip_country_name() != null) {
		centerPt = geoip_city() + ', ' + geoip_region() + " " + geoip_country_name();
		$('#search-query').val(centerPt);
		YUI().use('history', function(Y) {
			 
			var history = new Y.HistoryHash();
			history.addValue('q', centerPt);
		});
		doGeocodeAndSearch();
	}
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
  geocoder.getLocations($('#search-query').val(), function(response) {
    if (response.Status.code != 200 || !response.Placemark) {
      $('#search-error').text('Location not found.');
      $('#search-error').css('visibility', 'visible');
      $('#loading').css('visibility', 'hidden');
    } else {
      $('#search-query').val(response.Placemark[0].address);
      YUI().use('history', function(Y) {
    	  
    		var history = new Y.HistoryHash();
    		history.addValue('q', response.Placemark[0].address);
    	});
      var bounds = new google.maps.LatLngBounds(
          new google.maps.LatLng(
            response.Placemark[0].ExtendedData.LatLonBox.south,
            response.Placemark[0].ExtendedData.LatLonBox.west),
          new google.maps.LatLng(
            response.Placemark[0].ExtendedData.LatLonBox.north,
            response.Placemark[0].ExtendedData.LatLonBox.east));

      map.setCenter(bounds.getCenter(), map.getBoundsZoomLevel(bounds));
      
      var proximitySearch = (response.Placemark[0].AddressDetails.Accuracy >=
                             MIN_PROXIMITY_SEARCH_GEOCODE_ACCURACY);
      
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
          centerAddress: response.Placemark[0].address,
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






$(function() {
    $("#add-listing-toggle").live('click', function(event) {
    	
    	var popWindow = '<div class="messagepop pop"><form method="POST" id="new_message" action="/add" enctype="multipart/form-data"><table><tr><th><label for="id_address">Address: </label></th><td><textarea type="textarea" name="address" id="id_address" /></td></tr>' + 
    	'<tr><th><label for="id_price">Price: </label></th><td><input type="text" name="price" id="id_price" /></td></tr> ' + 
    	'<tr><th><label for="id_baths">Baths: </label></th><td><input type="text" name="baths" id="id_baths" /></td></tr> ' + 
    	'<tr><th><label for="id_beds">Beds: </label></th><td><input type="text" name="beds" id="id_beds" /></td></tr> ' + 
    	'<tr><th><label for="id_size">Size: </label></th><td><input type="text" name="size" id="id_size" /></td></tr> ' + 
    	//'<tr><th><label for="id_phone_number">Phone number:</label></th><td><input type="text" name="phone_number" id="id_phone_number" /></td></tr> ' + 
    	'<tr><th><label for="id_comments">Description: </label></th><td><textarea name="comments" id="id_comments" rows="6" cols="40"></textarea></td></tr> ' + 
    	'<tr><th><label for="id_property_type">Property Type: </label></th><td><input type="text" name="property_type" id="id_property_type" /></td></tr> ' + 
    	'<tr><th><label for="id_amenities">Amenities: </label></th><td><input type="text" name="amenities" id="id_amenities" /></td></tr> ' + 
    	// '<tr><th><label for="id_author">Author: </label></th><td><input type="text" name="author" id="id_author" /></td></tr> ' + 
    	// '<tr><th><label for="id_photo">Photo: <input type="file" name="photo" id="id_photo"/></td></tr>' + 
    	// '<!--<tr><th><label for="id_createDate">CreateDate: </label></th><td><input type="text" name="createDate" id="id_createDate" /></td></tr> ' + 
    	// '<tr><th><label for="id_lastUpdateDate">LastUpdateDate: </label></th><td><input type="text" name="lastUpdateDate" id="id_lastUpdateDate" /></td></tr> ' + 
    	// '<tr><th><label for="id_status">Status:</label></th><td><input type="text" name="status" id="id_status" /></td></tr> ' + 
    	// '<tr><th><label for="id_tag">Tags:< /label></th><td><input type="text" name="tag" id="id_tag" /></td></tr>--></table><input type="submit" value="Send Message" name="commit" id="message_submit"/> or <a class="close" href="/">Cancel</a></form></div>';
    	
        $(this).addClass("selected").parent().append(popWindow);
        $(".pop").slideFadeToggle()
        $("#email").focus();
        return false;
    });

    $(".close").live('click', function() {
        $(".pop").slideFadeToggle();
        $("#add-listing-toggle").removeClass("selected");
        return false;
    });
});

$.fn.slideFadeToggle = function(easing, callback) {
    return this.animate({ opacity: 'toggle', height: 'toggle' }, "fast", easing, callback);
};