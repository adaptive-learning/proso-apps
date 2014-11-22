import datetime


def is_user_id_overriden(request):
    return 'user' in request.GET and request.user.is_staff


def get_user_id(request):
    if is_user_id_overriden(request):
        return int(request.GET['user'])
    else:
        return request.user.id


def is_time_overriden(request):
    return 'time' in request.GET


def get_time(request):
    if 'time' in request.GET:
        time = datetime.datetime.strptime(request.GET['time'], '%Y-%m-%d_%H:%M:%S')
        return time
    else:
        return datetime.datetime.now()
