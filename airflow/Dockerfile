FROM apache/airflow:3.3.1-python3.12

COPY --chown=airflow:root requirements.txt /tmp/airflow-requirements.txt

RUN pip install --no-cache-dir -r /tmp/airflow-requirements.txt
