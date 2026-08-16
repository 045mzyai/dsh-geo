FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data

EXPOSE 8060

ENV PYTHONUNBUFFERED=1

# 单worker+多线程: APScheduler无多worker守卫，多worker会导致定时任务重复执行
# 并发靠threads承载(LLM调用为IO密集，线程足够)
CMD ["gunicorn", "--bind", "0.0.0.0:8060", "--workers", "1", "--threads", "8", "--timeout", "120", "app:app"]
