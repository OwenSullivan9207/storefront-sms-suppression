import os

from storefront_sms.infrai_sms import InfraiSmsClient
from storefront_sms.order_updates import (
    OrderMoment,
    OrderSmsRequest,
    OrderUpdateSender,
    SuppressionBook,
)


def main() -> None:
    phone = os.environ.get("DEMO_PHONE")
    if not phone:
        raise SystemExit("DEMO_PHONE is required")

    sender = OrderUpdateSender(InfraiSmsClient(), SuppressionBook(set()))
    result = sender.deliver(
        OrderSmsRequest(
            order_id="WEB-1042",
            phone=phone,
            moment=OrderMoment.CHECKOUT,
            detail="We have your order and will send tracking after packing.",
        )
    )
    print(result.model_dump_json())


if __name__ == "__main__":
    main()
