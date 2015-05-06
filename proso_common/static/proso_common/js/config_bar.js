try{ m = angular.module('proso_apps.directives'); } catch (err) { m = angular.module('proso_apps.directives', []); }
m.directive('configBar', function() {
    return {
        restrict: "E",
        scope: {
        },
        // TODO handle template better
        templateUrl: "/static/proso_common/js/config_bar.html",
        controller: function($scope, configService) {
            $scope.override = configService.override;
            $scope.removeOverridden = configService.removeOverridden;
        }
    };
});