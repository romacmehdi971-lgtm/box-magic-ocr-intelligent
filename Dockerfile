FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# System deps:
# - poppler-utils: pdftotext/pdfinfo for PDF text extraction (pdfplumber/pdfminer may still work, but this helps)
# - tesseract-ocr + lang packs: OCR fallback for scanned PDFs/images
# - libgl1/libglib2.0-0: common deps for image libs (safe defaults)
RUN apt-get update && apt-get install -y --no-install-recommends     poppler-utils     tesseract-ocr     tesseract-ocr-fra     tesseract-ocr-eng     ghostscript     libgl1     libglib2.0-0  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

EXPOSE 8080

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
