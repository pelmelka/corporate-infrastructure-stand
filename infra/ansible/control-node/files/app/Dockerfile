FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ARG APP_UID=1000
ARG APP_GID=1000

RUN groupadd --gid ${APP_GID} appuser \
    && useradd --uid ${APP_UID} --gid ${APP_GID} --home-dir /opt/app --shell /usr/sbin/nologin appuser

WORKDIR /opt/app

COPY requirements.txt /opt/app/requirements.txt
RUN pip install --no-cache-dir -r /opt/app/requirements.txt

COPY app.py /opt/app/app.py

RUN mkdir -p /var/log/app \
    && chown -R appuser:appuser /opt/app /var/log/app

USER appuser

EXPOSE 8080

CMD ["python", "/opt/app/app.py"]
