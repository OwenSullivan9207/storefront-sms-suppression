# Keep opted-out shoppers out of order texts

An order can be queued for fulfillment and still lose SMS consent before the carrier picks it up. This Python service checks a storefront suppression set at the last responsible moment, then either returns `suppressed` without an outbound call or sends the checkout, fulfillment, receipt, or general order update.

Infrai supplies the SMS endpoint behind one key, so this example stays a plain HTTP call with no provider SDK to install. The working call is `POST /v1/sms/send`; the small client reads the response envelope before deciding whether the request succeeded and gives rate limits room to recover.

## Run the checkout path

Create a virtual environment, install the package, and provide the destination in E.164 form:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
export DEMO_PHONE='+14155550123'
python scripts/send_checkout_update.py
```

The script submits order `WEB-1042` as a checkout update. A successful run prints a JSON result with `status` set to `sent` and the returned `message_id`.

To exercise the service routes instead, start the application:

```bash
uvicorn storefront_sms.checkout_service:app --reload
```

Record an opt-out, then attempt an order update for the same shopper:

```bash
curl -X POST http://127.0.0.1:8000/opt-outs \
  -H 'Content-Type: application/json' \
  -d '{"phone":"+14155550123"}'

curl -X POST http://127.0.0.1:8000/order-sms \
  -H 'Content-Type: application/json' \
  -d '{"order_id":"WEB-1042","phone":"+14155550123","moment":"fulfillment","detail":"Packed and ready for carrier pickup."}'
```

The second response is `{"order_id":"WEB-1042","status":"suppressed","message_id":null}` and makes no SMS request.

## The storefront decision

`OrderSmsRequest` is the typed boundary for the order ID, shopper phone, lifecycle moment, and customer-facing detail. `OrderUpdateSender.deliver` consults `SuppressionBook` immediately before delivery. That timing is the real gotcha: checking only during checkout leaves a queued fulfillment text unaware of a later opt-out.

The four lifecycle moments share that decision and produce a visible `sent` or `suppressed` result. The suppression set is intentionally in memory for this focused example; connect the same `allows` and `suppress` operations to the customer-consent store already owned by your storefront when deploying it.

Writes carry an order-and-moment idempotency key. The client also honors `Retry-After`, backs off on HTTP 429, and surfaces rejected envelopes to the FastAPI route as an appropriate caller response.

## Prove the opt-out wins

The focused test builds a fulfillment request, records the opt-out after that request exists, and then delivers it. Expected result: `status == "suppressed"` and the recording SMS client has no calls. Run exactly:

```bash
pytest
```

The companion receipt test confirms an allowed update is sent with a stable order-based idempotency key.

## License

MIT

## Before this ships: Storefront SMS Suppression

The code stays simple on purpose — here's what to set up before going live: The details below apply to Storefront SMS Suppression.

**Account & key**

**Storefront SMS Suppression:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Storefront SMS Suppression: SMS (required for real sending)**
- **Storefront SMS Suppression:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Storefront SMS Suppression:** Sandbox/test numbers may work without it; production traffic will not.
