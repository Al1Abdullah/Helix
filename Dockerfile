FROM python:3.12-slim

WORKDIR /app

# Layer cache: install deps before copying full source
COPY pyproject.toml .
COPY src/ ./src/

RUN pip install --no-cache-dir .

# Copy remaining files (tests, docs, etc.)
COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD python -c "import httpx, sys; r=httpx.get('http://localhost:8000/health',timeout=5); sys.exit(0 if r.status_code==200 else 1)"

CMD ["helix-api"]
