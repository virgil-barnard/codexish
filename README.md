# codexish

This project provides a CLI tool `autogen-gh` that:

- Clones a GitHub repo locally
- Creates a new work branch
- Uses AutoGen v2 (autogen-agentchat) to run:
  - A Dev Agent (writes code)
  - A Reviewer Agent (ensures correctness)
  - A UserProxy Agent (executes code & edits files)
- Applies edits through tool-based Python execution
- Runs tests
- Commits and pushes changes
- Opens a Pull Request automatically
- Optionally uses GitHub Issues as task descriptions via `--issue <num>`

## Running in Docker

1. Copy `.env.example` to `.env` and fill in real values:

```bash
cp .env.example .env
```

Build the image:
```bash
docker compose build
```

Run with an explicit task:
```bash
docker compose run --rm autogen-agent \
  --repo-url git@github.com:YourUser/YourRepo.git \
  --task "Add a --dry-run flag and update tests."
```
Or run based on an Issue:
```bash
docker compose run --rm autogen-agent \
  --repo-url https://github.com/YourUser/YourRepo.git \
  --issue 42
```

If you are using certs.pem, either:
- Set SSL_CERT_FILE in .env and mount the file:
```yaml
# in docker-compose.yml
volumes:
  - ./certs/certs.pem:/app/certs/certs.pem:ro
```

- Or rely on REQUESTS_CA_BUNDLE similarly.
```yaml

---

That should give you a completely self-contained, Docker-ready, `.env`-driven Autogen v2 GitHub agent you can print and stash for future hacking.
::contentReference[oaicite:0]{index=0}
```