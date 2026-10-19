
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --retries 10 --timeout 180 -r requirements.txt

COPY src/ src/

CMD ["python", "-m", "src.etl.etl_pipeline"]
