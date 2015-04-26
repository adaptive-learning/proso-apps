try{ m = angular.module('proso_apps.services'); } catch (err) { m = angular.module('proso_apps.services', []); }
m.service("configService", ["$http", function($http){
    var self = this;
    var config = null;
    var GET;

    self.getConfig = function(appName, key, defaultValue){
        if (GET[appName + "." + key]) {
            variable = GET[appName + "." + key];
            if (GET.debug) { console.log(appName + "." + key, "fake from url", variable); }
            return variable;
        }

        if (config === null){
            console.error("Config not loaded");
            return;
        }

        var variable = config[appName];
        var path =  key.split(".");
        for (var i=0; i < path.length; i++){
            if (typeof variable === 'undefined'){
                if (GET.debug) { console.log(appName + "." + key, "use default", defaultValue); }
                return defaultValue;
            }
            variable = variable[path[i]];
        }
        if (typeof variable === 'undefined'){
            if (GET.debug) { console.log(appName + "." + key, "use default", defaultValue); }
            return defaultValue;}
        if (GET.debug) { console.log(appName + "." + key, "from config", variable); }
        return variable;
    };

    self.loadConfig = function(){
        return $http.get("/common/config/")
            .success(function(response){
                self.processConfig(response.data);
            })
            .error(function(){
                console.error("Problem while loading config from server");
            });
    };

    self.processConfig = function(data){
        config = angular.copy(data);
    };

    var parseGET = function(){
        GET = getUrlVars();
    };

    parseGET();
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
