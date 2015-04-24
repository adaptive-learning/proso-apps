try{ var m = angular.module('proso_apps.services'); } catch (err) { m = angular.module('proso_apps.services', []); }
m.service("practiceService", ["$http", "$q", "configService", "$cookies", function($http, $q, configService, $cookies){
    var self = this;

    var queue = [];
    var deferred_fc = null;
    var promise_resolved_tmp = false;
    var current_fc = null;
    var answer_queue = [];
    
    var config = {};
    var current = 0;
    var set_id = 0;
    var summary = {
        flashcards: [],
        answers: [],
        correct: 0,
        count: 0
    };

    var contexts = {};

    // called on create and set reset
    self.init_set = function(config_name){
        var key = "practice." + config_name + ".";
        config.set_length = configService.get_config("proso_flashcards", key + "set_length", 10);
        config.fc_queue_size_max = configService.get_config("proso_flashcards", key + "fc_queue_size_max", 1);
        config.fc_queue_size_min = configService.get_config("proso_flashcards", key + "fc_queue_size_min", 1);
        config.save_answer_immediately = configService.get_config("proso_flashcards", key + "save_answer_immediately", false);
        config.cache_context = configService.get_config("proso_flashcards", key + "cache_context", false);

        self.set_filter({});
        current = 0;
        self.flush_answer_queue();
        self.clear_queue();
        deferred_fc = null;
        set_id++;
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
        if (answer) {
            answer.time = Date.now();
            answer_queue.push(answer);
            summary.answers.push(answer);
            summary.count++;
            if (answer.flashcard_id === answer.flashcard_answered_id) {
                summary.correct++;
            }
        }

        if (config.save_answer_immediately || farce_save || current >= config.set_length) {
            if (answer_queue.length > 0) {
                answer_queue.forEach(function(answer){
                    answer.time_gap = Math.round((Date.now() - answer.time) / 1000);
                    delete answer.time;
                });
                $http.defaults.headers.post['X-CSRFToken'] = $cookies.csrftoken;
                $http.post("/flashcards/answer/", {answers: answer_queue})
                    .error(function (response) {
                        console.error("Problem while uploading answer", response);
                    });
                answer_queue = [];
            }
        }
    };

    self.flush_answer_queue = function(){
        self.save_answer(null, true);
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
        if (meta) {
            answer.meta = meta;
        }
        if (current_fc.options){
            answer.option_ids = [];
            current_fc.options.forEach(function(o){
                if (o.id !== current_fc.id) {
                    answer.option_ids.push(o.id);
                }
            });
        }
        self.save_answer(answer);
    };

    // return promise of flashcard
    self.get_flashcard = function(){
        if(deferred_fc){
            return $q(function(resolve, reject){
                reject("Already one flashcard promised");
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

    self.get_fc_queue = function(){
        return queue;
    };

    self.get_answer_queue = function(){
        return answer_queue;
    };

    self.get_summary = function(){
        return summary;
    };


    var _load_flashcards = function(){
        if (queue.length >= config.fc_queue_size_min) { return; }                                       // if there are some FC queued
            config.filter.limit  = config.fc_queue_size_max - queue.length;
        if (deferred_fc && !promise_resolved_tmp) { config.filter.limit ++; }                  // if we promised one flashcard
        config.filter.limit = Math.min(config.filter.limit, config.set_length - current - queue.length);  // check size of set
        if (config.filter.limit === 0) {return;}                         // nothing to do
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
        if (config.cache_context){
            filter.without_contexts = 1;
        }

        var request;
        if (answer_queue.length === 0) {
            request = $http.get("/flashcards/practice/", {params: filter});
        }else{
            $http.defaults.headers.post['X-CSRFToken'] = $cookies.csrftoken;
            request = $http.post("/flashcards/practice/", {answers: answer_queue}, {params: filter});
            answer_queue = [];
        }
        var request_in_set = set_id;
        request
            .success(function(response){
                if (request_in_set !== set_id) {
                    return;
                }
                queue = queue.concat(response.data.flashcards);
                _load_contexts();
                if (queue.length > 0) {
                    _resolve_promise();
                }
                else{
                    console.error("No Flashcards to practice");
                }
            })
            .error(function (response) {
                console.error("Something went wrong while loading flashcards from backend.");
            });

    };

    var _load_contexts = function(){
        if (config.cache_context){
            queue.forEach(function(fc){
                if (fc.context_id in contexts){
                    if (contexts[fc.context_id] !== "loading"){
                        fc.context = contexts[fc.context_id];
                    }
                }else{
                    contexts[fc.context_id] = "loading";
                    $http.get("/flashcards/context/" + fc.context_id)
                        .success(function(response){
                            contexts[fc.context_id] = response.data;
                            _resolve_promise();
                        }).error(function(){
                            delete contexts[fc.context_id];
                            console.error("Error while loading context from backend");
                        });
                }
            });
        }
    };

    var _resolve_promise = function(){
        if (deferred_fc === null){
            return;
        }
        if (config.set_length === current){
            deferred_fc.reject("Set was completed");
            return;
        }
        if (queue.length > 0) {
            if (config.cache_context){
                if (typeof contexts[queue[0].context_id]  === 'object'){
                    queue[0].context = contexts[queue[0].context_id];
                }else{
                    return;
                }
            }
            current_fc = queue.shift();
            current++;
            promise_resolved_tmp = true;
            summary.flashcards.push(current_fc);
            deferred_fc.resolve(current_fc);
        }
        _load_flashcards();
    };
}]);