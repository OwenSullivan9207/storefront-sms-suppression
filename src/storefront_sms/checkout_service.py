from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .infrai_sms import InfraiError, InfraiSmsClient
from .order_updates import OrderSmsRequest, OrderUpdateSender, SendResult, SuppressionBook

app = FastAPI(title="Storefront SMS decisions")
suppressions = SuppressionBook(set())


class OptOutRequest(BaseModel):
    phone: str = Field(pattern=r"^\+[1-9]\d{7,14}$")


@app.post("/opt-outs", status_code=204)
def opt_out(request: OptOutRequest) -> None:
    suppressions.suppress(request.phone)


@app.post("/order-sms", response_model=SendResult)
def send_order_sms(request: OrderSmsRequest) -> SendResult:
    try:
        sender = OrderUpdateSender(InfraiSmsClient(), suppressions)
        return sender.deliver(request)
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=client_status, detail=exc.detail) from exc
