# Image pinnée au patch près — mettre à jour régulièrement (correctifs)
FROM python:3.13.16-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server/ server/

RUN useradd -r -u 10001 app
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health', timeout=5)" || exit 1

# --proxy-headers : fait confiance à X-Forwarded-For du reverse proxy (Traefik/WAF).
# Ne pas exposer le conteneur directement sans proxy.
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
