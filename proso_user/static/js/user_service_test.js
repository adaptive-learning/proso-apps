var app = angular.module('proso', []);
app.service("user_service", UserService);


describe("User Service", function() {
    var $httpBackend, $userService;

    beforeEach(module('proso'));

    beforeEach(inject(function($injector) {
        $httpBackend = $injector.get('$httpBackend');

        //authRequestHandler = $httpBackend.wen('GET', '/auth.py')
        //    .respond({userId: 'userX'}, {'A-Token': 'xxx'});

        $userService = $injector.get('user_service');

    }));

    afterEach(function() {
        $httpBackend.verifyNoOutstandingExpectation();
        $httpBackend.verifyNoOutstandingRequest();
    });

    it("should define user", function() {
        expect($userService.user).toBeDefined();
        expect($userService.user.logged).toBeDefined();
        expect($userService.user.loading).toBeDefined();
    });
});

