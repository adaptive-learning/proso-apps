var app = angular.module('proso', []);
app.service("user_service", UserService);


describe("User Service", function() {
    var $httpBackend, $userService;
    var empty_user = { "logged": false, "loading": false };
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

    beforeEach(module('proso'));

    beforeEach(inject(function($injector) {
        $httpBackend = $injector.get('$httpBackend');
        $userService = $injector.get('user_service');
    }));

    afterEach(function() {
        $httpBackend.verifyNoOutstandingExpectation();
        $httpBackend.verifyNoOutstandingRequest();
    });

    it("provide user", function() {
        expect($userService.user).toBeDefined();
        expect($userService.user.logged).toBeDefined();
        expect($userService.user.loading).toBeDefined();
    });

    it("logout", function(){
        $httpBackend.expectGET("/user/profile/").respond(200, {data: test_user_profile});
        $httpBackend.expectPOST("/user/session/").respond(200);
        $userService.load_user();
        $httpBackend.flush();
        expect($userService.user).not.toEqual(empty_user);

        $httpBackend.expectGET("/user/logout/").respond(200, "OK");
        $userService.logout();
        expect($userService.user.loading).toBeTruthy();
        $httpBackend.flush();
        expect($userService.user.loading).toBeFalsy();
        expect($userService.user.logged).toBeFalsy();
        expect($userService.user).toEqual(empty_user);
    });

    it("sign up", function(){
        $httpBackend.expectPOST("/user/signup/").respond(200, {data: test_user_profile});
        $httpBackend.expectPOST("/user/session/").respond(200);
        $userService.signup(test_signup_data);
        expect($userService.user.loading).toBeTruthy();
        $httpBackend.flush();
        expect($userService.user.loading).toBeFalsy();
        expect($userService.user.logged).toBeTruthy();
        expect($userService.user).toEqual(jasmine.objectContaining(test_user));
    });

    it("sign up by params", function(){
        $httpBackend.expectPOST("/user/signup/", test_signup_data).respond(200, {data: test_user_profile});
        $httpBackend.expectPOST("/user/session/").respond(200);
        $userService.signup_params(test_signup_data.username, test_signup_data.email, test_signup_data.password,
            test_signup_data.password_check, test_signup_data.first_name, test_signup_data.last_name);
        expect($userService.user.loading).toBeTruthy();
        $httpBackend.flush();
        expect($userService.user.loading).toBeFalsy();
        expect($userService.user.logged).toBeTruthy();
        expect($userService.user).toEqual(jasmine.objectContaining(test_user));
    });

    it("fail sign up", function(){
        $httpBackend.expectPOST("/user/signup/").respond(400, error);
        $userService.signup(test_signup_data);
        expect($userService.user.loading).toBeTruthy();
        $httpBackend.flush();
        expect($userService.user.loading).toBeFalsy();
        expect($userService.user.error).toBe(error.error);
        expect($userService.user.logged).toBeFalsy();
        expect($userService.user.error_type).toBe(error.error_type);
    });

    it("load user profile", function(){
        $httpBackend.expectGET("/user/profile/").respond(200, {data: test_user_profile});
        $httpBackend.expectPOST("/user/session/").respond(200);
        $userService.load_user();
        expect($userService.user.loading).toBeTruthy();
        $httpBackend.flush();
        expect($userService.user.loading).toBeFalsy();
        expect($userService.user.logged).toBeTruthy();
        expect($userService.user).toEqual(jasmine.objectContaining(test_user));
    });

    it("fail load user profile", function(){
        $httpBackend.expectGET("/user/profile/").respond(404);
        $userService.load_user();
        expect($userService.user.loading).toBeTruthy();
        $httpBackend.flush();
        expect($userService.user.loading).toBeFalsy();
        expect($userService.user.logged).toBeFalsy();
        expect($userService.user).toEqual(empty_user);
    });

    it("process user", function(){
        $httpBackend.expectPOST("/user/session/").respond(200);
        $userService.process_user(test_user_profile);
        $httpBackend.flush();
        expect($userService.user).toEqual(jasmine.objectContaining(test_user));
        expect($userService.user.logged).toBeTruthy();
    });

    it("process user should not change object", function(){
        var obj = angular.copy(test_user_profile);
        $httpBackend.expectPOST("/user/session/").respond(200);
        $userService.process_user(obj);
        $httpBackend.flush();
        expect(obj).toEqual(test_user_profile);
    });

    it("login", function(){
        $httpBackend.expectPOST("/user/login/", {"username":"login","password":"pass"}).respond(200, {data: test_user_profile});
        $httpBackend.expectPOST("/user/session/").respond(200);
        $userService.login("login", "pass");
        expect($userService.user.loading).toBeTruthy();
        $httpBackend.flush();
        expect($userService.user.loading).toBeFalsy();
        expect($userService.user.logged).toBeTruthy();
        expect($userService.user).toEqual(jasmine.objectContaining(test_user));
    });

    it("fail login", function(){
        $httpBackend.expectPOST("/user/login/", {"username":"login","password":"pass"}).respond(400, error);
        $userService.login("login", "pass");
        expect($userService.user.loading).toBeTruthy();
        $httpBackend.flush();
        expect($userService.user.loading).toBeFalsy();
        expect($userService.user.logged).toBeFalsy();
        expect($userService.user.error).toBe(error.error);
        expect($userService.user.error_type).toBe(error.error_type);
    });

    it("load session", function(){
        $httpBackend.expectGET("/user/session/").respond(200, {data: "mySession"});
        $userService.load_session();
        expect($userService.user.loading).toBeTruthy();
        $httpBackend.flush();
        expect($userService.user.loading).toBeFalsy();
        expect($userService.user.session).toBe("mySession")
    });

    it("update profile", function(){
        $httpBackend.expectPOST("/user/profile/", {data: "profile data"}).respond(200, {data: test_user_profile});
        $httpBackend.expectPOST("/user/session/").respond(200);
        $userService.update_profile({data: "profile data"});
        expect($userService.user.loading).toBeTruthy();
        $httpBackend.flush();
        expect($userService.user.loading).toBeFalsy();
        expect($userService.user).toEqual(jasmine.objectContaining(test_user));

    });

    it("update session", function(){
        $httpBackend.expectPOST("/user/session/").respond(200);
        $userService.update_session();
        $httpBackend.flush();
        expect(true).toBe(true);
    });

    it("not update session twice", function(){
        $httpBackend.expectGET("/user/profile/").respond(200, {data: test_user_profile});
        $httpBackend.expectPOST("/user/session/").respond(200);
        $userService.load_user();
        $httpBackend.flush();

        $httpBackend.expectGET("/user/profile/").respond(200, {data: test_user_profile});
        $userService.load_user();
        $httpBackend.flush();
        expect(true).toBe(true);
    });

    it("not update session when not logged in", function(){
        $httpBackend.expectGET("/user/profile/").respond(404);
        $userService.load_user();
        $httpBackend.flush();
        expect(true).toBe(true);
    });
});

