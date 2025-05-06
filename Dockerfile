FROM python:3.11-slim

WORKDIR /app

# Встановлення необхідних пакетів для збірки та роботи
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Копіювання та встановлення залежностей перед кодом
# для кращого кешування Docker layers
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копіювання коду
COPY . .

# Налаштування змінних середовища
ENV PYTHONUNBUFFERED=1

# Запуск через gunicorn
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 'bot:flask_app'
