from datetime import date
from unittest import mock

from decimal import Decimal
from django.test import TestCase, RequestFactory

from books.models import Book
from borrowings.models import Borrowing, Payment
from borrowings.payment_service import create_stripe_session
from users.models import User


class StripeSessionCreationTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.borrowing = Borrowing.objects.create(
            expected_return_date=date(2023, 5, 30),
            book=Book.objects.create(title="Book 1", inventory=2, dayle_fee=2),
            user=User.objects.create_user(
                email="test@example.com", password="testpass"
            ),
        )

    @mock.patch("stripe.checkout.Session.create")
    def test_create_stripe_session(self, mock_session_create):
        mock_session = mock.MagicMock()
        mock_session.url = "https://example.com/session"
        mock_session.id = "session_id"
        mock_session_create.return_value = mock_session

        request = self.factory.get("/some-url/")
        create_stripe_session(request, self.borrowing)

        payment = Payment.objects.get(borrowing=self.borrowing)

        self.assertEqual(payment.session_url, "https://example.com/session")
        self.assertEqual(payment.session_id, "session_id")
        self.assertEqual(payment.money_to_pay, Decimal("8"))
