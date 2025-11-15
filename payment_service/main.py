# payment_service/main.py
# from fastapi import FastAPI, HTTPException
# import httpx

# app = FastAPI(title="Fake Payment Service")

# @app.post("/create")
# def create_payment(order_id: int):
#     # генерируем "ссылку на оплату"
#     return {"payment_link": f"http://fakebank.local/pay/{order_id}"}

# @app.post("/webhook")
# def send_webhook(order_id: int):
#     # эмулируем уведомление основному сервису
#     try:
#         r = httpx.post("http://restaurant-api:8000/payments/webhook", json={"order_id": order_id})
#         r.raise_for_status()
#         return {"status": "ok"}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @app.post("/refund")
# def refund_payment(order_id: int):
#     # просто выводим лог (в реальности тут был бы возврат)
#     print(f"Refund issued for order {order_id}")
#     return {"status": "refunded"}
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import httpx
import random

app = FastAPI(title="Fake Payment Service")

# Временное хранилище для демо
payments_db = {}

class PaymentCreateRequest(BaseModel):
    order_id: int
    amount: float
    type: str = "card"

@app.post("/create")
def create_payment(request: PaymentCreateRequest):
    order_id = request.order_id
    amount = request.amount
    payment_type = request.type
    # Генерируем ссылку на оплату
    payment_id = f"pay_{random.randint(1000, 9999)}"
    
    # Для СБП генерируем специальную ссылку
    if payment_type == "sbp":
        payment_link = f"http://localhost:8001/pay/sbp/{payment_id}"
    else:
        payment_link = f"http://localhost:8001/pay/{payment_id}"
    
    payments_db[payment_id] = {
        "order_id": order_id,
        "amount": amount,
        "status": "pending",
        "type": payment_type
    }
    
    return {
        "payment_id": payment_id,
        "payment_link": payment_link,
        "status": "created"
    }

@app.get("/pay/{payment_id}", response_class=HTMLResponse)
def simulate_payment(payment_id: str):
    """Симуляция страницы оплаты"""
    payment = payments_db.get(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return f"""
    <html>
        <body>
            <h1>Оплата заказа #{payment['order_id']}</h1>
            <p>Сумма: {payment['amount']} руб.</p>
            <form action="/confirm/{payment_id}" method="post">
                <button type="submit">Оплатить</button>
            </form>
            <form action="/cancel/{payment_id}" method="post">
                <button type="submit">Отмена</button>
            </form>
        </body>
    </html>
    """

@app.get("/pay/sbp/{payment_id}", response_class=HTMLResponse)
def simulate_sbp_payment(payment_id: str):
    """Симуляция оплаты через СБП - автоматически подтверждает оплату"""
    payment = payments_db.get(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # Автоматически подтверждаем оплату
    if payment["status"] == "pending":
        payment["status"] = "success"
        print(f"Payment {payment_id} confirmed for order {payment['order_id']}")
        
        # Отправляем вебхук основному сервису (синхронно, чтобы убедиться, что он отправлен)
        try:
            print(f"Sending webhook to restaurant-api for order {payment['order_id']}")
            r = httpx.post(
                "http://restaurant-api:8000/payments/webhook",
                json={"order_id": payment["order_id"], "status": "success"},
                timeout=5.0
            )
            r.raise_for_status()
            print(f"Webhook sent successfully for order {payment['order_id']}")
        except Exception as e:
            print(f"Webhook error for order {payment['order_id']}: {e}")
            # Не прерываем выполнение, просто логируем ошибку
    
    # Показываем страницу успешной оплаты
    return f"""
    <html>
        <head>
            <title>Оплата через СБП</title>
            <meta http-equiv="refresh" content="3;url=http://localhost:3000">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 600px;
                    margin: 50px auto;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .container {{
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    text-align: center;
                }}
                h1 {{
                    color: #4CAF50;
                }}
                .amount {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #4CAF50;
                    margin: 20px 0;
                }}
                .success-icon {{
                    font-size: 64px;
                    color: #4CAF50;
                    margin: 20px 0;
                }}
                .message {{
                    color: #666;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success-icon">✓</div>
                <h1>Оплата успешно выполнена!</h1>
                <p>Заказ #{payment['order_id']}</p>
                <div class="amount">Сумма: {payment['amount']} руб.</div>
                <p class="message">Вы будете перенаправлены на главную страницу через 3 секунды...</p>
            </div>
        </body>
    </html>
    """

@app.post("/confirm/{payment_id}")
def confirm_payment(payment_id: str):
    """Подтверждение оплаты"""
    payment = payments_db.get(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    payment["status"] = "success"
    
    # Отправляем вебхук основному сервису
    try:
        r = httpx.post(
            "http://restaurant-api:8000/payments/webhook",
            json={"order_id": payment["order_id"], "status": "success"}
        )
        r.raise_for_status()
    except Exception as e:
        print(f"Webhook error: {e}")
    
    return {"status": "payment_confirmed"}

@app.post("/cancel/{payment_id}")
def cancel_payment(payment_id: str):
    """Отмена оплаты"""
    payment = payments_db.get(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    payment["status"] = "cancelled"
    return {"status": "payment_cancelled"}

@app.post("/refund")
def refund_payment(order_id: int):
    """Возврат средств"""
    print(f"Refund issued for order {order_id}")
    return {"status": "refunded", "order_id": order_id}

@app.post("/webhook")
def send_webhook(order_id: int):
    """Ручной вызов вебхука (для тестирования)"""
    try:
        r = httpx.post(
            "http://restaurant-api:8000/payments/webhook",
            json={"order_id": order_id, "status": "success"}
        )
        r.raise_for_status()
        return {"status": "webhook_sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))