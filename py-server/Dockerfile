FROM python:3.11.17-slim-bookworm

WORKDIR /app

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# CUDA libs are bind-mounted at runtime
ENV LD_LIBRARY_PATH="/opt/cuda_libs"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--ssl-keyfile", "192.168.100.4-key.pem", \
     "--ssl-certfile", "192.168.100.4.pem", \
     "--reload"] # Must be removed for prod