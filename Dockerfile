# Product Sentiment Crawler — run in container (free sources work without .env)
FROM python:3.12-slim

WORKDIR /app

# Copy project and install (so 'productreviews' entry point is available)
COPY requirements.txt pyproject.toml _version.py ./
COPY config.py run.py ./
COPY productreviews/ productreviews/
COPY sources/ sources/
COPY sentiment/ sentiment/
COPY insights/ insights/
COPY utils/ utils/
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir -e .

# Optional: mount .env at runtime for Reddit/Brave/SerpAPI
# docker run --rm -v $(pwd)/.env:/app/.env productreviews "Notion"
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["productreviews"]
CMD ["--help"]
