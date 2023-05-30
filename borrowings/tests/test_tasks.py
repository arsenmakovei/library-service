from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from books.models import Book
from borrowings.models import Borrowing
from borrowings.tasks import check_overdue_borrowings_task
from users.models import User


class OverdueBorrowingsTaskTests(TestCase):
    def setUp(self):
        self.book = Book.objects.create(
            title="Book 1", inventory=2, dayle_fee=2
        )
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass"
        )

    def test_check_overdue_borrowings_task(self):
        overdue_borrowing = Borrowing.objects.create(
            expected_return_date=timezone.localdate() - timedelta(days=1),
            book=self.book,
            user=self.user,
        )

        with mock.patch(
            "borrowings.tasks.send_telegram_message"
        ) as mock_send_telegram_message:
            check_overdue_borrowings_task()

        expected_message = (
            f"Overdue borrowing:\n"
            f"Borrowing ID: {overdue_borrowing.id}\n"
            f"User: {overdue_borrowing.user.email}\n"
            f"Book: {overdue_borrowing.book.title}"
        )
        mock_send_telegram_message.assert_called_once_with(expected_message)
