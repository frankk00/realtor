﻿/*
@author: Karl-Johan Sjögren / http://blog.crazybeavers.se/
@url: http://blog.crazybeavers.se/wp-content/demos/jquery.tag.editor/
@license: Creative Commons License - ShareAlike http://creativecommons.org/licenses/by-sa/3.0/
@version: 1.2
@changelog
 1.2
  Fixed bug with completeOnSeparator for Firefox
  Fixed so that pressing return on an empty editor would submit the form
 1.1
  Initial public release
  Added the completeOnSeparator and completeOnBlur options
*/
(function($) {
    $.fn.extend({
        tagEditor: function(options) {
            var defaults = {
                separator: ',',
                items: [],
                className: 'tagEditor',
                confirmRemoval: false,
                completeOnSeparator: false,
                completeOnBlur: false,
                listingId : 0
            }

            var options = $.extend(defaults, options);
            var listBase, textBase = this, hiddenText;
            var itemBase = [];

            return this.each(function() {
                hiddenText = $(document.createElement('input'));
                hiddenText.attr('type', 'hidden');
                textBase.after(hiddenText);

                listBase = $(document.createElement('ul'));
                listBase.attr('class', options.className);
                $(this).after(listBase);

                for (var i = 0; i < options.items.length; i++) {
                    addTag(jQuery.trim(options.items[i]));
                }

                buildArray();
                $(this).keypress(handleKeys);
                $(this).blur(parse);

                var form = $(this).parents("form");
                form.submit(function() {
                    parse();
                    hiddenText.val(itemBase.join(options.separator));
                    hiddenText.attr("id", textBase.attr("id"));
                    hiddenText.attr("name", textBase.attr("name"));
                    textBase.attr("id", textBase.attr("id") + '_old');
                    textBase.attr("name", textBase.attr("name") + '_old');
                });

                function addTag(tag) {
                    tag = jQuery.trim(tag);
                    for (var i = 0; i < itemBase.length; i++) {
                        if (itemBase[i].toLowerCase() == tag.toLowerCase())
                            return;
                    }
					
					// limit to 4
					if(itemBase.length < 3)
					{
	                    var item = $(document.createElement('li'));
	                    item.text(tag);
	                    item.attr('title', 'Remove tag');
	                    item.click(function() {
	                        if (options.confirmRemoval)
	                            if (!confirm("Do you really want to remove the tag?"))
	                            return;
	
	                        item.remove();
	                        parse();
	                    });
	
	                    listBase.append(item);
	                }
                }

                function buildArray() {
                    itemBase = [];
                    var items = $("li", listBase);

                    for (var i = 0; i < items.length; i++) {
                        itemBase.push(jQuery.trim($(items[i]).text()));
                    }
               		
               		$.get( '/utils/updateTags.php?tags=' + itemBase + '&listingId=' + options.listingId,
					function(data) {
					    //alert("Data Loaded: " + data);
			        })
               		
                }

                function parse() {
                    var items = textBase.val().split(options.separator);

                    for (var i = 0; i < items.length; i++) {
                        var trimmedItem = jQuery.trim(items[i]);
                        if (trimmedItem.length > 0)
                            addTag(trimmedItem);
                    }
                    textBase.val("");
                    buildArray();
                }

                function handleKeys(ev) {
                    var keyCode = (ev.which) ? ev.which : ev.keyCode;

                    if (options.completeOnSeparator) {
                        if (String.fromCharCode(keyCode) == options.separator) {
                            parse();
                            return false;
                        }
                    }

                    switch (keyCode) {
                        case 13:
                            {
                                if (jQuery.trim(textBase.val()) != '') {
                                    parse();
                                    return false;
                                }
                                return true;
                            }
                    }
                }
            });
        }
    });
})(jQuery);