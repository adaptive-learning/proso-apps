try{ m = angular.module('proso_apps.services'); } catch (err) { m = angular.module('proso_apps.services', []); }
m.service("configService", ["$http", function($http){
    var self = this;
    var config = null;
    var GET;

    self.get_config = function(app_name, key, default_value){
        if (GET[app_name + "." + key]) {
            variable = GET[app_name + "." + key];
            if (GET.debug) { console.log(app_name + "." + key, "fake from url", variable); }
            return variable;
        }

        if (config === null){
            console.error("Config not loaded");
            return;
        }

        var variable = config[app_name];
        var path =  key.split(".");
        for (var i=0; i < path.length; i++){
            if (typeof variable === 'undefined'){
                if (GET.debug) { console.log(app_name + "." + key, "use default", default_value); }
                return default_value;
            }
            variable = variable[path[i]];
        }
        if (typeof variable === 'undefined'){
            if (GET.debug) { console.log(app_name + "." + key, "use default", default_value); }
            return default_value;}
        if (GET.debug) { console.log(app_name + "." + key, "from config", variable); }
        return variable;
    };

    self.load_config = function(){
        return $http.get("/common/config/")
            .success(function(response){
                self.process_config(response.data);
            })
            .error(function(){
                console.error("Problem while loading config from server");
            });
    };

    self.process_config = function(data){
        config = angular.copy(data);
    };

    var parse_GET = function(){
        GET = getUrlVars();
    };

    parse_GET();
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
