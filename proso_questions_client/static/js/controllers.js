(function() {
  'use strict';
  /* Controllers */
  angular.module('adaptivePractice.controllers', [])

  .controller('AppCtrl', ['$scope', '$rootScope', 'user', 'pageTitle', '$modal', '$window',
      function($scope, $rootScope, user, pageTitle, $modal, $window) {
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

    $scope.initUser = function (userObj) {
      $rootScope.user = user.initUser(userObj);
    };

    $rootScope.logout = function() {
      $rootScope.user = user.logout(updateUser);
    };

  }])

  .controller('AppView', ['$scope', '$routeParams', '$filter', 'questions',
      function($scope, $routeParams, $filter, questions) {
    $scope.categoryId = $routeParams.category;
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
      questions.get($scope.categoryId, $scope.page).
        error(function(response){
          if (!response || response.status === 0) {
            $scope.error = "Aplikaci chybí připojení k internetu.";
          } else {
            $scope.error = "V aplikaci bohužel nastala chyba.";
          }
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
          if ($scope.categoryId && questions.length > 0) {
            $scope.category = questions[0].categories[0];
          }
        });
      $scope.page++;
    }
    loadQuestions();

  }])

  .controller('AppPractice', ['$scope', '$routeParams', '$timeout', '$filter',
      'practice', 'user', 'events',
      function($scope, $routeParams, $timeout, $filter,
      practice, user, events) {
    $scope.categoryId = $routeParams.category;

    $scope.checkAnswer = function(selected) {
      highlightOptions(selected);
      if (selected) {
        $scope.question.answered = selected;
      }
      $scope.progress = practice.answer($scope.question, $scope.categoryId);
      if (selected && selected.correct) {
        $timeout(function() {
          $scope.next();
        }, 700);
      } else {
        $scope.canNext = true;
      }
      user.addAnswer(selected && selected.correct);
    };

    $scope.next = function() {
      if ($scope.progress < 100) {
        practice.next($scope.categoryId, setQuestion);
      } else {
        setupSummary();
      }
    };

    function setupSummary() {
      $scope.progress = 0;
      $scope.questions = [];
      $scope.summary = practice.summary();
      $scope.showSummary = true;
      events.emit('questionSetFinished', user.getUser().points);
    }

    function setQuestion(active) {
      $scope.question = active;
      $scope.questions = [active];
      $scope.canNext = false;
    }

    function highlightOptions(selected) {
      $scope.question.options.map(function(o) {
        o.disabled = true;
        o.selected = o == selected;
        return o;
      });
    }

    practice.first($scope.categoryId, function(q) {
      setQuestion(q);
    }).error(function(response){
        if (!response || response.status === 0) {
          $scope.error = "Aplikaci chybí připojení k internetu.";
        } else {
          $scope.error = "V aplikaci bohužel nastala chyba.";
        }
    });
  }])

  .controller('AppTest', ['$scope', '$timeout', 'practice', '$',
      function($scope, $timeout, practice, $) {

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
      addResponseTime();
      $scope.activeQuestionIndex = undefined;
      $scope.showSummary = true;
      $scope.loading = true;
      practice.evaluateTest($scope.test, $scope.questions)
      .success(function(data){
        var result = data.data;
        $scope.result = result;
        $scope.result.pointsRatio = result.score_achieved / result.score_max;
        $scope.result.pointsMissingToPass = Math.max(0, result.score_to_pass - result.score_achieved);
        $scope.result.pointsToPassPortion = $scope.result.pointsMissingToPass / result.score_max;
        for (var i = 0; i < data.data.questions.length; i++) {
          for (var j = 0; j < $scope.questions.length; j++) {
            if ($scope.questions[j].id == data.data.questions[i].question_id ) {
              $scope.questions[j].points = data.data.questions[i].score + ' b';
            }
          }
        }
        $scope.loading = false;
      });
      $scope.questions.map(function(q) {
        q.isCorrect = q.answered && q.answered.correct;
        q.isWrong = !q.isCorrect;
        q.prediction = (q.answered ? q.answered.correct : 0) + 0;
        q.points = ' ';
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
      addResponseTime();
      $scope.question = $scope.questions[$scope.activeQuestionIndex];
      $scope.question.start_time = new Date().valueOf();
    }

    function addResponseTime() {
      if ($scope.question) {
        $scope.question.response_time += new Date().valueOf() - $scope.question.start_time;
      }
    }

    function highlightOptions(selected) {
      $scope.question.options.map(function(o) {
        o.selected = o == selected;
        return o;
      });
    }

    $scope.start = function() {
      $scope.started = true;
      practice.test(function(data) {
        $scope.questions = data.questions;
        $scope.questions.map(function(q){
          q.response_time = 0;
        });
        $scope.test = data.test;
        $scope.activateQuestion(0);
    console.log('test scope', $scope);
      }).error(function(response){
        if (!response || response.status === 0) {
          $scope.error = "Aplikaci chybí připojení k internetu.";
        } else {
          $scope.error = "V aplikaci bohužel nastala chyba.";
        }
      });
    };
  }])

  .controller('ReloadController', ['$window', function($window){
    $window.location.reload();
  }]);
}());
