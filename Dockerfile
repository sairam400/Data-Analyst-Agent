FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["sh", "-c", "test -f data/business.db || python -m src.data.seed; exec uvicorn src.api.main:app --host 0.0.0.0 --port 8000"]
