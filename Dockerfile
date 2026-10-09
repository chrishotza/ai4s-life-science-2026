FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml requirements.txt requirements-dev.txt requirements-lock-py311.txt requirements-dev-lock-py311.txt ./
COPY src ./src
COPY tests ./tests
COPY examples ./examples
COPY scripts ./scripts
COPY docs ./docs
COPY demo.py README.md ./

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-lock-py311.txt && \
    pip install --no-cache-dir -e . && \
    pip install --no-cache-dir -r requirements-dev-lock-py311.txt

CMD ["python", "demo.py"]
