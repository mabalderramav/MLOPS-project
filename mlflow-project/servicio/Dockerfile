FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY api.py .

RUN useradd --create-home --uid 1000 appuser
USER appuser

# El modelo no viaja en la imagen: se descarga del Model Registry al arrancar.
ENV MODEL_URI=models:/adult-income-classifier@production
ENV MLFLOW_TRACKING_URI=http://mlflow:5001

EXPOSE 8000

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
