var configServiceLoaded;
if (configServiceLoaded){
    throw "ConfigService already loaded";
}
configServiceLoaded = true;
try{ m = angular.module('proso_apps.services'); } catch (err) { m = angular.module('proso_apps.services', []); }

m.factory("configService", ["$http", "$window", "$cookieStore", function($http, $window, $cookieStore){
    if (!!$window.configService){
        return $window.configService;
    }

    var self = this;
    var config = null;

    self.getConfig = function (appName, key, defaultValue) {
        if (typeof overridden[appName + "." + key] !== 'undefined') {
            variable = overridden[appName + "." + key];
            if (self.isDebug()) {
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
                if (self.isDebug()) {
                    console.log(appName + "." + key, "use default", defaultValue);
                }
                return defaultValue;
            }
            variable = variable[path[i]];
        }
        if (typeof variable === 'undefined') {
            if (self.isDebug()) {
                console.log(appName + "." + key, "use default", defaultValue);
            }
            return defaultValue;
        }
        if (self.isDebug()) {
            console.log(appName + "." + key, "from config", variable);
        }
        return variable;
    };

    self.isDebug = function() {
        return overridden.debug === true;
    };

    self.loadConfig = function () {
        return $http.get("/common/config/")
            .success(function (response) {
                self.processConfig(response.data);
                console.log(response);
            })
            .error(function () {
                console.error("Problem while loading config from server");
            });
    };

    self.processConfig = function (data) {
        config = angular.copy(data);
    };

    self.override = function (key, value) {
        if (value === 'true') {
            console.log('bool: true');
            value = true;
        } else if (value === 'false') {
            console.log('bool: false');
            value = false;
        } else if ($.isNumeric(value)) {
            console.log('numeric');
            value = parseFloat(value);
        }
        overridden[key] = value;
        $cookieStore.put("configService:overridden", overridden);
    };

    self.removeOverridden = function (key) {
        delete overridden[key];
        $cookieStore.put("configService:overridden", overridden);
    };

    self.resetOverridden = function () {
        overridden = {};
        $cookieStore.put("configService:overridden", overridden);
    };

    self.getOverridden = function () {
        return angular.copy(overridden);
    };

    var overridden = $cookieStore.get("configService:overridden") || {};
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
