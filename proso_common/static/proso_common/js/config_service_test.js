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

    beforeEach(module('proso_apps.services'));

    beforeEach(inject(function($injector) {
        $httpBackend = $injector.get('$httpBackend');
        $configService = $injector.get('configService');
    }));

    beforeEach(function(){
    });

    afterEach(function() {
        $httpBackend.verifyNoOutstandingExpectation();
        $httpBackend.verifyNoOutstandingRequest();
    });


    it("should provide interface", function(){
        expect($configService.get_config).toBeDefined();
        expect($configService.process_config).toBeDefined();
        expect($configService.load_config).toBeDefined();
    });

    it("should use processed config", function(){
        $configService.process_config(config);
        expect($configService.get_config("A", "b")).toEqual(config.A.b);
    });

    it("should copy processed config", function(){
        $configService.process_config(config);
        expect($configService.get_config("A", "b")).not.toBe(config.A.b);
    });

    it("should access nested vars", function(){
        $configService.process_config(config);
        expect($configService.get_config("A", "a")).toEqual(10);
        expect($configService.get_config("A", "f")).toEqual(53);
        expect($configService.get_config("A", "b.e")).toEqual(11);
        expect($configService.get_config("A", "b.c.d")).toEqual(42);
    });

    it("should return unknown for vars not in config", function(){
        $configService.process_config(config);
        expect($configService.get_config("A", "x")).not.toBeDefined();
        expect($configService.get_config("A", "x.y")).not.toBeDefined();
        expect($configService.get_config("A", "b.c.e")).not.toBeDefined();
        expect($configService.get_config("A", "")).not.toBeDefined();
        expect($configService.get_config("C", "a")).not.toBeDefined();
    });

    it("should return default value for vars not in config", function(){
        $configService.process_config(config);
        expect($configService.get_config("A", "x", 61)).toBe(61);
        expect($configService.get_config("A", "x.y", 62)).toBe(62);
        expect($configService.get_config("A", "b.c.e", 63)).toBe(63);
        expect($configService.get_config("A", "", 64)).toBe(64);
        expect($configService.get_config("C", "a", 65)).toBe(65);
    });

    it("should load config", function() {
        $httpBackend.expectGET("/common/config/").respond({data: config});
        $configService.load_config();
        $httpBackend.flush();

        expect($configService.get_config("A", "b")).toEqual(config.A.b);
    });

    it("should load config and return promise", function() {
        var handler = jasmine.createSpy('success');
        $httpBackend.expectGET("/common/config/").respond({data: config});
        $configService.load_config().then(handler);
        expect(handler).not.toHaveBeenCalled();
        $httpBackend.flush();
        expect(handler).toHaveBeenCalled();
    });
});