from datetime import date
from unittest import mock

from _decimal import Decimal
from django.test import TestCase

from books.models import Book
from borrowings.models import Payment, Borrowing
from borrowings.serializers import BorrowingSerializer
from users.models import User


class BorrowingSerializerTests(TestCase):
    def setUp(self):
        self.book = Book.objects.create(
            title="Book 1", inventory=2, dayle_fee=2
        )
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass"
        )
        self.borrowing = Borrowing.objects.create(
            expected_return_date=date(2023, 5, 30),
            book=self.book,
            user=self.user,
        )

    def test_validate_with_pending_payments(self):
        Payment.objects.create(
            borrowing=self.borrowing,
            status=Payment.StatusChoices.PENDING,
            money_to_pay=Decimal("8"),
        )

        serializer = BorrowingSerializer(
            data={}, context={"request": mock.Mock(user=self.user)}
        )
        self.assertFalse(serializer.is_valid())
        self.assertTrue(serializer.errors)

    def test_validate_book_unavailable(self):
        self.book.inventory = 0
        self.book.save()

        serializer = BorrowingSerializer(
            data={"book": self.book.id},
            context={"request": mock.Mock(user=self.user)},
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors["book"][0],
            "Book is not available for borrowing.",
        )

    def test_create_borrowing(self):
        serializer = BorrowingSerializer(
            data={
                "book": self.book.id,
                "expected_return_date": date(2023, 5, 30),
            },
            context={"request": mock.Mock(user=self.user)},
        )
        self.assertTrue(serializer.is_valid())

        with mock.patch(
            "borrowings.serializers.create_stripe_session"
        ) as mock_create_session:
            borrowing = serializer.save()

        self.assertEqual(borrowing.book, self.book)
        self.assertEqual(borrowing.user, self.user)
        self.assertEqual(borrowing.actual_return_date, None)
        self.assertEqual(borrowing.payments.count(), 0)

        mock_create_session.assert_called_once_with(mock.ANY, borrowing)
