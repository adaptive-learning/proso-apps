(function() {
  'use strict';
  /* global jQuery  */
  // Declare app level module which depends on filters, and services
  angular.module('adaptivePractice', [
    'adaptivePractice.controllers',
    'adaptivePractice.directives',
    'adaptivePractice.filters',
    'adaptivePractice.services',
    'angulartics',
    'angulartics.google.analytics',
    'googleExperiments',
    'ngAnimate',
    'ngMaterial',
    'ngRoute',
    'ngSanitize',
    'proso.feedback',
    'proso.user',
    'timer',
    'ui.bootstrap',
  ])

  .value('$', jQuery)

  .config(['$routeProvider', '$locationProvider', 'domain', 'googleExperimentsProvider',
      function($routeProvider, $locationProvider, domain, googleExperimentsProvider) {
    $routeProvider.when('/', {
    }).when('/login/:somepath/', {
      controller : 'ReloadController',
      templateUrl : 'loading.html'
    }).when('/how-it-works', {
      templateUrl : 'how-it-works.html'
    }).when('/about', {
      templateUrl : 'static/tpl/about.html'
    }).when('/view/:category?', {
      controller : 'AppView',
      templateUrl : 'static/tpl/view_tpl.html',
      reloadOnSearch : false,
    }).when('/refreshpractice/:category?', {
      redirectTo : '/practice/:category'
    }).when('/practice/:category?', {
      controller : 'AppPractice',
      templateUrl : 'static/tpl/practice_tpl.html',
      reloadOnSearch : false,
    }).when('/test/', {
      controller : 'AppTest',
      templateUrl : 'static/tpl/test_tpl.html'
    }).when('/refreshtest/', {
      redirectTo : '/test/'
    }).when('/overview/:user?', {
      controller : 'AppOverview',
      templateUrl : 'static/tpl/overview_tpl.html'
    }).otherwise({
      //redirectTo : '/'
    });

    if (!domain) {
      // TODO: this desn't work in latest Angular
      //$locationProvider.html5Mode(true);
    }
      googleExperimentsProvider.configure({
        experimentId: ''
      });
  }])

  .run(['$analytics', function($analytics) {
    $analytics.settings.pageTracking.autoTrackFirstPage = false;
  }]);
}());
