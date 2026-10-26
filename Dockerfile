FROM python:3.11-slim-bookworm

LABEL maintainer="Pulsearr Team"
LABEL description="Pulsearr - Next-Gen Asynchronous Python TV PVR"

ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PULSEARR_DATA_DIR=/data \
    PULSEARR_HOST=0.0.0.0 \
    PULSEARR_PORT=8990

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY pulsearr/ ./pulsearr/
COPY static/ ./static/
COPY templates/ ./templates/
COPY run.py .

RUN mkdir -p /data/media/tv

EXPOSE 8990
VOLUME ["/data"]

CMD ["python", "run.py"]
