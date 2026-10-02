FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# CUDA libs are bind-mounted at runtime (see compose.yaml) into this path
ENV LD_LIBRARY_PATH="/opt/cuda_libs:${LD_LIBRARY_PATH}"

# Launch binding explicitly to 0.0.0.0
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--ssl-keyfile", "192.168.100.4-key.pem", "--ssl-certfile", "192.168.100.4.pem", "--reload"]