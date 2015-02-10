(function() {
  'use strict';
  /* Directives */
  angular.module('adaptivePractice.directives', [])
  .directive('email', function() {
    return {
      restrict : 'C',
      compile : function(elem) {
        var emailAddress = elem.html();
        emailAddress = emailAddress.replace('{zavinac}', '@');
        emailAddress = '<a href="mailto:' + emailAddress +
  '">' + emailAddress +
  '</a>';
        elem.html(emailAddress);
      }
    };
  })

  .directive('atooltip', function() {
    return {
      restrict : 'C',
      link : function($scope, elem, attrs) {
        elem.tooltip({
          'placement' : attrs.placement || 'bottom',
          'container' : attrs.container,
        });
      }
    };
  })

  .directive('dropLogin', ['$', function($) {
    return {
      restrict : 'C',
      compile : function(elem) {
        elem.bind('click', function() {
          elem.tooltip('destroy');
          $('.tooltip').each(function() {
            if ($(this).text().indexOf("Přihlašte se") != -1) {
              $(this).remove();
            }
          });
        });
      }
    };
  }])

  .directive('dropLogin',['$timeout', 'events', function($timeout, events) {
    return {
      restrict : 'C',
      link : function($scope, elem) {
        events.on('questionSetFinished', function(points) {
          if (10 < points && points <= 20) {
            $timeout(function() {
              elem.tooltip('show');
            }, 0);
          }
        });
      }
    };
  }])

  .directive('categoryProgress', [function() {
    return {
      restrict : 'C',
      template : '<div class="progress overview-progress">' +
                    '<div class="progress-bar progress-bar-learned" style="' +
                        'width: {{(skills.learned / count)|percent}};">' +
                    '</div>' +
                    '<div class="progress-bar progress-bar-practiced" style="' +
                        'width: {{(skills.practiced / count)|percent}};">' +
                    '</div>' +
                  '</div>',
      link : function($scope, elem, attrs) {
        $scope.count = attrs.count;
        attrs.$observe('skills', function(skills) {
          if(skills !== '') {
            $scope.skills = angular.fromJson(skills);
            elem.tooltip({
              html : true,
              placement: 'bottom',
              title : '<div class="skill-tooltip">' +
                     'Naučeno: ' +
                     '<span class="badge badge-default">' +
                       '<i class="color-indicator learned"></i>' +
                       $scope.skills.learned + ' / ' + $scope.count +
                     '</span>' +
                   '</div>' +
                   '<div class="skill-tooltip">' +
                     'Procvičováno: ' +
                     '<span class="badge badge-default">' +
                       '<i class="color-indicator practiced"></i>' +
                       $scope.skills.practiced + ' / ' + $scope.count +
                     '</span>' +
                   '</div>'
            });
          }
        });
      }
    };
  }])

  .directive('levelProgressBar',['user', '$timeout', function(user, $timeout) {

    function getLevelInfo(points) {
      var levelEnd = 0;
      var levelRange = 30;
      var rangeIncrease = 0;
      for (var i = 1; true; i++) {
        levelEnd += levelRange;
        if (points < levelEnd) {
          return {
            level : i,
            form : levelEnd - levelRange,
            to : levelEnd,
            range : levelRange,
            points : points - (levelEnd - levelRange),
          };
        }
        levelRange += rangeIncrease;
        rangeIncrease += 10;
      }

    }
    return {
      restrict : 'C',
      template : '<span class="badge level-start atooltip" ' +
                   'ng-bind="level.level" title="Aktuální úroveň">' +
                 '</span>' +
                 '<div class="progress level-progress" >' +
                   '<div class="progress-bar progress-bar-warning" ' +
                        'style="width: {{(level.points/level.range)|percent}};">' +
                   '</div>' +
                 '</div>' +
                 '<span class="badge level-goal atooltip" ' +
                       'ng-bind="level.level+1" title="Příští úroveň">' +
                 '</span>',
      link : function($scope, elem) {
        $scope.level = getLevelInfo(user.getUser().points);
        $timeout(function(){
          //console.log(elem, elem.find('.level-progress'));
          elem.find('.level-progress').tooltip({
            placement: 'bottom',
            title : $scope.level.points + ' z ' + $scope.level.range + ' bodů',
          });
        },100);
      }
    };
  }])

  .directive('infiniteScroll', ["$window", "$document", "$",
      function ($window, $document, $) {
    return {
      link:function (scope, element, attrs) {
        var offset = parseInt(attrs.threshold) || 0;
        $document.unbind('scroll');
        $document.bind('scroll', function () {
          if (scope.$eval(attrs.canLoad) &&
              $($window).scrollTop() + $($window).height() >=
              $($document).height() - offset) {
            scope.$apply(attrs.infiniteScroll);
          }
        });
      }
    };
  }])

  .directive('debug', ["params", function (params) {
    return {
      restrict : 'A',
      template : '<pre ng-show="debug" ng-bind-html="debug | prettify"></pre>',
      link:function ($scope, element, attrs) {
        $scope.$watch(attrs.debug, function() {
          $scope.debug = params.get('debug') ? $scope[attrs.debug] : undefined;
        });
      }
    };
  }])

  .directive('loadingIndicator', [function () {
    return {
      restrict : 'C',
      template : '<svg class="spinner" width="65px" height="65px" ' +
                    ' viewBox="0 0 66 66" xmlns="http://www.w3.org/2000/svg">' +
                   '<circle class="path" fill="none" stroke-width="6" ' +
                     'stroke-linecap="round" cx="33" cy="33" r="30"></circle>' +
                 '</svg>'
    };
  }])

  .directive('questionsList', [function () {
    return {
      restrict : 'A',
      templateUrl : 'static/tpl/questions_list_tpl.html',
      scope : false,
      link:function ($scope, element, attrs) {
        $scope.$watch(attrs.questionsList, function(questionsList) {
          $scope.questionsList = questionsList;
        });
        $scope.selectQuestion = function(q) {
          $scope.selected = q != $scope.selected ? q : undefined;
        };
        $scope.showCategories = attrs.showCategories == 'true';
      }
    };
  }])

  .directive('options', [function () {
    return {
      restrict : 'A',
      templateUrl : 'static/tpl/options_tpl.html',
      scope : false,
      link:function ($scope, element, attrs) {
        $scope.$watch(attrs.options, function(question) {
          $scope.question = question;
          $scope.disabled = attrs.ngDisabled;
          $scope.noAnswers = attrs.noAnswers;
        });
      }
    };
  }])

  .directive('dynamicTitle', ['events', function (events) {
    return {
      restrict : 'A',
      template : '{{dynamicTitle}}',
      scope : false,
      link:function ($scope, element, attrs) {
        events.on('titleChaged', function(newTitle) {
          $scope.dynamicTitle = newTitle;
        });
        if (attrs.dynamicTitle) {
          events.emit('titleChaged', attrs.dynamicTitle);
        }
      }
    };
  }]);
}());
