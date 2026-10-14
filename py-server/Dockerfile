FROM python:3.12-slim-bookworm

WORKDIR /app

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x docker-entrypoint.sh

# CUDA libs are bind-mounted at runtime
ENV LD_LIBRARY_PATH="/opt/cuda_libs"

EXPOSE 8000
# Invoke via sh so the entrypoint works from bind mounts where the exec bit
# may not survive (e.g. a Windows host).
ENTRYPOINT ["sh", "docker-entrypoint.sh"]
