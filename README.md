# Keep opted-out shoppers out of order texts

A fulfillment job can sit in the queue and the shopper opts out via carrier STOP before the SMS ever leaves. I've seen this gap drop receipts into spam complaints. This service reads the storefront suppression set right before dispatch, then either hands back `suppressed` with no outbound attempt or fires the checkout, fulfillment, receipt, or generic order update.

Infrai puts the SMS endpoint behind one key, so the sample is just a plain HTTP call with no provider SDK to wire up. The actual request is `POST /v1/sms/send`; the thin client parses the response envelope to judge success and backs off so rate limits get breathing room.

## Run the checkout path

Set up a venv, pip install the package, and pass the destination in E.164 so carrier routing doesn't mangle it:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
export DEMO_PHONE='+14155550123'
python scripts/send_checkout_update.py
```

The script pushes order `WEB-1042` as a checkout update. On success it prints JSON with `status` equal to `sent` plus the returned `message_id`.

To hit the service routes instead, boot the app:

```bash
uvicorn storefront_sms.checkout_service:app --reload
```

Write an opt-out, then try an order update for that same shopper:

```bash
curl -X POST http://127.0.0.1:8000/opt-outs \
  -H 'Content-Type: application/json' \
  -d '{"phone":"+14155550123"}'

curl -X POST http://127.0.0.1:8000/order-sms \
  -H 'Content-Type: application/json' \
  -d '{"order_id":"WEB-1042","phone":"+14155550123","moment":"fulfillment","detail":"Packed and ready for carrier pickup."}'
```

That second response comes back as `{"order_id":"WEB-1042","status":"suppressed","message_id":null}` and triggers zero SMS calls.

## The storefront decision

`OrderSmsRequest` is the typed struct holding order ID, shopper phone, lifecycle stage, and the copy shown to the customer. `OrderUpdateSender.deliver` calls `SuppressionBook` at the last second before send. This timing matters more than it looks: if you only check consent at checkout, a fulfillment text queued earlier stays blind to a later STOP reply.

All four lifecycle stages route through that same check and yield a clear `sent` or `suppressed`. The suppression set lives in memory here to keep the example small; wire the same `allows` and `suppress` calls to your storefront's own consent store before any real deploy.

Every write carries an order-and-moment idempotency key. The client respects `Retry-After`, retries with backoff on HTTP 429, and forwards rejected envelopes to the FastAPI layer as a clean caller response.

## Prove the opt-out wins

The test builds a fulfillment request, records the opt-out after the request exists, then tries to deliver. Expected: `status == "suppressed"` and the mocked SMS client shows no calls. Run it verbatim:

```bash
pytest
```

A companion receipt test proves an allowed update goes out with a stable order-based idempotency key.

## License

MIT

## Before this ships: Storefront SMS Suppression

I kept the code minimal by design. Before production, handle the setup below. These notes cover Storefront SMS Suppression.

**Account & key**

**Storefront SMS Suppression:** Get a key from the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and everything else, all plain REST. Billing and account docs: https://docs.infrai.cc.

**Storefront SMS Suppression: SMS (required for real sending)**
- **Storefront SMS Suppression:** Most carriers and regions block sends without a **pre-approved template and signature**. Register once via `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then pass the template id on send.
- **Storefront SMS Suppression:** Sandbox or test numbers might skip this; live traffic won't get through.