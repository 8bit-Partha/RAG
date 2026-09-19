FROM python:3.11-slim

WORKDIR /app

# System deps needed for pypdf and sentence-transformers' tokenizers
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Build the index at image build time so the container starts ready to
# serve queries immediately. Requires ANTHROPIC_API_KEY only if you also
# pass --contextual; the base build (ingestion/chunking/embedding) does
# not need an API key.
RUN python -m src.pipeline --build

EXPOSE 8501

CMD ["streamlit", "run", "app/streamlit_app.py", "--server.address=0.0.0.0"]
