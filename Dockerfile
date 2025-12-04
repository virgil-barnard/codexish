FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
 && rm -rf /var/lib/apt/lists/*

# Workdir
WORKDIR /app

# Copy project files
COPY pyproject.toml README.md cli.py minimal_example.py docker-compose.yml .env ./
COPY prompts ./prompts

# Optional: directory for certs if you mount certs.pem
RUN mkdir -p /app/certs

# Install Python deps directly (no packaging complexity)
RUN pip install --no-cache-dir \
    "pyautogen[openai]>=0.8,<1.0" \
    typer>=0.12.0 \
    python-dotenv>=1.0.0 \
    requests>=2.31.0 \
    autogen-agentchat~=0.2 \
    autogen-ext[openai]~=0.4

ENV PYTHONUNBUFFERED=1

# Default entrypoint:
# We fix the subcommand to "run", you pass options after.
ENTRYPOINT ["python", "cli.py", "run"]
