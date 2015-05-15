var config = {
    A: {
        a: 10,
        b: {
            c: {
                d: 42
            },
            e: 11
        },
        f: 53
    },
    B: {
    }
};

describe("Config Service", function() {
    var $httpBackend, $configService;

    beforeEach(module('proso_apps.services', "ngCookies"));

    beforeEach(inject(function($injector) {
        $httpBackend = $injector.get('$httpBackend');
        $configService = $injector.get('configService');
    }));

    beforeEach(inject(function($window){
        $window.configService = null;
    }));

    afterEach(function() {
        $httpBackend.verifyNoOutstandingExpectation();
        $httpBackend.verifyNoOutstandingRequest();
    });


    it("should provide interface", function(){
        expect($configService.getConfig).toBeDefined();
        expect($configService.processConfig).toBeDefined();
        expect($configService.loadConfig).toBeDefined();
    });

    it("should use processed config", function(){
        $configService.processConfig(config);
        expect($configService.getConfig("A", "b")).toEqual(config.A.b);
    });

    it("should copy processed config", function(){
        $configService.processConfig(config);
        expect($configService.getConfig("A", "b")).not.toBe(config.A.b);
    });

    it("should access nested vars", function(){
        $configService.processConfig(config);
        expect($configService.getConfig("A", "a")).toEqual(10);
        expect($configService.getConfig("A", "f")).toEqual(53);
        expect($configService.getConfig("A", "b.e")).toEqual(11);
        expect($configService.getConfig("A", "b.c.d")).toEqual(42);
    });

    it("should return unknown for vars not in config", function(){
        $configService.processConfig(config);
        expect($configService.getConfig("A", "x")).not.toBeDefined();
        expect($configService.getConfig("A", "x.y")).not.toBeDefined();
        expect($configService.getConfig("A", "b.c.e")).not.toBeDefined();
        expect($configService.getConfig("A", "")).not.toBeDefined();
        expect($configService.getConfig("C", "a")).not.toBeDefined();
    });

    it("should return default value for vars not in config", function(){
        $configService.processConfig(config);
        expect($configService.getConfig("A", "x", 61)).toBe(61);
        expect($configService.getConfig("A", "x.y", 62)).toBe(62);
        expect($configService.getConfig("A", "b.c.e", 63)).toBe(63);
        expect($configService.getConfig("A", "", 64)).toBe(64);
        expect($configService.getConfig("C", "a", 65)).toBe(65);
    });

    it("should load config", function() {
        $httpBackend.expectGET("/common/config/").respond({data: config});
        $configService.loadConfig();
        $httpBackend.flush();

        expect($configService.getConfig("A", "b")).toEqual(config.A.b);
    });

    it("should load config and return promise", function() {
        var handler = jasmine.createSpy('success');
        $httpBackend.expectGET("/common/config/").respond({data: config});
        $configService.loadConfig().then(handler);
        expect(handler).not.toHaveBeenCalled();
        $httpBackend.flush();
        expect(handler).toHaveBeenCalled();
    });
});