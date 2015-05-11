try{ m = angular.module('proso_apps.directives'); } catch (err) { m = angular.module('proso_apps.directives', []); }
m.directive('configBar', function() {
    return {
        restrict: "E",
        scope: {
        },
        // TODO handle template better
        templateUrl: "/static/proso_common/js/config_bar.html",
        controller: function($scope, configService, loggingService) {
            $scope.override = configService.override;
            $scope.removeOverridden = configService.removeOverridden;
            $scope.debugLog = [];
            $scope.debug = true;
            $scope.opened = true;
            $scope.loggingOpened = true;
            $scope.override('debug', true);
            loggingService.addDebugLogListener(function(events) {
                events.forEach(function(e) {
                    $scope.debugLog.unshift(e);
                });
            });
        }
    };
});
