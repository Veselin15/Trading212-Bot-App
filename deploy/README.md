# Server deploy bundle

1. Copy `env.backend.example` → `.env` and fill secrets.
2. `docker compose pull && docker compose up -d`
3. Map **signals.swifttrade.app** in Cloudflare Tunnel → `http://localhost:8010`

Full guide: [../docs/DEPLOY.md](../docs/DEPLOY.md).
