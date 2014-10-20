(function() {
  'use strict';
  /* Controllers */
  angular.module('addaptivePractice.controllers', [])

  .controller('AppCtrl', ['$scope', '$rootScope', 'user', 'pageTitle',
      function($scope, $rootScope, user, pageTitle) {
    $rootScope.topScope = $rootScope;
    
    $rootScope.initTitle = function (title) {
      $rootScope.initialTitle = title;
      $rootScope.title = title;
    };
    
    $rootScope.$on("$routeChangeStart", function(event, next) {
      $rootScope.title = pageTitle(next) + $rootScope.initialTitle;
      $rootScope.isHomepage = !next.templateUrl;
    });
    
    var updateUser = function(data) {
      $rootScope.user = data;
    };
    
    $scope.initUser = function (username, points) {
      $rootScope.user = user.initUser(username, points);
    };

    $rootScope.logout = function() {
      $rootScope.user = user.logout(updateUser);
    };
  }])

  .controller('AppView', ['$scope', '$routeParams', '$filter', 'places',
      function($scope, $routeParams, $filter, places) {
    $scope.category = $routeParams.category;
    $scope.page = 0;
    $scope.questions = [];
    
    $scope.onBottomReached = function() {
      loadQuestions();
    };

    function loadQuestions() {
      if ($scope.loading) {
        return;
      }
      $scope.loading = true;
      places.get($scope.category, $scope.page).
        error(function(){
          $scope.error = "V aplikaci bohužel nastala chyba.";
          $scope.loading = false;
        }).
        success(function(data) {
          var questions = data.data;
          questions = questions.map(function(question) {
            for (var i = 0; i < question.options.length; i++) {
              if (question.options[i].correct) {
                question.correct = question.options[i].order;
              }
            }
            return question;
          });
          $scope.questions = $scope.questions.concat(questions);
          $scope.loading = false;
          $scope.hasMoreQuestions = questions.length > 0;
        });
      $scope.page++;
    }
    loadQuestions();

    $scope.selectQuestion = function(q) {
      $scope.selected = q != $scope.selected ? q : undefined;
    };
    
  }])

  .controller('AppPractice', ['$scope', '$routeParams', '$timeout', '$filter',
      'question', 'user', 'events',
      function($scope, $routeParams, $timeout, $filter,
      question, user, events) {
    $scope.category = $routeParams.category;

    $scope.checkAnswer = function(selected) {
      highlightOptions(selected);
      if (selected) {
        $scope.question.answered = selected;
      }
      $scope.progress = question.answer($scope.question);
      if (selected &&  selected.correct) {
        user.addPoint();
        $timeout(function() {
          $scope.next();
        }, 700);
      } else {
        $scope.canNext = true;
      }
    };

    $scope.next = function() {
      if ($scope.progress < 100) {
        question.next($scope.category, setQuestion);
      } else {
        setupSummary();
      }
    };

    function setupSummary() {
      $scope.layer = undefined;
      // prevents additional points gain. issue #38
      $scope.summary = question.summary();
      $scope.showSummary = true;
      events.emit('questionSetFinished', user.getUser().points);
    }

    function setQuestion(active) {
      $scope.question = active;
      $scope.canNext = false;
    }

    function highlightOptions(selected) {
      $scope.question.options.map(function(o) {
        o.disabled = true;
        o.selected = o == selected;
        return o;
      });
    }

    question.first($scope.category, function(q) {
      setQuestion(q);
    }).error(function(){
      $scope.error = "V aplikaci bohužel nastala chyba.";
    });
  }])

  .controller('AppTest', ['$scope', '$timeout', 'question', '$',
      function($scope, $timeout, question, $) {

    $scope.checkAnswer = function(selected) {
      highlightOptions(selected);
      if (selected) {
        $scope.question.answered = selected;
      }
      $timeout(function() {
        $scope.next();
      }, 700);
    };

    $scope.prev = function() {
      $scope.activeQuestionIndex--;
      if ($scope.activeQuestionIndex < 0) {
        $scope.activeQuestionIndex = $scope.questions.length - 1;
      }
      setQuestion();
    };

    $scope.next = function() {
      $scope.activeQuestionIndex++;
      if ($scope.activeQuestionIndex > $scope.questions.length - 1) {
        $scope.activeQuestionIndex = 0;
      }
      setQuestion();
    };

    $scope.activateQuestion = function(index) {
      $scope.activeQuestionIndex = index;
      setQuestion();
    };

    $scope.evaluate = function(timeRunOut) {
      $scope.activeQuestionIndex = undefined;
      $scope.showSummary = true;
      $scope.questions.map(function(q) {
        q.isCorrect = q.options[q.answered.order] && q.options[q.answered.order].correct;
        q.isWrong = !q.isCorrect;
      });
      $scope.summary = {
        questions : $scope.questions,
        correctlyAnsweredRatio : 0.5,
      };
      if (timeRunOut) {
        $scope.$apply();
      } else {
        $('timer')[0].stop();
      }
    };

    function setQuestion() {
      $scope.question = $scope.questions[$scope.activeQuestionIndex];
    }

    function highlightOptions(selected) {
      $scope.question.options.map(function(o) {
        o.selected = o == selected;
        return o;
      });
    }

    question.test(function(data) {
      $scope.questions = data;
      $scope.activateQuestion(0);
    }).error(function(){
      $scope.error = "V aplikaci bohužel nastala chyba.";
    });
  }])

  .controller('ReloadController', ['$window', function($window){
    $window.location.reload();
  }]);
}());