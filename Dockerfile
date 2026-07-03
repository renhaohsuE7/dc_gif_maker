FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    DCM_DATA_DIR=/data

# media toolchain + CJK/emoji fonts so SVG <text> renders correctly
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg gifsicle librsvg2-bin pngquant \
        fonts-noto-core fonts-noto-cjk fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# install python deps first for layer caching
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install .[dev]

# chromium for animated-SVG capture (--with-deps pulls its shared libs)
RUN playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*

COPY tests ./tests

EXPOSE 8000
VOLUME /data
CMD ["uvicorn", "dcmaker.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
