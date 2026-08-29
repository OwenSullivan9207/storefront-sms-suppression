from storefront_sms.order_updates import (
    OrderMoment,
    OrderSmsRequest,
    OrderUpdateSender,
    SuppressionBook,
)


class RecordingSms:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def send(self, *, to: str, message: str, idempotency_key: str) -> dict:
        self.calls.append(
            {"to": to, "message": message, "idempotency_key": idempotency_key}
        )
        return {"message_id": "msg_1042"}


def request_for(phone: str, moment: OrderMoment = OrderMoment.FULFILLMENT) -> OrderSmsRequest:
    return OrderSmsRequest(
        order_id="WEB-1042",
        phone=phone,
        moment=moment,
        detail="Packed and ready for carrier pickup.",
    )


def test_opted_out_customer_is_suppressed_at_delivery_time() -> None:
    sms = RecordingSms()
    book = SuppressionBook(set())
    sender = OrderUpdateSender(sms, book)
    queued_request = request_for("+14155550123")

    book.suppress("+14155550123")
    result = sender.deliver(queued_request)

    assert result.status == "suppressed"
    assert result.message_id is None
    assert sms.calls == []


def test_allowed_receipt_is_sent_with_stable_idempotency_key() -> None:
    sms = RecordingSms()
    sender = OrderUpdateSender(sms, SuppressionBook(set()))

    result = sender.deliver(request_for("+14155550123", OrderMoment.RECEIPT))

    assert result.status == "sent"
    assert result.message_id == "msg_1042"
    assert sms.calls[0]["idempotency_key"] == "order:WEB-1042:receipt"
