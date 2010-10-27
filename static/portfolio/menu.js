function Menu(mocklist, user) {
  this.page_mocklist_ = mocklist;
  this.page_mocklist_.addListener(this.mockListListener_.bind(this));
  this.signed_in_ = user.signed_in;

  // Doesn't contain valid mocklist data, just id and name.
  this.mocklists_ = user.mocklists;
  this.username_ = user.name;
  this.sign_in_url_ = user.sign_in_url;
  this.sign_out_url_ = user.sign_out_url;

  // Edit controls (right side).
  this.node_ = createElement('div', 'home', document.body);

  this.node_new_ = createElement('a', 'menuitem', this.node_);
  this.node_new_.href = '/p';

  this.node_menu_ = createElement('select', 'menuitem', this.node_);
  var opt = new Option("Your mocks:", "", false, false);
  this.node_menu_.options[this.node_menu_.length] = opt;
  addEventListener(this.node_menu_, 'change', this.menuChanged_.bind(this));

  if (this.signed_in_) {
    // this.node_name_ = createElement('a', 'menuitem', this.node_);
    // setText(this.node_name_, this.username_);

    this.node_sign_ = createElement('a', 'menuitem', this.node_);
    this.node_sign_.href = this.sign_out_url_;
    setText(this.node_sign_, "Sign out");
  } else {
    this.node_sign_ = createElement('a', 'menuitem button', this.node_);
    this.node_sign_.href = this.sign_in_url_;

    this.node_new_.className = 'menuitem button';
    setText(this.node_sign_, "Sign in");
  }

  // Sharing bar (left side).
  this.node_share_ = createElement('div', 'sharebar', document.body);

  // TODO: Defer this until after page load.
  this.node_tweet_ = createElement('div', '', this.node_share_);
  this.node_tweet_.innerHTML = '';

  var twitter_script = document.createElement('script');
  twitter_script.src = 'http://platform.twitter.com/widgets.js';
  twitter_script.defer = true;
  this.node_share_.appendChild(twitter_script);

  this.update_();
}

Menu.prototype.mockListListener_ = function(e) {
  if (e.type == MockList.EVENT_SAVED) {
    if (!this.getMockListById(this.page_mocklist_.id)) {
      this.mocklists_.push({
        'id' : this.page_mocklist_.id,
        'name' : this.page_mocklist_.name
      });
      this.update_();
    }
  } else if (e.type == MockList.EVENT_NAMECHANGED) {
    this.getMockListById(this.page_mocklist_.id).name = this.page_mocklist_.name;
    this.update_();
  } else if (e.type == MockList.EVENT_DELETED) {
    this.node_.style.bottom = 25;
    this.node_.style.opacity = 0;
  }
}

Menu.prototype.getMockListById = function(id) {
  for (var i = 0, mocklist; mocklist = this.mocklists_[i]; i++) {
    if (mocklist.id == id) {
      return mocklist;
    }
  }
  return false;
}

Menu.prototype.update_ = function() {
  // window.console.log("Menu updating");
  
  this.node_new_.style.display = (this.page_mocklist_.id) ? 'inline-block' : 'none';
  this.node_share_.style.display = (this.page_mocklist_.id) ? 'block' : 'none';

  if (this.signed_in_ || this.page_mocklist_.key) {
    setText(this.node_new_, 'New');
    this.node_sign_.style.display = 'inline-block';
  } else {
    setText(this.node_new_, 'Create Gallery');
    this.node_sign_.style.display = 'none';
  }

  this.node_menu_.options.length = 1;
  for (var i = 0, mocklist; mocklist = this.mocklists_[i]; i++) {
    var selected = (mocklist.id == this.page_mocklist_.id);
    var name = mocklist.name ? mocklist.name : mocklist.id;
    var opt = new Option(name, mocklist.id, selected, selected);
    this.node_menu_.options[this.node_menu_.length] = opt;
  }

  this.node_menu_.style.display = (this.mocklists_.length) ? 'inline-block' : 'none';
}

Menu.prototype.menuChanged_ = function() {
  var v = this.node_menu_.value;
  if (v) {
    window.location.href = MockList.URL_VIEWER_BASE + v;
  }
}