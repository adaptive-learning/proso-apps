var app = angular.module('proso', []);
app.service("practice_service", PracticeService);


describe("Practice Service - flashcards", function() {
    var $httpBackend, $practiceService, $timeout;

    var generate_flashcards = function(limit){
        var flashcards = [];
        for (var i = 0; i < limit; i++){
            flashcards.push(i);
        }
        return flashcards;
    };


    beforeEach(module('proso'));

    beforeEach(inject(function($injector) {
        $httpBackend = $injector.get('$httpBackend');
        $timeout = $injector.get("$timeout");
        $practiceService = $injector.get('practice_service');

        for (var limit = 1; limit <=10; limit++){
            $httpBackend.whenGET(new RegExp("\/flashcards\/practice\/?.*limit="+limit+"&.*"))
                .respond(200, {data: {flashcards: generate_flashcards(limit)}});
        }
    }));

    afterEach(function() {
        $httpBackend.verifyNoOutstandingExpectation();
        $httpBackend.verifyNoOutstandingRequest();
    });


    it("should provide interface", function(){
        expect($practiceService.set_lenght).toBeDefined();
        expect($practiceService.fc_queue_size_max).toBeDefined();
        expect($practiceService.fc_queue_size_min).toBeDefined();
        expect($practiceService.current).toBeDefined();
        expect($practiceService.save_answer_immediately).toBeDefined();
        expect($practiceService.filter).toBeDefined();
    });

    it("getting first flashcard", function(){

        $practiceService.get_flashcard().then(function(flashcard){
            expect(flashcard).toBe(0);
        });
        $httpBackend.flush();
    });

    it("fc_queue_size_max should change limit of loaded FC", function(){
        $practiceService.fc_queue_size_max = 1;
        $httpBackend.expectGET(new RegExp("\/flashcards\/practice\/?.*limit=2.*"))
                .respond(200, {data: {flashcards: generate_flashcards(2)}});
        $practiceService.get_flashcard();
        $httpBackend.flush();

        $practiceService.reset_set();

        $practiceService.fc_queue_size_max = 5;
        $httpBackend.expectGET(new RegExp("\/flashcards\/practice\/?.*limit=6.*"))
                .respond(200, {data: {flashcards: generate_flashcards(6)}});
        $practiceService.get_flashcard();
        $httpBackend.flush();

        $practiceService.reset_set();

        $practiceService.set_lenght = $practiceService.fc_queue_size_max = 10;
        $httpBackend.expectGET(new RegExp("\/flashcards\/practice\/?.*limit=10.*"))
                .respond(200, {data: {flashcards: generate_flashcards(10)}});
        $practiceService.get_flashcard();
        $httpBackend.flush();

        expect(true).toBe(true);
    });

    it("getting more flashcards", function(){
        var handler = jasmine.createSpy('success');
        $practiceService.fc_queue_size_max = 4;
        $practiceService.set_lenght = 5;

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
        $practiceService.fc_queue_size_max = 10;
        $practiceService.set_lenght = 3;

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
        $practiceService.set_lenght = 3;
        $practiceService.fc_queue_size_max = $practiceService.fc_queue_size_min = 1;
        expect($practiceService.current).toBe(0);
        $practiceService.get_flashcard();
        $httpBackend.flush();
        expect($practiceService.current).toBe(1);
        $practiceService.get_flashcard();
        $httpBackend.flush();
        expect($practiceService.current).toBe(2);
        $practiceService.get_flashcard();
        expect($practiceService.current).toBe(3);
        $practiceService.get_flashcard();
        expect($practiceService.current).toBe(3);

    });

    it("should work with empty flashcard list returned from server", function(){
        $httpBackend.expectGET(/\/flashcards\/practice\/?.*/).respond(200, {data: {flashcards: []}});
        $practiceService.get_flashcard();
        $httpBackend.flush();
        expect($practiceService.current).toBe(0);
    });

    it("queue length", function() {
        for (var size = 1; size <= 10; size++) {
            $practiceService.fc_queue_size_max = size;
            $practiceService.preload_flashcards();
            $httpBackend.flush();
            expect($practiceService.get_fc_queue().length).toBe(size);
            $practiceService.reset_set();
        }

    });

    it("use of filter parameters", function(){
        $practiceService.filter.types = ["cosi", "kdesi"];
        $practiceService.filter.contexts = [71, 72, 33];
        $practiceService.filter.categories = [15, 16];
        $practiceService.filter.language= "xx";

        $httpBackend.expectGET(/\/flashcards\/practice\/\?.*categories=%5B15,16%5D.*contexts=%5B71,72,33%5D.*language=xx.*types=%5B%22cosi%22,%22kdesi%22%5D.*/).respond(200, {data: generate_flashcards(1)});
        $practiceService.preload_flashcards();
        $httpBackend.flush();

        expect($practiceService.current).toBe(0);
    });

    it("avoid already loaded flashcards", function(){
        $httpBackend.expectGET(/\/flashcards\/practice\/?.*/).respond(200, {data: {flashcards: [
            {id: 41}, {id: 42},{id: 43}
        ]}});
        $practiceService.fc_queue_size_max = $practiceService.fc_queue_size_min = 3;
        $practiceService.preload_flashcards();
        $httpBackend.flush();

        $httpBackend.expectGET(/\/flashcards\/practice\/?.*41,42,43.*/);
        $practiceService.get_flashcard();
        $timeout.flush();
        $httpBackend.flush();

        expect($practiceService.current).toBe(1);
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


    beforeEach(module('proso'));

    beforeEach(inject(function($injector) {
        $httpBackend = $injector.get('$httpBackend');
        $timeout = $injector.get("$timeout");
        $practiceService = $injector.get('practice_service');

        for (var limit = 1; limit <=10; limit++){
            $httpBackend.whenGET(new RegExp("\/flashcards\/practice\/?.*limit="+limit+"&.*"))
                .respond(200, {data: {flashcards: generate_flashcards(limit)}});
        }
    }));

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
        $practiceService.save_answer_immediately = true;
        $httpBackend.expectPOST("/flashcards/answer/", {answers: [1]}).respond(200, "OK");
        $practiceService.save_answer(1);
        $httpBackend.flush();
        expect($practiceService.get_answer_queue()).toEqual([]);

        $practiceService.save_answer_immediately = false;
        $practiceService.save_answer(1);
        expect($practiceService.get_answer_queue()).toEqual([1]);
    });

    it("save answer with getting FC", function() {
        $practiceService.save_answer_immediately = false;
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
        $practiceService.save_answer_immediately = false;
        $practiceService.fc_queue_size_max = $practiceService.set_lenght = 5;
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
        $practiceService.save_answer_immediately = true;

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
        $practiceService.save_answer_immediately = true;
        $practiceService.save_answer_to_current_fc(null, 12, "moje meta");
        expect($practiceService.get_answer_queue()).toEqual([]);
     });
});