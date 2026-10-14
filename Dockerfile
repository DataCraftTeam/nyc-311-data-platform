FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY pipeline ./pipeline
ENV PYTHONPATH=/app DAGSTER_HOME=/app/dagster_home
RUN mkdir -p $DAGSTER_HOME
CMD ["dagster", "dev", "-h", "0.0.0.0", "-p", "3000", "-m", "pipeline.definitions"]