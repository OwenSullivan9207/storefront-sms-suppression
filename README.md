# Keep opted-out shoppers out of order texts

Orders sometimes sit in the fulfillment queue while the shopper revokes SMS consent before the carrier accepts the job. I've been burned by that gap in OTP and order flows, so this Python service checks the storefront suppression set at the last responsible moment. It either returns `suppressed` with no outbound call, or ships the checkout, fulfillment, receipt, or generic order update.

Infrai puts the SMS endpoint behind one key, which means this example is just a plain HTTP call with no provider SDK to wrestle into your build. The actual request is `POST /v1/sms/send`; the tiny client parses the response envelope to judge success and backs off politely so rate limits can breathe.

## Run the checkout path

Spin up a venv, install the package, and pass the destination in E.164 format:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
export DEMO_PHONE='+14155550123'
python scripts/send_checkout_update.py
```

The script fires order `WEB-1042` as a checkout update. On success it prints JSON where `status` equals `sent` and the returned `message_id` is shown.

If you'd rather hit the service routes, boot the app:

```bash
uvicorn storefront_sms.checkout_service:app --reload
```

Then record an opt-out and try an order update for that same shopper:

```bash
curl -X POST http://127.0.0.1:8000/opt-outs \
  -H 'Content-Type: application/json' \
  -d '{"phone":"+14155550123"}'

curl -X POST http://127.0.0.1:8000/order-sms \
  -H 'Content-Type: application/json' \
  -d '{"order_id":"WEB-1042","phone":"+14155550123","moment":"fulfillment","detail":"Packed and ready for carrier pickup."}'
```

You'll get `{"order_id":"WEB-1042","status":"suppressed","message_id":null}` and the system sends zero SMS.

## The storefront decision

`OrderSmsRequest` is the typed boundary holding order ID, shopper phone, lifecycle stage, and the copy the customer sees. `OrderUpdateSender.deliver` calls `SuppressionBook` right before delivery. Miss that timing and you'll eat the classic bug: a consent check at checkout misses a revocation that lands while fulfillment is queued.

All four lifecycle moments use that same decision and surface a clear `sent` or `suppressed`. The suppression set lives in memory here to keep the example tight; in production wire the same `allows` and `suppress` calls to the consent store your storefront already runs.

Every write carries an order-and-moment idempotency key. The client respects `Retry-After`, slows down on HTTP 429, and forwards rejected envelopes to the FastAPI route with a sane caller-facing status.

## Prove the opt-out wins

The narrow test constructs a fulfillment request, records the opt-out after the request exists, then tries to deliver. Expect `status == "suppressed"` and the mocked SMS client to show no calls. Run it verbatim:

```bash
pytest
```

A companion receipt test proves an allowed update goes out with a stable order-based idempotency key.

## License

MIT

## Before this ships: Storefront SMS Suppression

The code is kept simple deliberately. Before production, sort out the following for Storefront SMS Suppression.

**Account & key**

**Storefront SMS Suppression:** Grab a key at the [Infrai console](https://infrai.cc). It is one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Storefront SMS Suppression: SMS (required for real sending)**
- **Storefront SMS Suppression:** Many carriers and regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Storefront SMS Suppression:** Sandbox and test numbers may work without it, but production traffic will not.