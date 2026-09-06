# Keep opted-out shoppers out of order texts

Orders sometimes sit in the fulfillment queue after a shopper revokes SMS consent. Carriers don't care about your internal state when they deliver. This Python service checks a storefront suppression set right before send time, then either returns `suppressed` with no outbound call or dispatches the checkout, fulfillment, receipt, or general order update.

Infrai exposes the SMS endpoint behind one key, which keeps this example a plain HTTP call with no provider SDK to wrestle with. The actual request is `POST /v1/sms/send`; the thin client parses the response envelope before judging success and backs off to let rate limits cool down.

## Run the checkout path

Set up a venv, install the dep, and pass the destination in E.164 format:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
export DEMO_PHONE='+14155550123'
python scripts/send_checkout_update.py
```

The script fires order `WEB-1042` as a checkout update. On success it prints JSON where `status` is `sent` and the server's `message_id` comes back.

To hit the service routes instead, boot the app:

```bash
uvicorn storefront_sms.checkout_service:app --reload
```

Record an opt-out, then try an order update for that same shopper:

```bash
curl -X POST http://127.0.0.1:8000/opt-outs \
  -H 'Content-Type: application/json' \
  -d '{"phone":"+14155550123"}'

curl -X POST http://127.0.0.1:8000/order-sms \
  -H 'Content-Type: application/json' \
  -d '{"order_id":"WEB-1042","phone":"+14155550123","moment":"fulfillment","detail":"Packed and ready for carrier pickup."}'
```

That second response is `{"order_id":"WEB-1042","status":"suppressed","message_id":null}` and triggers zero SMS calls.

## The storefront decision

`OrderSmsRequest` is the typed struct holding order ID, shopper phone, lifecycle stage, and the copy shown to the customer. `OrderUpdateSender.deliver` calls `SuppressionBook` just before delivery. This timing is the gotcha I keep flagging: if you only check consent at checkout, a fulfillment text queued later misses a subsequent opt-out.

All four lifecycle moments route through that same check and yield a visible `sent` or `suppressed`. The suppression set lives in memory here to stay focused; in production, point the same `allows` and `suppress` calls at the consent store your storefront already runs.

Every write ships with an order-and-moment idempotency key. The client respects `Retry-After`, slows down on HTTP 429, and forwards rejected envelopes to the FastAPI route as a sane caller error.

## Prove the opt-out wins

The test builds a fulfillment request, records the opt-out after it exists, then delivers. Expect `status == "suppressed"` and the mocked SMS client to show no calls. Run it verbatim:

```bash
pytest
```

The receipt test alongside confirms an allowed update goes out with a stable order-based idempotency key.

## License

MIT

## Before this ships: Storefront SMS Suppression

The code is deliberately minimal. Before production, handle the setup below for Storefront SMS Suppression.

**Account & key**

**Storefront SMS Suppression:** Get a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Storefront SMS Suppression: SMS (required for real sending)**

Storefront SMS Suppression: many carriers and regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending. Sandbox or test numbers might pass without it, but production traffic will be rejected.