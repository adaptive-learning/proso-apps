(function() {
  'use strict';
  /* global chroma  */

  /* Services */
  angular.module('adaptivePractice.services', [
    'ngCookies'
  ])

  .value('chroma', chroma)

  .constant('domain', window.domain || '')

  .value('colors', {
    'GOOD': '#0f9d58',
    'BAD': 'd9534f',
    'NEUTRAL': '#bbb',
    'BRIGHT_GRAY' : '#ddd',
  })

  .factory('colorScale', ['colors', 'chroma', function(colors, chroma) {
    var scale = chroma.scale([
        colors.BAD,
        '#ff4500',
        '#ffa500',
        '#ffff00',
        colors.GOOD
      ]);
    return scale;
  }])


  .factory('questions', ['$http', '$routeParams', 'params', 'domain',
      function($http, $routeParams, params, domain) {
    var that = {
      get : function(category, page) {
        var url = domain + '/questions/questions/';
        var options = {
          params : angular.extend({
            stats : true,
            page : page,
            limit : $routeParams.limit || 20,
          }, params.all())
        };
        if (category) {
          options.params.filter_column = 'category_id';
          options.params.filter_value = category;
        }
        options.params.json_orderby = 'prediction';
        var promise = $http.get(url, options);
        return promise;
      },
      fetchPredicitons : function(questions, predictionPropertyName) {
        predictionPropertyName = predictionPropertyName || 'prediction';
        var predictionsUrl = domain + '/models/model/?items=';
        predictionsUrl += questions.map(function(q) {
          return q.item_id;
        }).join(',');
        var options = {
          params : params.all(),
        };
        $http.get(predictionsUrl, options).success(function(data) {
          for (var i = 0; i < data.data.predictions.length; i++) {
            for (var j = 0; j < questions.length; j++) {
              if (questions[j].item_id == data.data.items[i].item_id ) {
                questions[j][predictionPropertyName] = data.data.items[i].prediction;
              }
            }
          }
        });
      },
    };
    return that;
  }])

  .service('practice', ['$http', '$log', 'user', '$', '$routeParams', 'questions',
        'params', 'domain',
      function($http, $log, user, $, $routeParams, questions, params, domain) {
    var qIndex = 0;
    var url;
    $http.defaults.headers.post['Content-Type'] = 'application/x-www-form-urlencoded';

    function returnQuestion(fn) {
      var q = questionsList[qIndex++];
      if (q)
        q.response_time = -new Date().valueOf();
      fn(q);
    }
    function hasNoTwoSameInARow(array) {
      for (var i = 0, j = array.length; i + 1 < j; i++) {
        if (array[i].id == array[i + 1].id) {
          return false;
        }
      }
      return true;
    }
    var questionsList = [];
    var summary = [];
    var requestOptions = {};
    return {
      test : function(fn) {
        url = domain + '/questions/test';
        var options = {
          params : params.all(),
        };
        var promise = $http.get(url, options).success(function(data) {
          fn(data.data);
          user.initCsfrtoken();
        });
        return promise;
      },
      evaluateTest : function(test, questions) {
        var data = $.param({
          question : questions.map(function(q){return q.id;}),
          answered : questions.map(function(q){return q.answered && q.answered.id;}),
          response_time : questions.map(function(q){return q.response_time;}),
        });
        var url = domain + test.test_evaluate_url + '?hack' + params.queryString();
        var promise = $http({
          method: 'POST',
          url : url,
          data: data,
          headers: {
            'X-CSRFToken' : user.getCsrftoken(),
          }
        });
        return promise;
      },
      first : function(part, fn) {
        requestOptions.params = angular.extend({
          category : part,
          stats : true,
        }, params.all());
        url = domain + '/questions/practice';
        summary = [];
        var promise = $http.get(url, requestOptions).success(function(data) {
          qIndex = 0;
          questionsList = data.data.questions;
          returnQuestion(fn);
          user.initCsfrtoken();
        });
        return promise;
      },
      next : function(part, fn) {
        returnQuestion(fn);
      },
      answer : function(question, category) {
        question.response_time += new Date().valueOf();
        question.index = qIndex - 1;
        var postParams = $.param({
          question : question.id,
          answered : question.answered.id,
          response_time : question.response_time,
        });
        var limit = (requestOptions.params.limit || 10) - question.index - 1;
        summary.push(question);
        $http({
          method: 'POST',
          url : domain + '/questions/practice?stats=true' +
            (category ?  '&category=' + category : '') +
            params.queryString() + '&limit=' + limit,
          data: postParams,
          headers: {
            'Content-Type' : 'application/x-www-form-urlencoded',
            'X-CSRFToken' : user.getCsrftoken(),
          }
        }).success(function(data) {
          var futureLength = qIndex + data.questions.length;
          console.log(futureLength, data);
          // questions array should be always the same size
          // if data sent by server is longer, it means the server is delayed
          if (questionsList.length == futureLength) {
            // try to handle interleaving
            var questionsCandidate = questionsList.slice(0, qIndex).concat(data.questions);
            if (hasNoTwoSameInARow(questionsCandidate)) {
              questionsList = questionsCandidate;
              $log.log('questions updated, question index', qIndex);
            }
          }
        });
        return 100 * qIndex / questionsList.length;
      },
      summary : function() {
        var correctlyAnswered = summary.filter(function(q) {
            return q.answered.correct;
          });
        questions.fetchPredicitons(summary, 'predictionAfter');
        return {
          correctlyAnsweredRatio : correctlyAnswered.length / summary.length,
          questions : summary
        };
      }
    };
  }])

  .factory('user', ['$http', '$cookies', 'events', 'domain',
      function($http, $cookies, events, domain) {
    var user;
    return {
      initUser : function(username, points) {
        user = {
          'username' : username,
          'points' : points
        };
        return user;
      },
      getUser : function() {
        return user;
      },
      logout : function(callback) {
        $http.get(domain + '/user/logout/').success(callback);
        this.initUser('', 0);
        events.emit('userUpdated', user);
        return user;
      },
      addPoint : function() {
        user.points++;
        $cookies.points = user.points;
        events.emit('userUpdated', user);
      },
      getCsrftoken : function() {
        return user.csrftoken || $cookies.csrftoken;
      },
      initCsfrtoken : function() {
        if (!domain || that.getUser().csrftoken) {
          return;
        }
        var url = domain + '/user/initmobile';
        if (localStorage.username && localStorage.password) {
          url += '?username=' + localStorage.username +
            '&password=' + localStorage.password;
        }
        $http.get(url).success(function(data) {
          that.initUser(data.username, 0);
          user.csrftoken = data.csrftoken;
          if (data.password) {
            localStorage.username = data.username;
            localStorage.password = data.password;
          }
        });
      }
    };
  }])

  .factory('events', function() {
    var handlers = {};
    return {
      on : function(eventName, handler) {
        handlers[eventName] = handlers[eventName] || [];
        handlers[eventName].push(handler);
      },
      emit : function(eventName, args) {
        handlers[eventName] = handlers[eventName] || [];
        handlers[eventName].map(function(handler) {
          handler(args);
        });
      }
    };
  })

  .factory('pageTitle',[function() {

    var titles = {
      '' : '',
      '../templates/home/how_it_works.html' : 'Jak to funguje? - ',
      'static/tpl/about.html' : 'O prjektu - ',
      'static/tpl/view_tpl.html' : 'Prohlížení otázek - ',
      'static/tpl/practice_tpl.html' : 'Procvičování otázek - ',
      'static/tpl/test_tpl.html' : 'Test - ',
    };
    return function (route) {
      var title = route.templateUrl ? titles[route.templateUrl] : '';
      return title;
    };
  }])

  .factory('params', ["$routeParams", "$location",
      function ($routeParams, $location) {
    var keys = ['user', 'debug', 'time', 'limit'];
    var params = {};
    var that =  {
      get: function (key) {
        if (params[key] && ! $routeParams[key]) {
          $location.search(key, params[key]);
        }
        if ($routeParams[key]) {
          params[key] = $routeParams[key];
        }
        return params[key];
      },
      all : function() {
        for (var i = 0; i < keys.length; i++) {
          that.get(keys[i]);
        }
        return params;
      },
      queryString : function() {
        that.all();
        var string = keys.map(function(key) {
          return that.get(key) ? '&' + key + '=' + that.get(key) : '';
        }).join('');
        return string;
      }
    };
    return that;
  }]);
}());
