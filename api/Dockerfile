FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Usuário sem privilégios; as pastas de fotos e de e-mails precisam ser dele.
RUN useradd --system --create-home api \
    && mkdir -p uploads/fotos caixa-de-saida \
    && chown -R api /app
USER api

EXPOSE 8000
# Produção: sem --reload. A porta vem de $PORT quando a hospedagem define (Render, Railway…); senão, 8000.
# --proxy-headers: atrás do proxy HTTPS da hospedagem, a API enxerga o endereço e o protocolo reais.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
