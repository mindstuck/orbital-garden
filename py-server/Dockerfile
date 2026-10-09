FROM python:3.11.17-slim-bookworm

WORKDIR /app

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x docker-entrypoint.sh

# CUDA libs are bind-mounted at runtime
ENV LD_LIBRARY_PATH="/opt/cuda_libs"

EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]
