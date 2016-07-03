from django.contrib.auth.models import User

from proso.django.test import TestCase
import json

from proso_user.models import init_user_profile


class UserAPITest(TestCase):

    def test_anonymous_profile(self):
        response = self.client.get('/user/profile/')
        self.assertEqual(response.status_code, 404, 'There is no profile for anonymous user.')

    def test_signup_and_profile(self):
        # signup
        response = self.client.post('/user/signup/', json.dumps({
            'username': 'new_user',
            'email': 'new_user@domain.com',
            'password': 'some_password',
            'password_check': 'some_password',
        }), content_type='application/json')
        self.assertEqual(response.status_code, 201, 'The user is successfuly created.')
        expected_profile = {
            "send_emails": True,
            "user": {
                "username": "new_user",
                "first_name": "",
                "last_name": "",
                "object_type": "auth_user",
                "email": "new_user@domain.com",
                "id": 1,
                "staff": False,
                "groups": [],
            },
            "properties": {},
            "object_type": "user_profile",
            "id": 1,
            "public": False,
            "owner_of": [],
            "member_of": [],
        }
        response = json.loads(response.content.decode("utf-8"))["data"]
        expected_profile["user"]["id"] = response["user"]["id"]
        expected_profile["id"] = response["id"]
        self.assertEqual(
            response, expected_profile,
            'The given profile has been created.'
        )
        # check profile
        response = self.client.get('/user/profile/')
        self.assertEqual(response.status_code, 200, 'There is a profile for user logged in.')
        self.assertEqual(
            json.loads(response.content.decode("utf-8"))['data'], expected_profile,
            'The profile matches.'
        )
        # update profile
        response = self.client.post('/user/profile/', json.dumps({
            'public': True,
            'user': {
                'first_name': 'Kvido'
            }
        }), content_type='application/json')
        expected_profile['public'] = True
        expected_profile['user']['first_name'] = 'Kvido'
        self.assertEqual(response.status_code, 202, 'The profile can be updated.')
        self.assertEqual(
            json.loads(response.content.decode("utf-8"))["data"], expected_profile,
            'The updated profile matches.'
        )

    def test_signup_without_email(self):
        response = self.client.post('/user/signup/', json.dumps({
            'username': 'new_user',
            'password': 'some_password',
            'password_check': 'some_password',
        }), content_type='application/json')
        self.assertEqual(response.status_code, 400, 'The user without e-mail can not be registered.')
        self.assertEqual(json.loads(response.content.decode("utf-8"))['error_type'], 'email_empty')

    def test_signup_wrong_password_check(self):
        response = self.client.post('/user/signup/', json.dumps({
            'username': 'new_user',
            'email': 'new_user@domain.com',
            'password': 'some_password',
            'password_check': 'some_password_wrong',
        }), content_type='application/json')
        self.assertEqual(response.status_code, 400, 'The user with wrong password check can not be registered.')
        self.assertEqual(json.loads(response.content.decode("utf-8"))['error_type'], 'password_not_match')

    def test_sesssion(self):
        # check session
        response = self.client.get('/user/session/')
        self.assertEqual(response.status_code, 200, 'There is session available.')
        content = json.loads(response.content.decode("utf-8"))['data']
        keys = ['display_height', 'display_width', 'http_user_agent', 'location', 'user_id', 'id', 'object_type']
        for key in keys:
            self.assertTrue(key in content, '"%s" is in the session' % key)
        # update session
        update = {
            'locale': 'cs_CZ',
            'display_width': 666,
            'display_height': 777,
            'time_zone': 'Prague'
        }
        response = self.client.post('/user/session/', json.dumps(update), content_type='application/json')
        self.assertEqual(response.status_code, 202, 'The session can be modified.')
        response = self.client.get('/user/session/')
        self.assertEqual(response.status_code, 200, 'There is session available.')
        content = json.loads(response.content.decode("utf-8"))['data']
        for k, v in update.items():
            msg = '"%s" is correct after session is updated.' % k
            if k == 'time_zone':
                self.assertEqual(content[k]['content'], v, msg)
            else:
                self.assertEqual(content[k], v, msg)

    def test_class(self):
        user = User.objects.create(username='testuser', email='test@test.com', is_staff=True)
        user.set_password('12345')
        user.save()
        init_user_profile(User, user)
        self.client.login(username='testuser', password='12345')

        response = self.client.post('/user/create_class/', json.dumps({
            'name': 'Test',
        }), content_type='application/json')
        self.assertEqual(response.status_code, 201, 'Class can be created.')

        cls = json.loads(self.client.get('/user/classes/',
                                         content_type='application/json').content.decode("utf-8"))['data'][0]
        self.assertEqual(cls['name'], 'Test', 'Class has correct name.')
        self.assertIsNotNone(cls['code'], 'Class has code.')
        self.assertEqual(cls['owner']['user']['id'], user.pk, 'Class has correct owner.')
        self.assertEqual(cls['members'], [], 'Class has no members.')

        result = self.client.post('/user/create_student/', json.dumps({
            'first_name': 'Testik',
            'class': cls['id'],
        }), content_type='application/json')
        self.assertEqual(result.status_code, 403, 'Can not create student if not allowed in config.')

        self.client.post('/user/create_student/?config.proso_user.allow_create_students=true', json.dumps({
            'first_name': 'Testie',
            'class': cls['id'],
        }), content_type='application/json')

        self.assertEqual(response.status_code, 201, 'Student can be created.')
        cls = json.loads(self.client.get('/user/classes/',
                                         content_type='application/json').content.decode("utf-8"))['data'][0]
        self.assertEqual(len(cls['members']), 1, 'Class has new student as member.')

        result = self.client.post('/user/login_student/', json.dumps({
            'student': cls['members'][0]['id'],
        }), content_type='application/json')
        self.assertEqual(result.status_code, 403, 'Can not log in as student if not allowed in config.')

        result = json.loads(self.client.post('/user/login_student/?config.proso_user.allow_login_students=true',
                                             json.dumps({'student': cls['members'][0]['id']}),
                                             content_type='application/json').content.decode("utf-8"))['data']
        self.assertEqual(result['user']['first_name'], 'Testie', 'Can log as student and have correct name')
