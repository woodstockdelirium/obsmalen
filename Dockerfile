# Використовуємо Python 3.10
FROM python:3.10-slim

# Встановлюємо необхідні бібліотеки
RUN apt-get update && apt-get install -y \
    python3-dev \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Створюємо та активуємо віртуальне середовище
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Копіюємо файли в контейнер
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо весь код
COPY . /app

# Перехід до директорії з вашим кодом
WORKDIR /app

# Запуск додатку
CMD ["python", "main.py"]
