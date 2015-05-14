from proso.django.test import TestCase
from models import Comment, Rating
import json


class FeedbackAPITest(TestCase):

    def testComment(self):
        # invalid e-mail address
        response = self.client.post('/feedback/feedback/', json.dumps({
            'email': 'aaa',
            'text': 'dummy'
        }), content_type='application/json')
        self.assertEqual(response.status_code, 400, "User can't give a feedback with invalid e-mail address.")
        # empty e-mail address
        response = self.client.post('/feedback/feedback/', json.dumps({
            'text': 'dummy with empty e-mail'
        }), content_type='application/json')
        self.assertEqual(response.status_code, 201, "User can give a feedback with empty e-mail address.")
        self.assertEqual(Comment.objects.all().count(), 1, "The feedback comment from user is saved.")
        # valid e-mail address
        response = self.client.post('/feedback/feedback/', json.dumps({
            'email': 'test@test.com',
            'text': 'dummy with valid e-mail'
        }), content_type='application/json')
        self.assertEqual(response.status_code, 201, "User can give a feedback with valid e-mail address.")
        self.assertEqual(Comment.objects.all().count(), 2, "The feedback comment from user is saved.")

    def testRating(self):
        # invalid value
        response = self.client.post('/feedback/rating/', json.dumps({
            'value': 4
        }), content_type='application/json')
        self.assertEqual(response.status_code, 400, "User can't give a rating with invalid value.")
        # valid value
        response = self.client.post('/feedback/rating/', json.dumps({
            'value': 3
        }), content_type='application/json')
        self.assertEqual(response.status_code, 201, "User can give a rating with invalid value.")
        self.assertEqual(Rating.objects.all().count(), 1, "The rating from user is saved.")
