FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY agents/requirements.txt /app/agents/requirements.txt
RUN pip install --no-cache-dir -r agents/requirements.txt

# Copy agent source
COPY agents/src/ /app/agents/src/

# Ensure the package is importable
ENV PYTHONPATH=/app

CMD ["python", "-m", "agents.src.main"]
