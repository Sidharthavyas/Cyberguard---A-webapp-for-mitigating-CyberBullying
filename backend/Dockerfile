FROM python:3.11-slim

# Create non-root user (HF Spaces requirement)
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

WORKDIR /app

# Copy requirements
COPY --chown=user requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy all backend files
COPY --chown=user . /app

# Expose port 7860 (HF Spaces requirement)
EXPOSE 7860

# Start FastAPI on port 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
