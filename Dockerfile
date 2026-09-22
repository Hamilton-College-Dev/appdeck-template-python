# syntax=docker/dockerfile:1

# ---------- Stage 1: install dependencies ----------
# pip and its build machinery live in this stage only. Nothing from here
# reaches the final image except the finished virtual environment.
FROM python:3.13-slim AS deps

WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# ---------- Stage 2: the image that actually runs ----------
FROM python:3.13-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

# A non-root user to run as. Nothing here needs root.
RUN useradd --create-home --uid 10001 appuser

WORKDIR /app

# Only what's needed to run: the finished virtual environment and the source.
# No pip cache, no compilers, no build headers.
COPY --from=deps --chown=appuser:appuser /opt/venv /opt/venv
COPY --chown=appuser:appuser app ./app

USER appuser

EXPOSE 8080

# 2 workers x 4 threads fits comfortably in 512 MB on a quarter of a CPU core.
# Exec form, so SIGTERM reaches gunicorn directly and shutdown stays clean.
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8080", \
     "--workers", "2", \
     "--threads", "4", \
     "--timeout", "30", \
     "--graceful-timeout", "20", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "app.main:application"]
