try{ var m = angular.module('proso_apps.services'); } catch (err) { m = angular.module('proso_apps.services', []); }
m.service("practiceService", ["$http", "$q", "configService", "$cookies", function($http, $q, configService, $cookies){
    var self = this;

    var queue = [];
    var deferredFC = null;
    var promiseResolvedTmp = false;
    var currentFC = null;
    var answerQueue = [];
    
    var config = {};
    var current = 0;
    var setId = 0;
    var summary = {
        flashcards: [],
        answers: [],
        correct: 0,
        count: 0
    };

    var contexts = {};

    // called on create and set reset
    self.initSet = function(configName){
        var key = "practice." + configName + ".";
        config.set_length = configService.getConfig("proso_flashcards", key + "set_length", 10);
        config.fc_queue_size_max = configService.getConfig("proso_flashcards", key + "fc_queue_size_max", 1);
        config.fc_queue_size_min = configService.getConfig("proso_flashcards", key + "fc_queue_size_min", 1);
        config.save_answer_immediately = configService.getConfig("proso_flashcards", key + "save_answer_immediately", false);
        config.cache_context = configService.getConfig("proso_flashcards", key + "cache_context", false);

        self.setFilter({});
        current = 0;
        self.flushAnswerQueue();
        self.clearQueue();
        deferredFC = null;
        setId++;
    };

    self.setFilter = function(filter){
        config.filter = {
            contexts: [],
            categories: [],
            types: [],
            language: "en"
        };
        angular.extend(config.filter, filter);
    };

    self.getCurrent = function(){
        return current;
    };

    self.getConfig = function(){
        return angular.copy(config);
    };

    // add answer to queue and upload queued answers if necessary
    self.saveAnswer = function(answer, farceSave){
        if (answer) {
            answer.time = Date.now();
            answerQueue.push(answer);
            summary.answers.push(answer);
            summary.count++;
            if (answer.flashcard_id === answer.flashcard_answered_id) {
                summary.correct++;
            }
        }

        if (config.save_answer_immediately || farceSave || current >= config.set_length) {
            if (answerQueue.length > 0) {
                answerQueue.forEach(function(answer){
                    answer.time_gap = Math.round((Date.now() - answer.time) / 1000);
                    delete answer.time;
                });
                $http.defaults.headers.post['X-CSRFToken'] = $cookies.csrftoken;
                $http.post("/flashcards/answer/", {answers: answerQueue})
                    .error(function (response) {
                        console.error("Problem while uploading answer", response);
                    });
                answerQueue = [];
            }
        }
    };

    self.flushAnswerQueue = function(){
        self.saveAnswer(null, true);
    };

    // build answer from current FC and save
    self.saveAnswerToCurrentFC = function(answeredFCId, responseTime, meta){
        if (!currentFC) {
            console.error("There is no current flashcard");
            return;
        }
        var answer = {
            flashcard_id: currentFC.id,
            flashcard_answered_id: answeredFCId,
            response_time: responseTime,
            direction: currentFC.direction
        };
        if (meta) {
            answer.meta = meta;
        }
        if (currentFC.options){
            answer.option_ids = [];
            currentFC.options.forEach(function(o){
                if (o.id !== currentFC.id) {
                    answer.option_ids.push(o.id);
                }
            });
        }
        self.saveAnswer(answer);
    };

    // return promise of flashcard
    self.getFlashcard = function(){
        if(deferredFC){
            return $q(function(resolve, reject){
                reject("Already one flashcard promised");
            });
        }
        deferredFC  = $q.defer();
        promiseResolvedTmp = false;
        _resolvePromise();
        deferredFC.promise.then(function(){ deferredFC = null;}, function(){ deferredFC = null;});
        return deferredFC.promise;
    };

    self.clearQueue = function(){
        queue = [];
    };

    // preload flashcards
    self.preloadFlashcards = function(){
        _loadFlashcards();
    };

    self.getFCQueue = function(){
        return queue;
    };

    self.getAnswerQueue = function(){
        return answerQueue;
    };

    self.getSummary = function(){
        return summary;
    };


    var _loadFlashcards = function(){
        if (queue.length >= config.fc_queue_size_min) { return; }                                       // if there are some FC queued
            config.filter.limit  = config.fc_queue_size_max - queue.length;
        if (deferredFC && !promiseResolvedTmp) { config.filter.limit ++; }                  // if we promised one flashcard
        config.filter.limit = Math.min(config.filter.limit, config.set_length - current - queue.length);  // check size of set
        if (config.filter.limit === 0) {return;}                         // nothing to do
        config.filter.avoid = currentFC ? [currentFC.id] : [];      // avoid current FC
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
        if (answerQueue.length === 0) {
            request = $http.get("/flashcards/practice/", {params: filter});
        }else{
            $http.defaults.headers.post['X-CSRFToken'] = $cookies.csrftoken;
            request = $http.post("/flashcards/practice/", {answers: answerQueue}, {params: filter});
            answerQueue = [];
        }
        var request_in_set = setId;
        request
            .success(function(response){
                if (request_in_set !== setId) {
                    return;
                }
                queue = queue.concat(response.data.flashcards);
                _loadContexts();
                if (queue.length > 0) {
                    _resolvePromise();
                }
                else{
                    console.error("No Flashcards to practice");
                }
            })
            .error(function (response) {
                if (deferredFC !== null){
                    deferredFC.reject("Something went wrong while loading flashcards from backend.");
                }
                console.error("Something went wrong while loading flashcards from backend.");
            });

    };

    var _loadContexts = function(){
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
                            _resolvePromise();
                        }).error(function(){
                            delete contexts[fc.context_id];
                            console.error("Error while loading context from backend");
                        });
                }
            });
        }
    };

    var _resolvePromise = function(){
        if (deferredFC === null){
            return;
        }
        if (config.set_length === current){
            deferredFC.reject("Set was completed");
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
            currentFC = queue.shift();
            current++;
            promiseResolvedTmp = true;
            summary.flashcards.push(currentFC);
            deferredFC.resolve(currentFC);
        }
        _loadFlashcards();
    };
}]);