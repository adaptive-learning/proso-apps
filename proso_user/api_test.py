from django.test import TestCase, Client
import json


class UserAPITest(TestCase):

    def setUp(self):
        self.client = Client()
        self.client.get('/user/logout')

    def test_anonymous_profile(self):
        response = self.client.get('/user/profile/')
        self.assertEqual(response.status_code, 404, 'There is no profile for anonymous user.')

    def test_signup_and_profile(self):
        response = self.client.post('/user/signup/', json.dumps({
            'username': 'new_user',
            'email': 'new_user@domain.com',
            'password': 'some_password',
            'password_check': 'some_password',
        }), content_type='application/json')
        self.assertEqual(response.status_code, 200, 'The user is successfuly created.')
        expected_profile = {
            "send_emails": True,
            "user": {
                "username": "new_user",
                "first_name": "",
                "last_name": "",
                "object_type": "user",
                "email": "new_user@domain.com",
                "id": 1
            },
            "object_type": "user_profile",
            "id": 1,
            "public": False
        }
        self.assertEqual(
            json.loads(response.content)['data'], expected_profile,
            'The given profile has been created.'
        )
        response = self.client.get('/user/profile/')
        self.assertEqual(response.status_code, 200, 'There is a profile for user logged in.')
        self.assertEqual(
            json.loads(response.content)['data'], expected_profile,
            'The profile matches.'
        )
        response = self.client.post('/user/profile/', json.dumps({
            'public': True,
            'user': {
                'first_name': 'Kvido'
            }
        }), content_type='application/json')
        expected_profile['public'] = True
        expected_profile['user']['first_name'] = 'Kvido'
        self.assertEqual(response.status_code, 200, 'The profile can be updated.')
        self.assertEqual(
            json.loads(response.content)['data'], expected_profile,
            'The updated profile matches.'
        )
