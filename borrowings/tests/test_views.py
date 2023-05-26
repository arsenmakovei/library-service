from datetime import date
from unittest import mock

from decimal import Decimal
from django.test import TestCase, RequestFactory
from django.urls import reverse
from rest_framework import status
from rest_framework.test import force_authenticate

from books.models import Book
from borrowings.models import Borrowing, Payment
from borrowings.views import BorrowingViewSet, PaymentViewSet
from users.models import User


class BorrowingViewSetTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass"
        )
        self.borrowing = Borrowing.objects.create(
            expected_return_date=date(2023, 5, 30),
            book=Book.objects.create(title="Book 1", inventory=2, dayle_fee=2),
            user=self.user,
        )
        self.url = reverse("borrowings:borrowing-list")

    def test_list_borrowings(self):
        request = self.factory.get(self.url)
        force_authenticate(request, user=self.user)

        view = BorrowingViewSet.as_view({"get": "list"})
        response = view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.borrowing.id)

    def test_create_borrowing(self):
        book = Book.objects.create(title="Book 2", inventory=2, dayle_fee=2)
        data = {"book": book.id, "expected_return_date": "2023-06-30"}

        request = self.factory.post(self.url, data)
        force_authenticate(request, user=self.user)

        view = BorrowingViewSet.as_view({"post": "create"})
        response = view(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Borrowing.objects.count(), 2)

    def test_return_borrowing(self):
        borrowing = Borrowing.objects.create(
            expected_return_date=date(2023, 5, 25),
            book=Book.objects.create(title="Book 3", inventory=2, dayle_fee=2),
            user=self.user,
        )
        url = reverse(
            "borrowings:borrowing-book-return", kwargs={"pk": borrowing.id}
        )

        request = self.factory.post(url)
        force_authenticate(request, user=self.user)

        view = BorrowingViewSet.as_view({"post": "book_return"})
        response = view(request, pk=borrowing.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(
            Borrowing.objects.get(pk=borrowing.id).actual_return_date
        )
        self.assertEqual(Book.objects.get(pk=borrowing.book.id).inventory, 3)
        self.assertEqual(Payment.objects.count(), 1)

    def test_return_already_returned_borrowing(self):
        borrowing = Borrowing.objects.create(
            expected_return_date=date(2023, 5, 25),
            actual_return_date=date(2023, 5, 24),
            book=Book.objects.create(title="Book 4", inventory=2, dayle_fee=2),
            user=self.user,
        )
        url = reverse(
            "borrowings:borrowing-book-return", kwargs={"pk": borrowing.id}
        )

        request = self.factory.post(url)
        force_authenticate(request, user=self.user)

        view = BorrowingViewSet.as_view({"post": "book_return"})
        response = view(request, pk=borrowing.id)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["error"], "Book has already been returned"
        )


class PaymentViewSetTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass"
        )
        self.payment = Payment.objects.create(
            status=Payment.StatusChoices.PENDING,
            type=Payment.TypeChoices.FINE,
            borrowing=Borrowing.objects.create(
                expected_return_date=date(2023, 5, 30),
                book=Book.objects.create(
                    title="Book 1", inventory=2, dayle_fee=2
                ),
                user=self.user,
            ),
            money_to_pay=Decimal("10"),
        )
        self.url = reverse(
            "borrowings:payment-detail", kwargs={"pk": self.payment.id}
        )

    def test_list_payments(self):
        request = self.factory.get(reverse("borrowings:payment-list"))
        force_authenticate(request, user=self.user)

        view = PaymentViewSet.as_view({"get": "list"})
        response = view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.payment.id)

    def test_payment_success(self):
        session_mock = mock.MagicMock()
        session_mock.payment_status = "paid"

        with mock.patch(
            "stripe.checkout.Session.retrieve", return_value=session_mock
        ):
            request = self.factory.get(
                reverse(
                    "borrowings:payment_success",
                    kwargs={"pk": self.payment.id},
                )
            )
            force_authenticate(request, user=self.user)

            view = PaymentViewSet.as_view({"get": "payment_success"})
            response = view(request, pk=self.payment.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Payment.objects.get(pk=self.payment.id).status,
            Payment.StatusChoices.PAID,
        )

    def test_payment_cancel(self):
        request = self.factory.get(
            reverse(
                "borrowings:payment_cancel", kwargs={"pk": self.payment.id}
            )
        )
        force_authenticate(request, user=self.user)

        view = PaymentViewSet.as_view({"get": "payment_cancel"})
        response = view(request, pk=self.payment.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["message"], "Payment can be made later."
        )
