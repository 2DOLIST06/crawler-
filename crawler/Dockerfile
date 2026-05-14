FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && playwright install chromium
COPY . .
CMD ["uvicorn","crawler_app.main:app","--host","0.0.0.0","--port","10000"]
