# One image for the backend — runs the FastAPI app with uvicorn.
# Works the same locally (docker compose) and anywhere you host a container.
# (If this later moves to AWS Lambda, wrap the app with Mangum — no separate image needed now.)
FROM python:3.12-slim

# tesseract-ocr: OCR fallback for scanned pages/drawings during ingestion (pytesseract shells
# out to this binary). tesseract-ocr-ell/-eng: Greek + English trained data, matching OCR_LANGS.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-ell tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .

COPY app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
