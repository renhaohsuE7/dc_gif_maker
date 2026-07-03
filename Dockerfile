FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    DCM_DATA_DIR=/data

# force HTTPS mirrors: the local network's HTTP cache serves stale files
# (apt "Hash Sum mismatch"); also used by `playwright install --with-deps`
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' \
        /etc/apt/sources.list.d/debian.sources

# media toolchain + CJK/emoji fonts so SVG <text> renders correctly
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg gifsicle librsvg2-bin pngquant \
        fonts-noto-core fonts-noto-cjk fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# heavy dependency layers FIRST so src edits rebuild in seconds.
# keep this list in sync with pyproject [project.dependencies] + dev extra.
RUN pip install "fastapi>=0.115" "uvicorn[standard]>=0.30" \
        "python-multipart>=0.0.9" "playwright>=1.45" "pytest>=8"
RUN playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*

# the package itself (cheap layer)
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-deps .
COPY tests ./tests
COPY samples/original ./samples/original

EXPOSE 8000
VOLUME /data
CMD ["uvicorn", "dcmaker.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
