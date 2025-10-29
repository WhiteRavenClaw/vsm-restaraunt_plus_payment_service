FROM python:3.13-slim

WORKDIR /app

# Устанавливаем менеджер пакетов uv
RUN pip install uv

# Копируем зависимости (если в payment_service есть свой pyproject.toml и uv.lock)
COPY pyproject.toml uv.lock ./
RUN uv sync

# Копируем код микросервиса
COPY . .

# Открываем порт для FastAPI
EXPOSE 8001

# Запускаем сервис
CMD ["uv", "run", "python", "main.py"]
