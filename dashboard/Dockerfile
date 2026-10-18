FROM python:3.13-slim

WORKDIR /opt/lab-medicao
COPY requirements.txt /tmp/dashboard-requirements.txt
RUN pip install --no-cache-dir -r /tmp/dashboard-requirements.txt

EXPOSE 8501
CMD ["streamlit", "run", "dashboard/app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
