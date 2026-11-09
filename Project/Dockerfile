# One image, two processes: the REST service (8081) and the dashboard (8080).
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY devkit/requirements.txt /tmp/devkit-requirements.txt
RUN pip install -r /tmp/devkit-requirements.txt

COPY . /app
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi \
 && python devkit/bootstrap_demo.py --all --small

EXPOSE 8080 8081
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8081/health')"
CMD ["sh", "-c", "python run_api_service.py & sleep 20 && streamlit run run_dashboard.py --server.port 8080 --server.address 0.0.0.0"]
