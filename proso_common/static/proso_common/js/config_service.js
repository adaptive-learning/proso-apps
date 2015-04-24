try{ m = angular.module('proso_apps.services'); } catch (err) { m = angular.module('proso_apps.services', []); }
m.service("configService", ["$http", function($http){
    var self = this;
    var config = null;

    self.get_config = function(app_name, key, default_value){
        if (config === null){
            console.error("Config not loaded");
            return;
        }

        var variable = config[app_name];
        var path =  key.split(".");
        for (var i=0; i < path.length; i++){
            if (typeof variable === 'undefined'){ return default_value;}
            variable = variable[path[i]];
        }
        if (typeof variable === 'undefined'){ return default_value;}
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
}]);