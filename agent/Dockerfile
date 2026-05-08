FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent.py gpu_monitor.py resource_monitor.py container_tracker.py heartbeat.py ./

EXPOSE 9000

CMD ["uvicorn", "agent:app", "--host", "0.0.0.0", "--port", "9000"]
