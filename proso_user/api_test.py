from proso.django.test import TestCase
import json


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
                "object_type": "user",
                "email": "new_user@domain.com",
                "id": 1,
                "staff": False,
            },
            "object_type": "user_profile",
            "id": 1,
            "public": False
        }
        response = json.loads(response.content)['data']
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
            json.loads(response.content)['data'], expected_profile,
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
            json.loads(response.content)['data'], expected_profile,
            'The updated profile matches.'
        )

    def test_signup_without_email(self):
        response = self.client.post('/user/signup/', json.dumps({
            'username': 'new_user',
            'password': 'some_password',
            'password_check': 'some_password',
        }), content_type='application/json')
        self.assertEqual(response.status_code, 400, 'The user without e-mail can not be registered.')
        self.assertEqual(json.loads(response.content)['error_type'], 'email_empty')

    def test_signup_wrong_password_check(self):
        response = self.client.post('/user/signup/', json.dumps({
            'username': 'new_user',
            'email': 'new_user@domain.com',
            'password': 'some_password',
            'password_check': 'some_password_wrong',
        }), content_type='application/json')
        self.assertEqual(response.status_code, 400, 'The user with wrong password check can not be registered.')
        self.assertEqual(json.loads(response.content)['error_type'], 'password_not_match')

    def test_sesssion(self):
        # check session
        response = self.client.get('/user/session/')
        self.assertEqual(response.status_code, 200, 'There is session available.')
        content = json.loads(response.content)['data']
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
        content = json.loads(response.content)['data']
        for k, v in update.iteritems():
            msg = '"%s" is correct after session is updated.' % k
            if k == 'time_zone':
                self.assertEqual(content[k]['content'], v, msg)
            else:
                self.assertEqual(content[k], v, msg)
