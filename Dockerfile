FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
 && rm -rf /var/lib/apt/lists/*

# Workdir
WORKDIR /app

# Copy project files
COPY pyproject.toml README.md cli.py minimal_example2.py docker-compose.yml .env ./
COPY prompts ./prompts

# Optional: directory for certs if you mount certs.pem
RUN mkdir -p /app/certs

# Install Python deps directly (no packaging complexity)
RUN pip install --no-cache-dir \
    typer>=0.12.0 \
    python-dotenv>=1.0.0 \
    requests>=2.31.0 \
    langchain==0.1.17 \
    langchain-community==0.0.36 \
    openai==1.16.1

ENV PYTHONUNBUFFERED=1

# Default entrypoint:
# We fix the subcommand to "run", you pass options after.
ENTRYPOINT ["python", "minimal_example2.py", "run"]
