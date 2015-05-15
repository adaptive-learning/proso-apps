var config;
var configServiceMock = function(){
    var self = this;
    config = {"proso_flashcards": { "practice": {"test": {
        "set_length": 10,
        "fc_queue_size_max": 1,
        "fc_queue_size_min": 1,
        "save_answer_immediately": false,
        "cache_context": false
    }}}};

    self.getConfig = function(app_name, key, default_value){
        if (config === null){
            console.error("Config not loaded");
            return;
        }

        var variable = config[app_name];
        var path =  key.split(".");
        for (var i=0; i < path.length; i++){
            variable = variable[path[i]];
            if (typeof variable === 'undefined'){ return default_value; }
        }
        return variable;
    };

    self.getOverridden = function () {
        return {};
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

    beforeEach(module('proso_apps.services', "ngCookies"));

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
        $practiceService.initSet("test");
    });

    afterEach(function() {
        $httpBackend.verifyNoOutstandingExpectation();
        $httpBackend.verifyNoOutstandingRequest();
    });


    it("should provide interface", function(){
        expect($practiceService.getCurrent).toBeDefined();
        expect($practiceService.initSet).toBeDefined();
        expect($practiceService.setFilter).toBeDefined();
        expect($practiceService.saveAnswer).toBeDefined();
        expect($practiceService.saveAnswerToCurrentFC).toBeDefined();
        expect($practiceService.flushAnswerQueue).toBeDefined();
        expect($practiceService.getFlashcard).toBeDefined();
        expect($practiceService.getSummary).toBeDefined();
    });

    it("getting first flashcard", function(){

        $practiceService.getFlashcard().then(function(flashcard){
            expect(flashcard).toBe(0);
        });
        $httpBackend.flush();
    });

    it("fc_queue_size_max should change limit of loaded FC", function(){
        $httpBackend.expectGET(new RegExp("\/flashcards\/practice\/?.*limit=2.*"))
                .respond(200, {data: {flashcards: generate_flashcards(2)}});
        $practiceService.getFlashcard();
        $httpBackend.flush();

        config.proso_flashcards.practice.test.fc_queue_size_max = 5;
        $practiceService.initSet("test");
        $httpBackend.expectGET(new RegExp("\/flashcards\/practice\/?.*limit=6.*"))
                .respond(200, {data: {flashcards: generate_flashcards(6)}});
        $practiceService.getFlashcard();
        $httpBackend.flush();

        config.proso_flashcards.practice.test.set_length = config.proso_flashcards.practice.test.fc_queue_size_max = 10;
        $practiceService.initSet("test");
        $httpBackend.expectGET(new RegExp("\/flashcards\/practice\/?.*limit=10.*"))
                .respond(200, {data: {flashcards: generate_flashcards(10)}});
        $practiceService.getFlashcard();
        $httpBackend.flush();

        expect(true).toBe(true);
    });

    it("getting more flashcards", function(){
        var handler = jasmine.createSpy('success');
        config.proso_flashcards.practice.test.fc_queue_size_max = 4;
        config.proso_flashcards.practice.test.set_length = 5;
        $practiceService.initSet("test");

        $practiceService.getFlashcard().then(handler);
        $httpBackend.flush();
        $timeout.flush();
        expect(handler).toHaveBeenCalledWith(0);

        $practiceService.getFlashcard().then(handler);
        $timeout.flush();
        expect(handler).toHaveBeenCalledWith(1);

        $practiceService.getFlashcard().then(handler);
        $timeout.flush();
        expect(handler).toHaveBeenCalledWith(2);

        $practiceService.getFlashcard().then(handler);
        $timeout.flush();
        expect(handler).toHaveBeenCalledWith(3);

        $practiceService.getFlashcard().then(handler);
        $timeout.flush();
        expect(handler).toHaveBeenCalledWith(4);
    });

    it("getting more flashcards when not loaded yet", function(){
        var handler = jasmine.createSpy('success');
        var handler2 = jasmine.createSpy('error');
        $practiceService.fc_queue_size_max = 0;

        $practiceService.getFlashcard().then(handler);
        $practiceService.getFlashcard().then(handler, handler2);
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
        $practiceService.initSet("test");

        $practiceService.getFlashcard().then(handler, handler2);
        $httpBackend.flush();
        $timeout.flush();
        expect(handler).toHaveBeenCalledWith(0);

        $practiceService.getFlashcard().then(handler, handler2);
        $timeout.flush();
        expect(handler).toHaveBeenCalledWith(1);

        $practiceService.getFlashcard().then(handler, handler2);
        $timeout.flush();
        expect(handler).toHaveBeenCalledWith(2);

        expect(handler2).not.toHaveBeenCalled();
        $practiceService.getFlashcard().then(handler, handler2);
        $timeout.flush();
        expect(handler2).toHaveBeenCalled();

    });

    it("current counter", function(){
        config.proso_flashcards.practice.test.set_length = 3;
        config.proso_flashcards.practice.test.fc_queue_size_max = config.proso_flashcards.practice.test.fc_queue_size_min = 1;
        $practiceService.initSet("test");
        expect($practiceService.getCurrent()).toBe(0);
        $practiceService.getFlashcard();
        $httpBackend.flush();
        expect($practiceService.getCurrent()).toBe(1);
        $practiceService.getFlashcard();
        $httpBackend.flush();
        expect($practiceService.getCurrent()).toBe(2);
        $practiceService.getFlashcard();
        expect($practiceService.getCurrent()).toBe(3);
        $practiceService.getFlashcard();
        expect($practiceService.getCurrent()).toBe(3);

    });

    it("should work with empty flashcard list returned from server", function(){
        $httpBackend.expectGET(/\/flashcards\/practice\/?.*/).respond(200, {data: {flashcards: []}});
        $practiceService.getFlashcard();
        $httpBackend.flush();
        expect($practiceService.getCurrent()).toBe(0);
    });

    it("queue length", function() {
        for (var size = 1; size <= 10; size++) {
            config.proso_flashcards.practice.test.fc_queue_size_max = size;
            $practiceService.initSet("test");
            $practiceService.preloadFlashcards();
            $httpBackend.flush();
            expect($practiceService.getFCQueue().length).toBe(size);
        }

    });

    it("use of filter parameters", function(){
        var filter = {};
        filter.types = ["cosi", "kdesi"];
        filter.contexts = [71, 72, 33];
        filter.categories = [15, 16];
        filter.language= "xx";
        $practiceService.setFilter(filter);

        $httpBackend.expectGET(/\/flashcards\/practice\/\?.*categories=%5B15,16%5D.*contexts=%5B71,72,33%5D.*language=xx.*types=%5B%22cosi%22,%22kdesi%22%5D.*/).respond(200, {data: generate_flashcards(1)});
        $practiceService.preloadFlashcards();
        $httpBackend.flush();

        expect($practiceService.getCurrent()).toBe(0);
    });

    it("avoid already loaded flashcards", function(){
        $httpBackend.expectGET(/\/flashcards\/practice\/?.*/).respond(200, {data: {flashcards: [
            {id: 41}, {id: 42},{id: 43}
        ]}});
        config.proso_flashcards.practice.test.fc_queue_size_max = config.proso_flashcards.practice.test.fc_queue_size_min = 3;
        $practiceService.initSet("test");
        $practiceService.preloadFlashcards();
        $httpBackend.flush();

        $httpBackend.expectGET(/\/flashcards\/practice\/?.*41,42,43.*/);
        $practiceService.getFlashcard();
        $timeout.flush();
        $httpBackend.flush();

        expect($practiceService.getCurrent()).toBe(1);
    });

    it("should drop incoming FC after starting new set", function(){
        $practiceService.preloadFlashcards();
        $practiceService.initSet("test");
        $httpBackend.flush();
        expect($practiceService.getFCQueue().length).toBe(0);
    });

    var generate_full_flashcards = function(limit, without_contexts, same_id){
        var flashcards = [];
        for (var i = 1; i <= limit; i++){
            var id = same_id ? 1 : i;
            var fc = {
                "context_id": id
            };
            if (!without_contexts) {
                fc.context = {id: id, content: 42};
            }
            flashcards.push(fc);
        }
        return flashcards;
    };

    it("if cache context - still return question with context", function(){
        config.proso_flashcards.practice.test.cache_context = true;
        $practiceService.initSet("test");
        $httpBackend.expectGET(new RegExp("\/flashcards\/practice\/?.*without_contexts.*"))
                .respond(200, {data: {flashcards: generate_full_flashcards(2, true, true)}});
        $httpBackend.expectGET("/flashcards/context/1").respond({data: {id: 1, content: 42}});

        var fc;
        $practiceService.getFlashcard().then(function(d){fc = d;});
        $httpBackend.flush();
        $timeout.flush();

        expect(fc.context).toBeDefined();
    });

    it("if cache context - context should have correct id", function(){
        config.proso_flashcards.practice.test.cache_context = true;
        $practiceService.initSet("test");
        $httpBackend.expectGET(new RegExp("\/flashcards\/practice\/?.*without_contexts.*"))
            .respond(200, {data: {flashcards: generate_full_flashcards(2, true, true)}});
        $httpBackend.expectGET("/flashcards/context/1").respond({data: {id: 1, content: 42}});

        var fc;
        $practiceService.getFlashcard().then(function(d){fc = d;});
        $httpBackend.flush();
        $timeout.flush();

        expect(fc.context.id).toBe(fc.context_id);
    });

    it("if cache context - should load context separately", function(){
        config.proso_flashcards.practice.test.cache_context = true;
        config.proso_flashcards.practice.test.set_length = 2;
        $practiceService.initSet("test");
        $httpBackend.expectGET(new RegExp("\/flashcards\/practice\/?.*without_contexts.*"))
            .respond(200, {data: {flashcards: generate_full_flashcards(2, true)}});
        $httpBackend.expectGET("/flashcards/context/1").respond({data: {id: 1, content: 42}});
        $httpBackend.expectGET("/flashcards/context/2").respond({data: {id: 2, content: 42}});

        var fc;
        $practiceService.getFlashcard().then(function(d){fc = d;});
        $httpBackend.flush();
        $timeout.flush();
        expect(fc.context.id).toBe(fc.context_id);

        $practiceService.getFlashcard().then(function(d){fc = d;});
        $timeout.flush();
        expect(fc.context.id).toBe(fc.context_id);
    });

    it("if cache context - should load context only once", function(){
        config.proso_flashcards.practice.test.cache_context = true;
        $practiceService.initSet("test");
        $httpBackend.expectGET(new RegExp("\/flashcards\/practice\/?.*without_contexts.*"))
            .respond(200, {data: {flashcards: generate_full_flashcards(10, true, true)}});
        $httpBackend.expectGET("/flashcards/context/1").respond({data: {id: 1, content: 42}});

        var fc, fc2;
        $practiceService.getFlashcard().then(function(d){fc = d;});
        $httpBackend.flush();
        $timeout.flush();
        expect(fc.context.id).toBe(fc.context_id);

        $practiceService.getFlashcard().then(function(d){fc2 = d;});
        $timeout.flush();
        expect(fc.context.id).toBe(fc.context_id);

        expect(fc).not.toBe(fc2);
        expect(fc.context).toBe(fc2.context);
    });

    it("if not cache context - should not load context", function(){
        $practiceService.getFlashcard();
        $httpBackend.flush();
        $timeout.flush();

        expect(true).toBe(true);
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


    beforeEach(module('proso_apps.services', "ngCookies"));
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
        $practiceService.initSet("test");
    });

    afterEach(function() {
        $httpBackend.verifyNoOutstandingExpectation();
        $httpBackend.verifyNoOutstandingRequest();
    });


    it("flush answer queue", function() {
        expect($practiceService.getAnswerQueue()).toEqual([]);
        $practiceService.saveAnswer(1);
        $practiceService.saveAnswer(2);
        $practiceService.saveAnswer(3);
        expect($practiceService.getAnswerQueue()).toEqual([1,2,3]);

        $httpBackend.expectPOST("/flashcards/answer/", {answers: [1,2,3]}).respond(200, "OK");
        $practiceService.flushAnswerQueue();
        $httpBackend.flush();
        expect($practiceService.getAnswerQueue()).toEqual([]);

        $httpBackend.expectPOST("/flashcards/answer/", {answers: [1]}).respond(200, "OK");
        $practiceService.saveAnswer(1, true);
        $httpBackend.flush();
        expect($practiceService.getAnswerQueue()).toEqual([]);
    });


    it("save answer immediately", function() {
        config.proso_flashcards.practice.test.save_answer_immediately = true;
        $practiceService.initSet("test");
        $httpBackend.expectPOST("/flashcards/answer/", {answers: [1]}).respond(200, "OK");
        $practiceService.saveAnswer(1);
        $httpBackend.flush();
        expect($practiceService.getAnswerQueue()).toEqual([]);

        config.proso_flashcards.practice.test.save_answer_immediately = false;
        $practiceService.initSet("test");
        $practiceService.saveAnswer(1);
        expect($practiceService.getAnswerQueue()).toEqual([1]);
    });

    it("save answer with getting FC", function() {
        $httpBackend.expectPOST(/\/flashcards\/practice\/?.*/, {answers: [1, 2, 3]})
            .respond(200, {data: generate_flashcards(1)});
        $practiceService.saveAnswer(1);
        $practiceService.saveAnswer(2);
        $practiceService.saveAnswer(3);
        $practiceService.preloadFlashcards();
        $httpBackend.flush();
        expect($practiceService.getAnswerQueue()).toEqual([]);
    });

    it("save answer at the end of set", function() {
        config.proso_flashcards.practice.test.fc_queue_size_max = config.proso_flashcards.practice.test.set_length = 5;
        $practiceService.initSet("test");
        for (var i = 1; i < 5; i++){
            $practiceService.getFlashcard();
            if (i === 1){
                $httpBackend.flush();
            }
            $timeout.flush();
            $practiceService.saveAnswer(i);
        }
        $httpBackend.expectPOST("/flashcards/answer/", {answers: [1, 2, 3, 4, 5]}).respond(200, "OK");
        $practiceService.getFlashcard();
        $practiceService.saveAnswer(i);
        $httpBackend.flush();

        expect($practiceService.getAnswerQueue()).toEqual([]);
    });

    it("save answer to current flashcard", function() {
        config.proso_flashcards.practice.test.save_answer_immediately = true;
        $practiceService.initSet("test");

        $practiceService.getFlashcard();
        $httpBackend.flush();

        $httpBackend.expectPOST("/flashcards/answer/", {"answers":[{"flashcard_id":0,"flashcard_answered_id":42,"response_time":42000,"direction":"xxxs","meta":"moje meta", time_gap:0}]}).respond(200, "OK");
        $practiceService.saveAnswerToCurrentFC(42, 42000, "moje meta");
        $httpBackend.flush();

        $practiceService.getFlashcard();
        $httpBackend.expectPOST("/flashcards/answer/", {"answers":[{"flashcard_id":1,"flashcard_answered_id":null,"response_time":12,"direction":"xxxs","meta":"moje meta", time_gap:0}]}).respond(200, "OK");
        $practiceService.saveAnswerToCurrentFC(null, 12, "moje meta");
        $httpBackend.flush();

        expect($practiceService.getAnswerQueue()).toEqual([]);
    });

    it("save answer to current flashcard without flashcard", function() {
        config.proso_flashcards.practice.test.save_answer_immediately = true;
        $practiceService.initSet("test");
        $practiceService.saveAnswerToCurrentFC(null, 12, "moje meta");
        expect($practiceService.getAnswerQueue()).toEqual([]);
    });

    it("questions in summary", function() {
        config.proso_flashcards.practice.test.fc_queue_size_max = config.proso_flashcards.practice.test.set_length = 5;
        $practiceService.initSet("test");
        $practiceService.getFlashcard();
        $httpBackend.flush();
        $timeout.flush();
        $practiceService.getFlashcard();
        $timeout.flush();
        $practiceService.getFlashcard();
        $timeout.flush();

        expect($practiceService.getSummary().flashcards).toEqual(generate_flashcards(3));
     });

    it("answers in summary", function() {
        config.proso_flashcards.practice.test.fc_queue_size_max = config.proso_flashcards.practice.test.set_length = 5;
        $practiceService.initSet("test");
        $practiceService.getFlashcard();
        $httpBackend.flush();
        $timeout.flush();
        $practiceService.saveAnswerToCurrentFC(null, 12, "moje meta");

        $practiceService.getFlashcard();
        $timeout.flush();
        $practiceService.saveAnswerToCurrentFC(1, 32, "moje meta");

        $practiceService.getFlashcard();
        $timeout.flush();
        $practiceService.saveAnswer(123);

        var answers = $practiceService.getSummary().answers;
        expect(answers[0].response_time).toBe(12);
        expect(answers[0].flashcard_answered_id).toBe(null);
        expect(answers[1].flashcard_answered_id).toBe(1);
        expect(answers[1].response_time).toBe(32);
        expect(answers[2]).toBe(123);
     });


    it("count in summary", function() {
        config.proso_flashcards.practice.test.fc_queue_size_max = config.proso_flashcards.practice.test.set_length = 5;
        $practiceService.initSet("test");
        expect($practiceService.getSummary().count).toBe(0);
        $practiceService.getFlashcard();
        $httpBackend.flush();
        $timeout.flush();
        $practiceService.saveAnswerToCurrentFC(null, 12, "moje meta");
        $practiceService.getFlashcard();
        $timeout.flush();
        $practiceService.saveAnswerToCurrentFC(null, 12, "moje meta");
        expect($practiceService.getSummary().count).toBe(2);
        $practiceService.getFlashcard();
        expect($practiceService.getSummary().count).toBe(2);
        $timeout.flush();
        $practiceService.saveAnswerToCurrentFC(null, 12, "moje meta");

        expect($practiceService.getSummary().count).toBe(3);
     });

    it("correct in summary", function() {
        config.proso_flashcards.practice.test.fc_queue_size_max = config.proso_flashcards.practice.test.set_length = 5;
        $practiceService.initSet("test");
        expect($practiceService.getSummary().correct).toBe(0);
        $practiceService.getFlashcard();
        $httpBackend.flush();
        $timeout.flush();
        $practiceService.saveAnswerToCurrentFC(null, 12, "moje meta");
        expect($practiceService.getSummary().correct).toBe(0);
        $practiceService.getFlashcard();
        $timeout.flush();
        $practiceService.saveAnswerToCurrentFC(null, 12, "moje meta");
        expect($practiceService.getSummary().correct).toBe(0);
        $practiceService.getFlashcard();
        $timeout.flush();
        $practiceService.saveAnswerToCurrentFC(2, 12, "moje meta");

        expect($practiceService.getSummary().correct).toBe(1);
     });

    it("create good time gaps", function() {
        config.proso_flashcards.practice.test.fc_queue_size_max = config.proso_flashcards.practice.test.set_length = 2;
        $practiceService.initSet("test");

        $practiceService.getFlashcard();
        $httpBackend.flush();

        $practiceService.saveAnswerToCurrentFC(42, 42000, "moje meta");

        $practiceService.getFlashcard();
        var d = Date.now() + 3000;
        var x = spyOn(Date, 'now');
        x.and.callFake(function() { return d; });
        $practiceService.saveAnswerToCurrentFC(null, 12, "moje meta");

        $httpBackend.expectPOST("/flashcards/answer/", {"answers":[
            {"flashcard_id":0,"flashcard_answered_id":42,"response_time":42000,"direction":"xxxs","meta":"moje meta", time_gap:3},
            {"flashcard_id":1,"flashcard_answered_id":null,"response_time":12,"direction":"xxxs","meta":"moje meta", time_gap:0}
        ]}).respond(200, "OK");
        $httpBackend.flush();

        expect($practiceService.getSummary().correct).toBe(0);

    });
});