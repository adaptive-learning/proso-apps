(function() {
  'use strict';
  /* Filters */
  angular.module('adaptivePractice.filters', [])

  .filter('percent', function() {
    return function(n) {
      n = n || 0;
      return Math.round(100 * n) + '%';
    };
  })

  .filter('StatesFromPlaces', function() {
    return function(data) {
      var places = {};
      if (data && data[0]) {
        angular.forEach(data, function(category) {
          if (!category.haveMaps && category.places) {
            angular.forEach(category.places, function(place) {
              places[place.code] = place;
            });
          }
        });
      }
      return places;
    };
  })

  .filter('colNum', function() {
    return function(colsCount) {
      return Math.floor(12 / colsCount);
    };
  })

  .filter('isActive',['$location', function($location) {
    return function(path) {
      if ($location.path().indexOf(path) != -1) {
        return 'active';
      } else {
        return '';
      }
    };
  }])

  .filter('isFindOnMapType', function() {
    return function(question) {
      return question && question.type < 20;
    };
  })

  .filter('isPickNameOfType', function() {
    return function(question) {
      return question && question.type >= 20;
    };
  })

  .filter('isAllowedOption', function() {
    return function(question, code) {
      return !question.options || 1 == question.options.filter(function(place) {
        return place.code == code;
      }).length;
    };
  })

  .filter('imgSrc', ['domain', function(domain) {
    return function(option) {
      var src = option && option.images && option.images[0] && option.images[0].url;
      return domain ? (src && src.substr(1)) : src;
    };
  }])

  .filter('stripImg', function() {
    return function(option) {
      return option && option.text && option.text.replace(/\!\[Image\]\((.*)\)/, "").replace("<br />", "");
    };
  })

  .filter('stripHtml', function() {
    return function(html) {
      return html.replace(/(<([^>]+)>)/ig,"");
    };
  })

  .filter('isTypeCategory', function() {
    return function(types, category) {
      types = types && types.filter(function(t){
        return category.types.filter(function(slug){
          return slug == t.slug;
        }).length == 1;
      });
      return types;
    };
  })

  .filter('codeToName',['places', function(places) {
    return function(code) {
      return places.getName(code) || "Neznámý";
    };
  }])

  .filter('probColor', ['colorScale', function(colorScale) {
    return function(probability) {
      return colorScale(probability).hex();
    };
  }])

  .filter('sumCounts', [ function() {
    return function(layers) {
      if (!layers || layers.length === 0) {
        return 0;
      }
      var sum = layers.map(function(p){
        return p.count;
      }).reduce(function(a, b) {
        return a + b;
      });
      return sum;
    };
  }])

  .filter('prettify', function () {

    function syntaxHighlight(obj) {
      var json = JSON.stringify(obj, undefined, 4) || "";
      json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
      return json.replace(
        /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, // jshint ignore:line
         function (match) {
        var cls = 'number';
        if (/^"/.test(match)) {
          if (/:$/.test(match)) {
            cls = 'key';
          } else {
            cls = 'string';
          }
        } else if (/true|false/.test(match)) {
          cls = 'boolean';
        } else if (/null/.test(match)) {
          cls = 'null';
        }
        return '<span class="' + cls + '">' + match + '</span>';
      });
    }

    return syntaxHighlight;
  });
}());
