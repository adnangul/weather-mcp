# Official Python image (rebuilt regularly; good CVE posture). uv copied from Astral distroless — see:
# https://docs.astral.sh/uv/guides/integration/docker/#installing-uv
FROM python:3.13-slim-bookworm

# Pin uv image tag (not :latest) for reproducible builds; bump when you need newer uv.
COPY --from=ghcr.io/astral-sh/uv:0.11.7 /uv /uvx /bin/

# OS upgrades (OpenSSL/libssl, etc.) for distro CVEs such as CVE-2026-31789 on Debian bookworm.
USER root
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get upgrade -y --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock weather.py ./
RUN uv sync --frozen --no-dev

RUN useradd --create-home --uid 1000 app \
    && chown -R app:app /app
USER app

EXPOSE 8080
CMD ["uv", "run", "python", "weather.py"]
