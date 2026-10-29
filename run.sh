#!/bin/sh
# Punto de entrada del conector en Lambda (AWS Lambda Web Adapter llama a este script).
exec python3 -m uvicorn aws_lambda.conector:app --host 0.0.0.0 --port "${AWS_LWA_PORT:-8080}" --log-level warning
