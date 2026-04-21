FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml .
COPY agentseceval/ agentseceval/
COPY dataset/ dataset/

RUN pip install --no-cache-dir -e .

# Non-root user for minimal privilege
RUN useradd -m evaluser
USER evaluser

ENTRYPOINT ["python", "-m", "agentseceval.experiments.orchestrator"]
