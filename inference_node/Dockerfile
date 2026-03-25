FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# NODE_PORT 由 compose 传入环境变量
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${NODE_PORT:-8001}"]
