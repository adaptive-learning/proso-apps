var config;
var configServiceMock = function(){
    var self = this;
    config = {"proso_flashcards": { "practice": {"test": {
        "set_length": 10,
        "fc_queue_size_max": 1,
        "fc_queue_size_min": 1,
        "save_answer_immediately": false
    }}}};

    self.get_config = function(app_name, key, default_value){
        if (config == null){
            console.error("Config not loaded");
            return;
        }

        var variable = config[app_name];
        var path =  key.split(".");
        for (var i=0; i < path.length; i++){
            variable = variable[path[i]];
            if (typeof variable === 'undefined') return default_value;
        }
        return variable;
    };
};

describe("Practice Service - flashcards", function() {
    var $httpBackend, $practiceService, $timeout;

    var generate_flashcards = function(limit){
        var flashcards = [];
        for (var i = 0; i < limit; i++){
            flashcards.push(i);
        }
        return flashcards;
    };

    beforeEach(module('proso_apps.services'));

    beforeEach(module(function ($provide) { $provide.service("configService", configServiceMock); }));

    beforeEach(inject(function($injector) {

        $httpBackend = $injector.get('$httpBackend');
        $timeout = $injector.get("$timeout");
        $practiceService = $injector.get('practiceService');
    }));

    beforeEach(function(){
        for (var limit = 1; limit <=10; limit++){
            $httpBackend.whenGET(new RegExp("\/flashcards\/practice\/?.*limit="+limit+"&.*"))
                .respond(200, {data: {flashcards: generate_flashcards(limit)}});
        }
        $practiceService.init_set("test");
    });

    afterEach(function() {
        $httpBackend.verifyNoOutstandingExpectation();
        $httpBackend.verifyNoOutstandingRequest();
    });


    it("should provide interface", function(){
        expect($practiceService.get_current).toBeDefined();
        expect($practiceService.init_set).toBeDefined();
        expect($practiceService.set_filter).toBeDefined();
        expect($practiceService.save_answer).toBeDefined();
        expect($practiceService.save_answer_to_current_fc).toBeDefined();
        expect($practiceService.flush_answer_queue).toBeDefined();
        expect($practiceService.get_flashcard).toBeDefined();
        expect($practiceService.get_summary).toBeDefined();
    });

    it("getting first flashcard", function(){

        $practiceService.get_flashcard().then(function(flashcard){
            expect(flashcard).toBe(0);
        });
        $httpBackend.flush();
    });

    it("fc_queue_size_max should change limit of loaded FC", function(){
        $httpBackend.expectGET(new RegExp("\/flashcards\/practice\/?.*limit=2.*"))
                .respond(200, {data: {flashcards: generate_flashcards(2)}});
        $practiceService.get_flashcard();
        $httpBackend.flush();

        config.proso_flashcards.practice.test.fc_queue_size_max = 5;
        $practiceService.init_set("test");
        $httpBackend.expectGET(new RegExp("\/flashcards\/practice\/?.*limit=6.*"))
                .respond(200, {data: {flashcards: generate_flashcards(6)}});
        $practiceService.get_flashcard();
        $httpBackend.flush();

        config.proso_flashcards.practice.test.set_length = config.proso_flashcards.practice.test.fc_queue_size_max = 10;
        $practiceService.init_set("test");
        $httpBackend.expectGET(new RegExp("\/flashcards\/practice\/?.*limit=10.*"))
                .respond(200, {data: {flashcards: generate_flashcards(10)}});
        $practiceService.get_flashcard();
        $httpBackend.flush();

        expect(true).toBe(true);
    });

    it("getting more flashcards", function(){
        var handler = jasmine.createSpy('success');
        config.proso_flashcards.practice.test.fc_queue_size_max = 4;
        config.proso_flashcards.practice.test.set_length = 5;
        $practiceService.init_set("test");

        $practiceService.get_flashcard().then(handler);
        $httpBackend.flush();
        $timeout.flush();
        expect(handler).toHaveBeenCalledWith(0);

        $practiceService.get_flashcard().then(handler);
        $timeout.flush();
        expect(handler).toHaveBeenCalledWith(1);

        $practiceService.get_flashcard().then(handler);
        $timeout.flush();
        expect(handler).toHaveBeenCalledWith(2);

        $practiceService.get_flashcard().then(handler);
        $timeout.flush();
        expect(handler).toHaveBeenCalledWith(3);

        $practiceService.get_flashcard().then(handler);
        $timeout.flush();
        expect(handler).toHaveBeenCalledWith(4);
    });

    it("getting more flashcards when not loaded yet", function(){
        var handler = jasmine.createSpy('success');
        var handler2 = jasmine.createSpy('error');
        $practiceService.fc_queue_size_max = 0;

        $practiceService.get_flashcard().then(handler);
        $practiceService.get_flashcard().then(handler, handler2);
        $timeout.flush();
        $httpBackend.flush();
        expect(handler).toHaveBeenCalledWith(0);
        expect(handler2).toHaveBeenCalled();
        expect(handler).not.toHaveBeenCalledWith(1);

    });

    it("reject get more FC than length", function(){
        var handler = jasmine.createSpy('success');
        var handler2 = jasmine.createSpy('error');
        config.proso_flashcards.practice.test.fc_queue_size_max = 10;
        config.proso_flashcards.practice.test.set_length = 3;
        $practiceService.init_set("test");

        $practiceService.get_flashcard().then(handler, handler2);
        $httpBackend.flush();
        $timeout.flush();
        expect(handler).toHaveBeenCalledWith(0);

        $practiceService.get_flashcard().then(handler, handler2);
        $timeout.flush();
        expect(handler).toHaveBeenCalledWith(1);

        $practiceService.get_flashcard().then(handler, handler2);
        $timeout.flush();
        expect(handler).toHaveBeenCalledWith(2);

        expect(handler2).not.toHaveBeenCalled();
        $practiceService.get_flashcard().then(handler, handler2);
        $timeout.flush();
        expect(handler2).toHaveBeenCalled();

    });

    it("current counter", function(){
        config.proso_flashcards.practice.test.set_length = 3;
        config.proso_flashcards.practice.test.fc_queue_size_max = config.proso_flashcards.practice.test.fc_queue_size_min = 1;
        $practiceService.init_set("test");
        expect($practiceService.get_current()).toBe(0);
        $practiceService.get_flashcard();
        $httpBackend.flush();
        expect($practiceService.get_current()).toBe(1);
        $practiceService.get_flashcard();
        $httpBackend.flush();
        expect($practiceService.get_current()).toBe(2);
        $practiceService.get_flashcard();
        expect($practiceService.get_current()).toBe(3);
        $practiceService.get_flashcard();
        expect($practiceService.get_current()).toBe(3);

    });

    it("should work with empty flashcard list returned from server", function(){
        $httpBackend.expectGET(/\/flashcards\/practice\/?.*/).respond(200, {data: {flashcards: []}});
        $practiceService.get_flashcard();
        $httpBackend.flush();
        expect($practiceService.get_current()).toBe(0);
    });

    it("queue length", function() {
        for (var size = 1; size <= 10; size++) {
            config.proso_flashcards.practice.test.fc_queue_size_max = size;
            $practiceService.init_set("test");
            $practiceService.preload_flashcards();
            $httpBackend.flush();
            expect($practiceService.get_fc_queue().length).toBe(size);
        }

    });

    it("use of filter parameters", function(){
        var filter = {};
        filter.types = ["cosi", "kdesi"];
        filter.contexts = [71, 72, 33];
        filter.categories = [15, 16];
        filter.language= "xx";
        $practiceService.set_filter(filter);

        $httpBackend.expectGET(/\/flashcards\/practice\/\?.*categories=%5B15,16%5D.*contexts=%5B71,72,33%5D.*language=xx.*types=%5B%22cosi%22,%22kdesi%22%5D.*/).respond(200, {data: generate_flashcards(1)});
        $practiceService.preload_flashcards();
        $httpBackend.flush();

        expect($practiceService.get_current()).toBe(0);
    });

    it("avoid already loaded flashcards", function(){
        $httpBackend.expectGET(/\/flashcards\/practice\/?.*/).respond(200, {data: {flashcards: [
            {id: 41}, {id: 42},{id: 43}
        ]}});
        config.proso_flashcards.practice.test.fc_queue_size_max = config.proso_flashcards.practice.test.fc_queue_size_min = 3;
        $practiceService.init_set("test");
        $practiceService.preload_flashcards();
        $httpBackend.flush();

        $httpBackend.expectGET(/\/flashcards\/practice\/?.*41,42,43.*/);
        $practiceService.get_flashcard();
        $timeout.flush();
        $httpBackend.flush();

        expect($practiceService.get_current()).toBe(1);
    });

    it("should drop incoming FC after starting new set", function(){
        $practiceService.preload_flashcards();
        $practiceService.init_set("test");
        $httpBackend.flush();
        expect($practiceService.get_fc_queue().length).toBe(0);
    });

    it("", function(){
        $practiceService.preload_flashcards();
        $practiceService.init_set("test");
        $httpBackend.flush();
        expect($practiceService.get_fc_queue().length).toBe(0);
    });
});

