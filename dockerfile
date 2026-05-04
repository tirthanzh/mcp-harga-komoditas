FROM python:3.13.13-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

RUN chmod +x /app/runapp.sh

ENTRYPOINT ["/app/runapp.sh"]