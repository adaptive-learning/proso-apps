import datetime


def get_user_id(request):
    if 'user' in request.GET and request.user.is_staff:
        return int(request.GET['user'])
    else:
        return request.user.id


def get_time(request):
    if 'time' in request.GET and request.user.is_staff:
        time = datetime.datetime.strptime(request.GET['time'], '%Y-%m-%d_%H:%M:%S')
        return time
    else:
        return datetime.datetime.now()
