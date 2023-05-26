from unittest.mock import Mock, patch

from django.test import TestCase
from borrowings.notification_service import send_telegram_message


class SendTelegramMessageTests(TestCase):
    @patch("requests.post")
    def test_send_telegram_message(self, mock_post):
        message = "Test message"

        mocked_response = Mock(status_code=200, json={"text": message})
        mock_post.return_value = mocked_response

        response = send_telegram_message(message)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"text": message})
