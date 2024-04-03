FROM python:3.9.6
WORKDIR /app

RUN apt-get update && apt-get -y install cron

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY python-cronjob.txt /etc/cron.d/cronjob
RUN chmod 0644 /etc/cron.d/cronjob
RUN crontab /etc/cron.d/cronjob


# commands to run your stuff here I think?
CMD ["python", "/app/src/scrape.py", ";", "cron", "-f"]

