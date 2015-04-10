PracticeService = function($http){
    var self = this;
    self.fc_in_set = 10;
    self.fc_in_queue = 1; // 0 - for load FC when needed. 1 - for 1 waiting FC, QUESTIONS_IN_SET - for load all FC on start
    self.current = 0;

    self.save_answer = function(answer){

    };

    self.get_flashcard = function(answer){

    };

};