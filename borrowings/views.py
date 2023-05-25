import os

import stripe
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from borrowings.models import Borrowing, Payment
from borrowings.notification_service import send_telegram_message
from borrowings.serializers import (
    BorrowingSerializer,
    BorrowingListSerializer,
    BorrowingReturnSerializer,
    PaymentSerializer,
)


stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


class BorrowingViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Borrowing.objects.select_related("book", "user")
    serializer_class = BorrowingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = self.queryset
        is_active = self.request.query_params.get("is_active")
        user_id = self.request.query_params.get("user_id")

        if is_active:
            if is_active.lower() == "true":
                queryset = queryset.filter(actual_return_date=None)
            else:
                queryset = queryset.exclude(actual_return_date=None)

        if self.request.user.is_staff:
            if user_id:
                queryset = queryset.filter(user__id=user_id)

            return queryset

        return queryset.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return BorrowingListSerializer

        if self.action == "book_return":
            return BorrowingReturnSerializer

        return BorrowingSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(methods=["POST"], detail=True, url_path="return")
    def book_return(self, request, pk=None):
        borrowing = self.get_object()

        if borrowing.actual_return_date is not None:
            return Response(
                {"error": "Book has already been returned"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        borrowing.actual_return_date = timezone.now().date()
        borrowing.save()

        book = borrowing.book
        book.inventory += 1
        book.save()

        if borrowing.actual_return_date > borrowing.expected_return_date:
            fine_amount = borrowing.fine_price

            Payment.objects.create(
                status=Payment.StatusChoices.PENDING,
                type=Payment.TypeChoices.FINE,
                borrowing=borrowing,
                money_to_pay=fine_amount,
            )

        return Response(
            {"success": "Your book was successfully returned"},
            status=status.HTTP_200_OK,
        )


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = self.queryset

        if not self.request.user.is_staff:
            return queryset.filter(borrowing__user=self.request.user)

        return queryset

    @action(detail=True, methods=["GET"], url_path="success")
    def payment_success(self, request, pk=None):
        payment = get_object_or_404(Payment, pk=pk)

        session = stripe.checkout.Session.retrieve(payment.session_id)
        if session.payment_status == "paid":
            payment.status = Payment.StatusChoices.PAID
            payment.save()

            message = (
                f"Payment #{payment.id} was successful.\n"
                f"Type: {payment.type}\n"
                f"Borrowing: {payment.borrowing}"
            )
            send_telegram_message(message)

            return Response(
                {"success": "Payment was successful."},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"error": "Payment was not successful."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["GET"], url_path="cancel")
    def payment_cancel(self, request, pk=None):
        return Response(
            {"message": "Payment can be made later."},
            status=status.HTTP_200_OK,
        )
