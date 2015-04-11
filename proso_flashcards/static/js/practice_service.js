PracticeService = function($http, $q){
    var self = this;
    self.fc_in_set = 10;
    self.fc_in_queue = 1;   // 0 - for load FC when needed. 1 - for 1 waiting FC, QUESTIONS_IN_SET - for load all FC on start
    self.current = 0;       // number of last provided FC

    self.filter = {
        contexts: [],
        categories: [],
        types: [],
        language: "en"
    };

    var queue = [];
    var deferred_fc = null;
    var promise_resolved_tmp = false;
    var current_fc = null;


    self.save_answer = function(answer){

    };

    // return promise of flashcard
    self.get_flashcard = function(answer){
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
        _load_flashcards(b);
    };

    self.reset_set = function(){
        self.clear_queue();
        self.current = 0;
        deferred_fc = null;
    };


    var _load_flashcards = function(){
        self.filter.limit  = self.fc_in_queue - queue.length;
        if (deferred_fc && !promise_resolved_tmp) self.filter.limit ++;                  // if we promised one flashcard
        self.filter.limit = Math.min(self.filter.limit, self.fc_in_set - self.current);  // check size of set
        if (self.filter.limit == 0) return;                         // nothing to do
        self.filter.avoid = current_fc ? [current_fc.id] : [];      // avoid current FC
        queue.forEach(function(fc){
            self.filter.avoid.push(fc.id);
        });

        var filter = {};
        for (var key in self.filter){
            if (self.filter[key] instanceof Array) {
                filter[key] = JSON.stringify(self.filter[key]);
            }else{
                filter[key] = self.filter[key];
            }
        }

        $http.get("/flashcards/practice/", {params: filter})
            .success(function(response){
                queue = queue.concat(response.data.flashcards);
                _resolve_promise();
            })
            .error(function (response) {
                console.error("Something went wrong while loading flashcards from backend.")
            });

    };

    var _resolve_promise = function(){
        if (deferred_fc == null){
            return;
        }
        if (self.fc_in_set == self.current){
            deferred_fc.reject("Set was completed");
            return;
        }
        if (queue.length > 0) {
            current_fc = queue.shift();
            self.current++;
            promise_resolved_tmp = true;
            deferred_fc.resolve(current_fc);
        }
        _load_flashcards();
    };
};