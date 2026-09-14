FROM docker:29-cli AS dockercli

FROM postgres:14.24

RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY --from=dockercli /usr/local/bin/docker /usr/local/bin/docker

COPY scripts/branding.py scripts/wiki-start.sh scripts/backup.sh scripts/backup.py scripts/report-deployment.py /app/

ENTRYPOINT ["python3", "/app/branding.py"]
