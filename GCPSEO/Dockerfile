FROM python:3.11-slim

# Install fonts for Japanese rendering in matplotlib/ReportLab
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project (inner repo dir) into image
COPY . /app

# Install pinned dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Cloud Run provides PORT env; default to 8080 locally
ENV PORT=8080 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0

EXPOSE 8080

CMD ["bash", "-lc", "streamlit run seo_aio_streamlit.py --server.port=${PORT:-8080} --server.address=0.0.0.0"]


