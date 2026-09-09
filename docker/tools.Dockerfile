FROM postgres:14.24
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 ca-certificates \
 && rm -rf /var/lib/apt/lists/*
COPY scripts/branding.py scripts/wiki-start.sh scripts/backup.sh scripts/backup.py /app/
ENTRYPOINT ["python3", "/app/branding.py"]
