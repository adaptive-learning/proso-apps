describe("User Service", function() {
    var $httpBackend, $userService;
    var test_user = {
        "profile": {
            "send_emails": true,
            "object_type": "user_profile",
            "id": 6,
            "public": false
        },
        "username": "test-user",
        "first_name": "Test",
        "last_name": "Testik",
        "email": "test@proso.cz",
        "id": 10
    };
    var test_user_profile = {
        "send_emails": true,
        "user": {
            "username": "test-user",
            "first_name": "Test",
            "last_name": "Testik",
            "object_type": "user",
            "email": "test@proso.cz",
            "id": 10
        },
        "object_type": "user_profile",
        "id": 6,
        "public": false
    };
    var test_signup_data = {
        username: test_user_profile.user.username,
        email: test_user_profile.user.email,
        password: "heslo",
        password_check: "heslo",
        first_name: test_user_profile.user.first_name,
        last_name: test_user_profile.user.first_name
    };
    var error = { "error_type": "error_type", "error": "error"};

    beforeEach(module('proso_apps.services'));

    beforeEach(inject(function($injector) {
        $httpBackend = $injector.get('$httpBackend');
        $userService = $injector.get('userService');
    }));

    afterEach(function() {
        $httpBackend.verifyNoOutstandingExpectation();
        $httpBackend.verifyNoOutstandingRequest();
    });

    it("provide basic structure", function() {
        expect($userService.user).toBeDefined();
        expect($userService.error).toBeDefined();
        expect($userService.status).toBeDefined();
        expect($userService.status.logged).toBeDefined();
        expect($userService.status.loading).toBeDefined();
    });

    it("logout", function(){
        $httpBackend.expectGET("/user/profile/").respond(200, {data: test_user_profile});
        $httpBackend.expectPOST("/user/session/").respond(200);
        $userService.loadUser();
        $httpBackend.flush();
        expect($userService.user).not.toEqual({});

        $httpBackend.expectGET("/user/logout/").respond(200, "OK");
        $userService.logout();
        expect($userService.status.loading).toBeTruthy();
        $httpBackend.flush();
        expect($userService.status.loading).toBeFalsy();
        expect($userService.status.logged).toBeFalsy();
        expect($userService.user).toEqual({});
    });

    it("sign up", function(){
        $httpBackend.expectPOST("/user/signup/").respond(200, {data: test_user_profile});
        $httpBackend.expectPOST("/user/session/").respond(200);
        $userService.signup(test_signup_data);
        expect($userService.status.loading).toBeTruthy();
        $httpBackend.flush();
        expect($userService.status.loading).toBeFalsy();
        expect($userService.status.logged).toBeTruthy();
        expect($userService.user).toEqual(jasmine.objectContaining(test_user));
        expect($userService.error).toEqual({});
    });

    it("sign up by params", function(){
        $httpBackend.expectPOST("/user/signup/", test_signup_data).respond(200, {data: test_user_profile});
        $httpBackend.expectPOST("/user/session/").respond(200);
        $userService.signupParams(test_signup_data.username, test_signup_data.email, test_signup_data.password,
            test_signup_data.password_check, test_signup_data.first_name, test_signup_data.last_name);
        expect($userService.status.loading).toBeTruthy();
        $httpBackend.flush();
        expect($userService.status.loading).toBeFalsy();
        expect($userService.status.logged).toBeTruthy();
        expect($userService.user).toEqual(jasmine.objectContaining(test_user));
        expect($userService.error).toEqual({});
    });

    it("fail sign up", function(){
        $httpBackend.expectPOST("/user/signup/").respond(400, error);
        $userService.signup(test_signup_data);
        expect($userService.status.loading).toBeTruthy();
        $httpBackend.flush();
        expect($userService.status.loading).toBeFalsy();
        expect($userService.status.logged).toBeFalsy();
        expect($userService.error).toEqual(error);
    });

    it("load user profile", function(){
        $httpBackend.expectGET("/user/profile/").respond(200, {data: test_user_profile});
        $httpBackend.expectPOST("/user/session/").respond(200);
        $userService.loadUser();
        expect($userService.status.loading).toBeTruthy();
        $httpBackend.flush();
        expect($userService.status.loading).toBeFalsy();
        expect($userService.status.logged).toBeTruthy();
        expect($userService.user).toEqual(jasmine.objectContaining(test_user));
    });

    it("fail load user profile", function(){
        $httpBackend.expectGET("/user/profile/").respond(404);
        $userService.loadUser();
        expect($userService.status.loading).toBeTruthy();
        $httpBackend.flush();
        expect($userService.status.loading).toBeFalsy();
        expect($userService.status.logged).toBeFalsy();
        expect($userService.user).toEqual({});
    });

    it("process user", function(){
        $httpBackend.expectPOST("/user/session/").respond(200);
        $userService.processUser(test_user_profile);
        $httpBackend.flush();
        expect($userService.user).toEqual(jasmine.objectContaining(test_user));
        expect($userService.status.logged).toBeTruthy();
    });

    it("process user should not change object", function(){
        var obj = angular.copy(test_user_profile);
        $httpBackend.expectPOST("/user/session/").respond(200);
        $userService.processUser(obj);
        $httpBackend.flush();
        expect(obj).toEqual(test_user_profile);
    });

    it("login", function(){
        $httpBackend.expectPOST("/user/login/", {"username":"login","password":"pass"}).respond(200, {data: test_user_profile});
        $httpBackend.expectPOST("/user/session/").respond(200);
        $userService.login("login", "pass");
        expect($userService.status.loading).toBeTruthy();
        $httpBackend.flush();
        expect($userService.status.loading).toBeFalsy();
        expect($userService.status.logged).toBeTruthy();
        expect($userService.user).toEqual(jasmine.objectContaining(test_user));
        expect($userService.error).toEqual({});
    });

    it("fail login", function(){
        $httpBackend.expectPOST("/user/login/", {"username":"login","password":"pass"}).respond(400, error);
        $userService.login("login", "pass");
        expect($userService.status.loading).toBeTruthy();
        $httpBackend.flush();
        expect($userService.status.loading).toBeFalsy();
        expect($userService.status.logged).toBeFalsy();
        expect($userService.error).toEqual(error);
    });

    it("load session", function(){
        $httpBackend.expectGET("/user/session/").respond(200, {data: "mySession"});
        $userService.loadSession();
        expect($userService.status.loading).toBeTruthy();
        $httpBackend.flush();
        expect($userService.status.loading).toBeFalsy();
        expect($userService.user.session).toBe("mySession");
    });

    it("update profile", function(){
        $httpBackend.expectPOST("/user/profile/", {data: "profile data"}).respond(200, {data: test_user_profile});
        $httpBackend.expectPOST("/user/session/").respond(200);
        $userService.updateProfile({data: "profile data"});
        expect($userService.status.loading).toBeTruthy();
        $httpBackend.flush();
        expect($userService.status.loading).toBeFalsy();
        expect($userService.user).toEqual(jasmine.objectContaining(test_user));
        expect($userService.error).toEqual({});

    });

    it("fail update profile", function(){
        $httpBackend.expectPOST("/user/profile/", {data: "profile data"}).respond(400, error);
        $userService.updateProfile({data: "profile data"});
        expect($userService.status.loading).toBeTruthy();
        $httpBackend.flush();
        expect($userService.status.loading).toBeFalsy();
        expect($userService.error).toEqual(error);

    });

    it("update session", function(){
        $httpBackend.expectPOST("/user/session/").respond(200);
        $userService.updateSession();
        $httpBackend.flush();
        expect(true).toBe(true);
    });

    it("not update session twice", function(){
        $httpBackend.expectGET("/user/profile/").respond(200, {data: test_user_profile});
        $httpBackend.expectPOST("/user/session/").respond(200);
        $userService.loadUser();
        $httpBackend.flush();

        $httpBackend.expectGET("/user/profile/").respond(200, {data: test_user_profile});
        $userService.loadUser();
        $httpBackend.flush();
        expect(true).toBe(true);
    });

    it("not update session when not logged in", function(){
        $httpBackend.expectGET("/user/profile/").respond(404);
        $userService.loadUser();
        $httpBackend.flush();
        expect(true).toBe(true);
    });
});

