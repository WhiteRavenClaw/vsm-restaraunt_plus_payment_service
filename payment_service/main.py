# payment_service/main.py
from fastapi import FastAPI, HTTPException
import httpx

app = FastAPI(title="Fake Payment Service")

@app.post("/create")
def create_payment(order_id: int):
    # генерируем "ссылку на оплату"
    return {"payment_link": f"http://fakebank.local/pay/{order_id}"}

@app.post("/webhook")
def send_webhook(order_id: int):
    # эмулируем уведомление основному сервису
    try:
        r = httpx.post("http://restaurant-api:8000/payments/webhook", json={"order_id": order_id})
        r.raise_for_status()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/refund")
def refund_payment(order_id: int):
    # просто выводим лог (в реальности тут был бы возврат)
    print(f"Refund issued for order {order_id}")
    return {"status": "refunded"}
