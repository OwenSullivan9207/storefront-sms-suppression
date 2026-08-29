from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Protocol


class OrderMoment(str, Enum):
    CHECKOUT = "checkout"
    FULFILLMENT = "fulfillment"
    RECEIPT = "receipt"
    ORDER_UPDATE = "order_update"


@dataclass
class OrderSmsRequest:
    order_id: str
    phone: str
    moment: OrderMoment
    detail: str

    def __post_init__(self) -> None:
        if not self.order_id:
            raise ValueError("order_id must not be empty")
        if not re.fullmatch(r"\+[1-9]\d{7,14}", self.phone):
            raise ValueError("phone must be a valid E.164 number")
        if not isinstance(self.moment, OrderMoment):
            try:
                self.moment = OrderMoment(self.moment)
            except (TypeError, ValueError) as exc:
                raise ValueError("moment must be a valid order moment") from exc
        if not 1 <= len(self.detail) <= 240:
            raise ValueError("detail must contain between 1 and 240 characters")


@dataclass
class SendResult:
    order_id: str
    status: str
    message_id: str | None = None


class SmsSender(Protocol):
    def send(self, *, to: str, message: str, idempotency_key: str) -> dict:
        raise AssertionError("protocol method")


@dataclass
class SuppressionBook:
    opted_out: set[str]

    def suppress(self, phone: str) -> None:
        self.opted_out.add(phone)

    def allows(self, phone: str) -> bool:
        return phone not in self.opted_out


class OrderUpdateSender:
    def __init__(self, sms: SmsSender, suppressions: SuppressionBook) -> None:
        self.sms = sms
        self.suppressions = suppressions

    def deliver(self, request: OrderSmsRequest) -> SendResult:
        # Check consent at delivery time, after any queueing or fulfillment work.
        if not self.suppressions.allows(request.phone):
            return SendResult(order_id=request.order_id, status="suppressed")

        message = self._message(request)
        result = self.sms.send(
            to=request.phone,
            message=message,
            idempotency_key=f"order:{request.order_id}:{request.moment.value}",
        )
        return SendResult(
            order_id=request.order_id,
            status="sent",
            message_id=result.get("message_id"),
        )

    @staticmethod
    def _message(request: OrderSmsRequest) -> str:
        labels = {
            OrderMoment.CHECKOUT: "Order confirmed",
            OrderMoment.FULFILLMENT: "Fulfillment update",
            OrderMoment.RECEIPT: "Receipt",
            OrderMoment.ORDER_UPDATE: "Order update",
        }
        return f"{labels[request.moment]} for {request.order_id}: {request.detail}"
