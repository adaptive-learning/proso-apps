angular.module('googleExperiments').provider(
    'googleExperiments', [function googleExperimentsProvider() {
        var variation;
        this.configure = function(conf) {
            this.config = conf;
        };

        this.$get = function($q, $timeout) {
            var variationDeferred = $q.defer();
            // dynamically load external javascript file and wait for it to load
            var s = document.createElement('script');
            $timeout(function() {
                variationDeferred.resolve(cxApi.chooseVariation());
            }, 300, false);

            s.async = false;
            s.src = '//www.google-analytics.com/cx/api.js?experiment=' + this.config.experimentId;
            angular.element('body').append(s);

            return {
                getVariation: function() {
                    return variationDeferred.promise;
                }
            };
        };
    }]
);
