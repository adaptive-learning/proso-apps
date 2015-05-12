try{ m = angular.module('proso_apps.services'); } catch (err) { m = angular.module('proso_apps.services', []); }

m.factory("configService", ["$http", "$window", function($http, $window){
    if (!!$window.configService){
        return $window.configService;
    }

    var self = this;
    var config = null;
    var GET;

    self.getConfig = function (appName, key, defaultValue) {
        if (GET[appName + "." + key]) {
            variable = GET[appName + "." + key];
            if (GET.debug) {
                console.log(appName + "." + key, "fake from url", variable);
            }
            return variable;
        }

        if (overridden[appName + "." + key]) {
            variable = overridden[appName + "." + key];
            if (GET.debug) {
                console.log(appName + "." + key, "overridden", variable);
            }
            return variable;
        }

        if (config === null) {
            console.error("Config not loaded");
            return;
        }

        var variable = config[appName];
        var path = key.split(".");
        for (var i = 0; i < path.length; i++) {
            if (typeof variable === 'undefined') {
                if (GET.debug) {
                    console.log(appName + "." + key, "use default", defaultValue);
                }
                return defaultValue;
            }
            variable = variable[path[i]];
        }
        if (typeof variable === 'undefined') {
            if (GET.debug) {
                console.log(appName + "." + key, "use default", defaultValue);
            }
            return defaultValue;
        }
        if (GET.debug) {
            console.log(appName + "." + key, "from config", variable);
        }
        return variable;
    };

    self.loadConfig = function () {
        return $http.get("/common/config/")
            .success(function (response) {
                self.processConfig(response.data);
            })
            .error(function () {
                console.error("Problem while loading config from server");
            });
    };

    self.processConfig = function (data) {
        config = angular.copy(data);
    };

    // Overriding
    var overridden = {};

    self.override = function (key, value) {
        overridden[key] = value;
        // todo save to cookies
    };

    self.removeOverridden = function (key) {
        delete overridden[key];
    };

    self.resetOverridden = function () {
        overridden = {};
    };

    self.getOverridden = function () {
        return angular.copy(overridden);
    };

    var parseGET = function () {
        GET = getUrlVars();
    };

    parseGET();

    $window.configService = self;
    return self;
}]);

m.config(['$httpProvider', function($httpProvider) {
    var configService;
    $httpProvider.interceptors.push(function($injector){
        return {
            request: function(config){
                configService = configService || $injector.get("configService");
                if (config.url.split("?")[0].match(/\.\w+$/) !== null){
                    return config;
                }
                var overridden = obj2get(configService.getOverridden(), "config.", ["user", "time", "debug"]);
                if (overridden === ""){
                    return config;
                }
                config.url += config.url.indexOf("?") === -1 ? "?" : "&";
                config.url += overridden;
                return config;
            }
        };
    });
}]);


function getUrlVars() {
    var vars = [], hash;
    var hashes = window.location.href.slice(window.location.href.indexOf('?') + 1).split('&');
    for(var i = 0; i < hashes.length; i++) {
        hash = hashes[i].split('=');
        vars.push(hash[0]);
        vars[hash[0]] = hash[1];
    }
    return vars;
}

function obj2get(obj, prefix, ignore_prefix_keys){
    var str = "";
    for (var key in obj) {
        if (obj.hasOwnProperty(key)) {
            if (str !== "") {
                str += "&";
            }
            if (ignore_prefix_keys.indexOf(key) === -1){
                str += prefix;
            }
            str += key + "=" + encodeURIComponent(obj[key]);
        }
    }
    return str;
}
