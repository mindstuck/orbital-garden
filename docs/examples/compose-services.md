# Example Compose services (not active)

These services are **not** part of the running stack. They are kept here as
reference definitions for future milestones and are not presented as
operational. See `docs/decisions/0004-coding-agent-boundary.md` for how
provider integrations stay behind adapter contracts.

## 9router (smart routing, planned)

```yaml
  9router:
    image: decolua/9router:latest
    container_name: 9router
    restart: unless-stopped
    ports:
      - "127.0.0.1:20128:20128"
    volumes:
      - router_data:/app/data
    env_file:
      - .env
    environment:
      DATA_DIR: /app/data
      PORT: 20128
      HOSTNAME: 0.0.0.0
      NODE_ENV: production
```

## Ollama (alternative local model server, planned)

```yaml
  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    restart: unless-stopped
    ports:
      - "127.0.0.1:11434:11434"
    volumes:
      - ollama_data:/root/.ollama
```

If one of these is adopted, pin a specific image tag/digest, publish ports on
loopback only, provide a named volume, and remove secrets from any committed
example.
