FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd -m runner && chown -R runner /app
USER runner
ENTRYPOINT ["python", "-m", "assure"]
