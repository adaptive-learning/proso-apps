angular.module('proso_apps.services', [])
.service("practiceService", ["$http", "$q", function($http, $q){
    var self = this;

    // TODO get summary

    var queue = [];
    var deferred_fc = null;
    var promise_resolved_tmp = false;
    var current_fc = null;
    var answer_queue = [];
    
    var config = {};
    var current = 0;

    // called on create and set reset
    self.init = function (){
        config.set_length = 10;
        config.fc_queue_size_max = 1;   // 0 - for load FC when needed. 1 - for 1 waiting FC, QUESTIONS_IN_SET - for load all FC on start
        config.fc_queue_size_min = 1;
        config.save_answer_immediately = false;
        self.set_filter({});
        current = 0;       // number of last provided FC
    };

    self.set_filter = function(filter){
        config.filter = {
            contexts: [],
            categories: [],
            types: [],
            language: "en"
        };
        angular.extend(config.filter, filter);
    };

    self.get_current = function(){
        return current;
    };

    self.get_config = function(){
        return angular.copy(config);
    };

    // add answer to queue and upload queued answers if necessary
    self.save_answer = function(answer, farce_save){
        if (answer)
            answer_queue.push(answer);

        if (config.save_answer_immediately || farce_save || current >= config.set_length) {
            if (answer_queue.length > 0) {
                $http.post("/flashcards/answer/", {answers: answer_queue})
                    .error(function (response) {
                        console.error("Problem while uploading answer", response)
                    });
                answer_queue = [];
            }
        }
    };

    self.flush_answer_queue = function(){
        self.save_answer(null, true)
    };

    // build answer from current FC and save
    self.save_answer_to_current_fc = function(answered_fc_id, response_time, meta){
        if (!current_fc) {
            console.error("There is no current flashcard");
            return;
        }
        var answer = {
            flashcard_id: current_fc.id,
            flashcard_answered_id: answered_fc_id,
            response_time: response_time,
            direction: current_fc.direction
        };
        if (meta)
            answer.meta = meta;
        if (current_fc.options){
            answer.option_ids = [];
            current_fc.options.forEach(function(o){
                if (o.id != current_fc.id)
                    answer.option_ids.push(o.id);
            });
        }
        self.save_answer(answer);
    };

    // return promise of flashcard
    self.get_flashcard = function(){
        if(deferred_fc){
            return $q(function(resolve, reject){
                reject("Already one flashcard promised")
            });
        }
        deferred_fc  = $q.defer();
        promise_resolved_tmp = false;
        _resolve_promise();
        deferred_fc.promise.then(function(){ deferred_fc = null;}, function(){ deferred_fc = null;});
        return deferred_fc.promise;
    };

    self.clear_queue = function(){
        queue = [];
    };

    // preload flashcards
    self.preload_flashcards = function(){
        _load_flashcards();
    };

    self.reset_set = function(){
        // TODO cancel ongoing requests
        self.flush_answer_queue();
        self.clear_queue();
        deferred_fc = null;
        self.init()
    };

    self.get_fc_queue = function(){
        return queue;
    };

    self.get_answer_queue = function(){
        return answer_queue;
    };


    var _load_flashcards = function(){
        if (queue.length >= config.fc_queue_size_min)                                           // if there are some FC queued
            return;
        config.filter.limit  = config.fc_queue_size_max - queue.length;
        if (deferred_fc && !promise_resolved_tmp) config.filter.limit ++;                  // if we promised one flashcard
        config.filter.limit = Math.min(config.filter.limit, config.set_length - current - queue.length);  // check size of set
        if (config.filter.limit == 0) return;                         // nothing to do
        config.filter.avoid = current_fc ? [current_fc.id] : [];      // avoid current FC
        queue.forEach(function(fc){
            config.filter.avoid.push(fc.id);
        });

        var filter = {};
        for (var key in config.filter){
            if (config.filter[key] instanceof Array) {
                filter[key] = JSON.stringify(config.filter[key]);
            }else{
                filter[key] = config.filter[key];
            }
        }

        var request;
        if (answer_queue.length == 0) {
            request = $http.get("/flashcards/practice/", {params: filter});
        }else{
            request = $http.post("/flashcards/practice/", {answers: answer_queue}, {params: filter});
            answer_queue = [];
        }
        request
            .success(function(response){
                queue = queue.concat(response.data.flashcards);
                if (queue.length > 0)
                    _resolve_promise();
                else{
                    console.error("No Flashcards to practice")
                }
            })
            .error(function (response) {
                console.error("Something went wrong while loading flashcards from backend.")
            });

    };

    var _resolve_promise = function(){
        if (deferred_fc == null){
            return;
        }
        if (config.set_length == current){
            deferred_fc.reject("Set was completed");
            return;
        }
        if (queue.length > 0) {
            current_fc = queue.shift();
            current++;
            promise_resolved_tmp = true;
            deferred_fc.resolve(current_fc);
        }
        _load_flashcards();
    };

    self.init();
}]);