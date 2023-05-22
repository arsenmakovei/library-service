from rest_framework import serializers

from books.serializers import BookSerializer
from borrowings.models import Borrowing


class BorrowingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrowing
        fields = (
            "id",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
            "book",
            "user",
        )
        read_only_fields = ("id", "borrow_date", "actual_return_date", "user")

    def validate_book(self, book):
        if book.inventory == 0:
            raise serializers.ValidationError(
                "Book is not available for borrowing."
            )
        return book

    def create(self, validated_data):
        book = validated_data["book"]
        user = self.context["request"].user
        borrowing = Borrowing.objects.create(
            expected_return_date=validated_data["expected_return_date"],
            book=book,
            user=user,
        )
        book.inventory -= 1
        book.save()
        return borrowing


class BorrowingListSerializer(BorrowingSerializer):
    book = BookSerializer(read_only=True)
    user = serializers.ReadOnlyField(source="user.email")


class BorrowingReturnSerializer(BorrowingSerializer):
    expected_return_date = serializers.ReadOnlyField()
    book = serializers.ReadOnlyField()
