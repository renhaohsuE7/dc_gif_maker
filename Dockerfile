# gifsicle pinned at 1.95: Debian trixie's 1.96 --lossy is ineffective on
# flat-colour anime frames (0.06% vs 43% saving on the same input — see
# docs/references/2026-07-03-gifsicle-196-lossy-regression.md)
FROM python:3.12-slim AS gifsicle-build
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' \
        /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y --no-install-recommends \
        build-essential wget ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN wget -qO- https://www.lcdf.org/gifsicle/gifsicle-1.95.tar.gz | tar xz \
    && cd gifsicle-1.95 \
    && ./configure --disable-gifview --disable-gifdiff \
    && make -j"$(nproc)" && make install

# gh CLI (release automation) fetched here as a static binary — reuses this
# stage's wget, and only the ~30MB binary is copied into the final image
# (no third-party apt source, no stale-mirror hash-sum risk).
ARG GH_VERSION=2.96.0
RUN arch="$(dpkg --print-architecture)" \
    && wget -qO- "https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_linux_${arch}.tar.gz" \
        | tar xz -C /tmp \
    && mv "/tmp/gh_${GH_VERSION}_linux_${arch}/bin/gh" /usr/local/bin/gh \
    && rm -rf /tmp/gh_*

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

# /usr/local/bin precedes /usr/bin, so the pinned 1.95 shadows apt's 1.96
COPY --from=gifsicle-build /usr/local/bin/gifsicle /usr/local/bin/gifsicle
# gh CLI for scripts/release.sh (release automation; not used by the web server)
COPY --from=gifsicle-build /usr/local/bin/gh /usr/local/bin/gh

EXPOSE 8000
VOLUME /data
CMD ["uvicorn", "dcmaker.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
