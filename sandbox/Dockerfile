FROM python:3.12-slim
WORKDIR /app
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/browsers PYTHONDONTWRITEBYTECODE=1
COPY pyproject.toml README.md LICENSE ./
COPY ghostdiff ./ghostdiff
RUN apt-get update && apt-get install -y --no-install-recommends libatomic1 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir . && python -m playwright install --with-deps chromium && chmod -R a+rX /opt/browsers && useradd --uid 10001 --create-home ghostdiff
COPY benchmarks ./benchmarks
USER 10001:10001
ENV HOME=/home/ghostdiff XDG_CACHE_HOME=/tmp/cache XDG_CONFIG_HOME=/tmp/config
ENTRYPOINT ["actrift"]
CMD ["demo","--out","/tmp/report"]
