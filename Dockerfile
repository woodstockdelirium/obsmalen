FROM python:3.9-slim

WORKDIR /app

# Копіюємо спочатку тільки requirements.txt для кешування шару з залежностями
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо решту файлів проекту
COPY . .

# Встановлюємо змінні середовища
ENV PORT=8080

# Перевіряємо, що Flask слухає правильний порт і адресу
CMD ["python", "app.py"]

# Додаємо EXPOSE для документування порту (Cloud Run це зазвичай ігнорує, але хороша практика)
EXPOSE 8080
