UserService = function($http){
    var self = this;
    var empty_user = {
        "logged": false,
        "loading": false
    };
    var user = this.user = angular.copy(empty_user);

    self.signup = function(data){
        user.loading = true;
        _reset_error();
        return $http.post("/user/signup/", data)
            .success(function(response){
                self.process_user(response.data);
            })
            .error(function(response){
                user.error = response.error;
                user.error_type = response.error_type;
            })
            .finally(function(response){
                user.loading = false;
            });
    };

    self.signup_params = function(name, email, pass, pass2, first_name, last_name){
        return self.signup({
            "username": name,
            "email": email,
            "password": pass,
            "password_check": pass2,
            "first_name": first_name,
            "last_name": last_name
        });
    };

    // get user profile from backend
    self.load_user = function(){
        user.loading = true;
        return $http.get("/user/profile/")
            .success(function(response){
                self.process_user(response.data);
            })
            .finally(function(response){
                user.loading = false;
            });
    };

    // process user data
    self.process_user = function(data){
        if (data == null) {
            user.logged = false;
            return;
        }
        user.logged = true;
        user.profile = data;
        angular.extend(user, data.user);
        delete user.profile.user;
    };

    self.login = function(name, pass){
        user.loading = true;
        _reset_error();
        return $http.post("/user/login/", {
            username: name,
            password: pass
        })
            .success(function(response){
                self.process_user(response.data);
            })
            .error(function(response){
                user.error = response.error;
                user.error_type = response.error_type;
            })
            .finally(function(response){
                user.loading = false;
            });
    };

    self.logout = function(){
        user.loading = true;
        $http.get("/user/logout/")
            .success(function(response){
                for (var prop in user) if (user.hasOwnProperty(prop)) delete user[prop];
                angular.extend(user, empty_user);
            })
            .finally(function(response){
                user.loading = false;
            });
    };


    var _reset_error = function(){
        user.error = null;
        user.error_type = null;
    };


    self.load_user_fromJS = function (scope) {
        scope.$apply(self.load_user())
    };

    self.load_session = function(){
        user.loading = true;
        $http.get("/user/session/")
            .success(function(response){
                user.session = response.data;
            })
            .finally(function(response){
                user.loading = false;
            });
    };

    self.login_google = function() {
        _open_popup('/login/google-oauth2/', '/user/close_popup')
    };

    self.login_google = function() {
        _open_popup('/login/facebook/', '/user/close_popup')
    };

    var _open_popup = function(url, next){
        var settings = 'height=700,width=7000,left=100,top=100,resizable=yes,scrollbars=yes,toolbar=no,menubar=no,location=yes,directories=no,status=yes';
        url += "?next=" + next;
        window.open(url, "popup", settings)
    };

};