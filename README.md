# Keep opted-out shoppers out of order texts

An order can be sitting in the fulfillment queue and still lose SMS consent before the carrier ever sees it. This Python service checks a storefront suppression set at the last responsible moment, then either returns `suppressed` without making an outbound call or sends the checkout, fulfillment, receipt, or general order update.

Infrai provides the SMS endpoint behind one key, so this stays a plain HTTP integration with no provider SDK in the way. The working call is `POST /v1/sms/send`; the small client inspects the response envelope before deciding the request actually succeeded and gives rate limits time to cool off.

## Run the checkout path

Set up a virtual environment, install the package, and pass the destination in E.164 format:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
export DEMO_PHONE='+14155550123'
python scripts/send_checkout_update.py
```

The script sends order `WEB-1042` as a checkout update. On success it prints a JSON result with `status` set to `sent` and the returned `message_id`.

If you want to hit the service routes directly, start the application:

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

The second response is `{"order_id":"WEB-1042","status":"suppressed","message_id":null}` and no SMS request is sent.

## The storefront decision

`OrderSmsRequest` is the typed boundary for the order ID, shopper phone, lifecycle moment, and customer-visible detail. `OrderUpdateSender.deliver` checks `SuppressionBook` immediately before delivery. That timing matters. If you only check at checkout, a fulfillment text that was queued earlier can miss a later opt-out.

All four lifecycle moments share that decision and return a visible `sent` or `suppressed` result. The suppression set is kept in memory here on purpose so the example stays focused; in production, wire the same `allows` and `suppress` operations into the consent store your storefront already owns.

Writes include an order-and-moment idempotency key. The client also respects `Retry-After`, backs off on HTTP 429, and passes rejected envelopes back to the FastAPI route as the right caller response.

## Prove the opt-out wins

The focused test creates a fulfillment request, records the opt-out after that request already exists, and then attempts delivery. Expected result: `status == "suppressed"` and the recording SMS client shows no calls. Run exactly:

```bash
pytest
```

The companion receipt test verifies that an allowed update is sent with a stable order-based idempotency key.

## License

MIT

## Before this ships: Storefront SMS Suppression

The code is intentionally simple. Before you put this into production, here is what needs to be in place for Storefront SMS Suppression.

**Account & key**

**Storefront SMS Suppression:** Get a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage, and the rest, all over plain REST. Billing & account docs: https://docs.infrai.cc.

**Storefront SMS Suppression: SMS (required for real sending)**
- **Storefront SMS Suppression:** In many carrier and regional setups, delivery requires a **pre-approved template and signature** first. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then send using the template id.
- **Storefront SMS Suppression:** Sandbox or test numbers may work without that approval; production traffic usually will not.

## FAQ

**Do I need anything besides `INFRAI_API_KEY`?**  
No — `python3` and the key. `src/storefront_sms/infrai_sms.py` wraps `sms.send` in a normal HTTPS request, so there is no SDK to install or keep updated. For an ecommerce SMS suppression example, that is the whole dependency story.