describe("Practice Service - answers", function() {
    var $httpBackend, $practiceService, $timeout;

    var generate_flashcards = function(limit){
        var flashcards = [];
        for (var i = 0; i < limit; i++){
            flashcards.push({
                "lang": "en",
                "object_type": "fc_flashcard",
                "direction": "xxxs",
                "item_id": 12,
                "id": i
            });
        }
        return flashcards;
    };


    beforeEach(module('proso_apps.services'));

    beforeEach(module(function ($provide) { $provide.service("configService", configServiceMock); }));

    beforeEach(inject(function($injector) {

        $httpBackend = $injector.get('$httpBackend');
        $timeout = $injector.get("$timeout");
        $practiceService = $injector.get('practiceService');
    }));

    beforeEach(function(){
        for (var limit = 1; limit <=10; limit++){
            $httpBackend.whenGET(new RegExp("\/flashcards\/practice\/?.*limit="+limit+"&.*"))
                .respond(200, {data: {flashcards: generate_flashcards(limit)}});
        }
        $practiceService.init_set("test");
    });

    afterEach(function() {
        $httpBackend.verifyNoOutstandingExpectation();
        $httpBackend.verifyNoOutstandingRequest();
    });


    it("flush answer queue", function() {
        expect($practiceService.get_answer_queue()).toEqual([]);
        $practiceService.save_answer(1);
        $practiceService.save_answer(2);
        $practiceService.save_answer(3);
        expect($practiceService.get_answer_queue()).toEqual([1,2,3]);

        $httpBackend.expectPOST("/flashcards/answer/", {answers: [1,2,3]}).respond(200, "OK");
        $practiceService.flush_answer_queue();
        $httpBackend.flush();
        expect($practiceService.get_answer_queue()).toEqual([]);

        $httpBackend.expectPOST("/flashcards/answer/", {answers: [1]}).respond(200, "OK");
        $practiceService.save_answer(1, true);
        $httpBackend.flush();
        expect($practiceService.get_answer_queue()).toEqual([]);
    });


    it("save answer immediately", function() {
        config.proso_flashcards.practice.test.save_answer_immediately = true;
        $practiceService.init_set("test");
        $httpBackend.expectPOST("/flashcards/answer/", {answers: [1]}).respond(200, "OK");
        $practiceService.save_answer(1);
        $httpBackend.flush();
        expect($practiceService.get_answer_queue()).toEqual([]);

        config.proso_flashcards.practice.test.save_answer_immediately = false;
        $practiceService.init_set("test");
        $practiceService.save_answer(1);
        expect($practiceService.get_answer_queue()).toEqual([1]);
    });

    it("save answer with getting FC", function() {
        $httpBackend.expectPOST(/\/flashcards\/practice\/?.*/, {answers: [1, 2, 3]})
            .respond(200, {data: generate_flashcards(1)});
        $practiceService.save_answer(1);
        $practiceService.save_answer(2);
        $practiceService.save_answer(3);
        $practiceService.preload_flashcards();
        $httpBackend.flush();
        expect($practiceService.get_answer_queue()).toEqual([]);
    });

    it("save answer at the end of set", function() {
        config.proso_flashcards.practice.test.fc_queue_size_max = config.proso_flashcards.practice.test.set_length = 5;
        $practiceService.init_set("test");
        for (var i = 1; i < 5; i++){
            $practiceService.get_flashcard();
            if (i == 1){
                $httpBackend.flush();
            }
            $timeout.flush();
            $practiceService.save_answer(i);
        }
        $httpBackend.expectPOST("/flashcards/answer/", {answers: [1, 2, 3, 4, 5]}).respond(200, "OK");
        $practiceService.get_flashcard();
        $practiceService.save_answer(i);
        $httpBackend.flush();

        expect($practiceService.get_answer_queue()).toEqual([]);
    });

    it("save answer to current flashcard", function() {
        config.proso_flashcards.practice.test.save_answer_immediately = true;
        $practiceService.init_set("test");

        $practiceService.get_flashcard();
        $httpBackend.flush();

        $httpBackend.expectPOST("/flashcards/answer/", {"answers":[{"flashcard_id":0,"flashcard_answered_id":42,"response_time":42000,"direction":"xxxs","meta":"moje meta"}]}).respond(200, "OK");
        $practiceService.save_answer_to_current_fc(42, 42000, "moje meta");
        $httpBackend.flush();

        $practiceService.get_flashcard();
        $httpBackend.expectPOST("/flashcards/answer/", {"answers":[{"flashcard_id":1,"flashcard_answered_id":null,"response_time":12,"direction":"xxxs","meta":"moje meta"}]}).respond(200, "OK");
        $practiceService.save_answer_to_current_fc(null, 12, "moje meta");
        $httpBackend.flush();

        expect($practiceService.get_answer_queue()).toEqual([]);
    });

    it("save answer to current flashcard without flashcard", function() {
        config.proso_flashcards.practice.test.save_answer_immediately = true;
        $practiceService.init_set("test");
        $practiceService.save_answer_to_current_fc(null, 12, "moje meta");
        expect($practiceService.get_answer_queue()).toEqual([]);
    });

    it("questions in summary", function() {
        config.proso_flashcards.practice.test.fc_queue_size_max = config.proso_flashcards.practice.test.set_length = 5;
        $practiceService.init_set("test");
        $practiceService.get_flashcard();
        $httpBackend.flush();
        $timeout.flush();
        $practiceService.get_flashcard();
        $timeout.flush();
        $practiceService.get_flashcard();
        $timeout.flush();

        expect($practiceService.get_summary().flashcards).toEqual(generate_flashcards(3));
     });

    it("answers in summary", function() {
        config.proso_flashcards.practice.test.fc_queue_size_max = config.proso_flashcards.practice.test.set_length = 5;
        $practiceService.init_set("test");
        $practiceService.get_flashcard();
        $httpBackend.flush();
        $timeout.flush();
        $practiceService.save_answer_to_current_fc(null, 12, "moje meta");

        $practiceService.get_flashcard();
        $timeout.flush();
        $practiceService.save_answer_to_current_fc(1, 32, "moje meta");

        $practiceService.get_flashcard();
        $timeout.flush();
        $practiceService.save_answer(123);

        var answers = $practiceService.get_summary().answers;
        expect(answers[0].response_time).toBe(12);
        expect(answers[0].flashcard_answered_id).toBe(null);
        expect(answers[1].flashcard_answered_id).toBe(1);
        expect(answers[1].response_time).toBe(32);
        expect(answers[2]).toBe(123);
     });


    it("count in summary", function() {
        config.proso_flashcards.practice.test.fc_queue_size_max = config.proso_flashcards.practice.test.set_length = 5;
        $practiceService.init_set("test");
        expect($practiceService.get_summary().count).toBe(0);
        $practiceService.get_flashcard();
        $httpBackend.flush();
        $timeout.flush();
        $practiceService.save_answer_to_current_fc(null, 12, "moje meta");
        $practiceService.get_flashcard();
        $timeout.flush();
        $practiceService.save_answer_to_current_fc(null, 12, "moje meta");
        expect($practiceService.get_summary().count).toBe(2);
        $practiceService.get_flashcard();
        expect($practiceService.get_summary().count).toBe(2);
        $timeout.flush();
        $practiceService.save_answer_to_current_fc(null, 12, "moje meta");

        expect($practiceService.get_summary().count).toBe(3);
     });

    it("correct in summary", function() {
        config.proso_flashcards.practice.test.fc_queue_size_max = config.proso_flashcards.practice.test.set_length = 5;
        $practiceService.init_set("test");
        expect($practiceService.get_summary().correct).toBe(0);
        $practiceService.get_flashcard();
        $httpBackend.flush();
        $timeout.flush();
        $practiceService.save_answer_to_current_fc(null, 12, "moje meta");
        expect($practiceService.get_summary().correct).toBe(0);
        $practiceService.get_flashcard();
        $timeout.flush();
        $practiceService.save_answer_to_current_fc(null, 12, "moje meta");
        expect($practiceService.get_summary().correct).toBe(0);
        $practiceService.get_flashcard();
        $timeout.flush();
        $practiceService.save_answer_to_current_fc(2, 12, "moje meta");

        expect($practiceService.get_summary().correct).toBe(1);
     });

});