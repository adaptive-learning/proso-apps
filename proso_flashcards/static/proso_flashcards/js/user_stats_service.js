try{ var m = angular.module('proso_apps.services'); } catch (err) { m = angular.module('proso_apps.services', []); }
m.service("userStatsService", ["$http", "$cookies", function($http, $cookies){
    var self = this;

    var filters = {};

    self.addGroup = function (id, data) {
        if (!data.language){
            delete data.language;
        }
        filters[id] = data;
    };

    self.addGroupParams = function (id, categories, contexts, types, language) {
        filters[id] = {
            categories: categories,
            contexts: types,
            types: types
        };
        if (typeof language !== "undefined"){
            filters[id].language = language;
        }
    };

    self.getStats = function(){
        $http.defaults.headers.post['X-CSRFToken'] = $cookies.csrftoken;
        return $http.get("/flashcards/user_stats/", {params: {filters: JSON.stringify(filters)}});
    };

    self.getStatsPost = function(){
        $http.defaults.headers.post['X-CSRFToken'] = $cookies.csrftoken;
        return $http.post("/flashcards/user_stats/", filters);
    };

    self.clean = function(){
        filters = {};
    };

    self.getGroups = function (){
        return angular.copy(filters);
    };

}]);
