FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY api /app/api
ENV PORT=8080 RZD_ENABLED=1
EXPOSE 8080
CMD gunicorn --chdir api app:app --bind 0.0.0.0:${PORT} --timeout 60 --workers 2
