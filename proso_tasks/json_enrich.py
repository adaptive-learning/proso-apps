def answer_type(request, json_list, nested):
    for question in json_list:
        if question['payload']['object_type'] == 'task_instance':
            question['answer_class'] = 'task_answer'
