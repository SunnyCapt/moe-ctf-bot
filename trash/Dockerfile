FROM python:3.7-alpine
COPY . .
VOLUME data:data
RUN pip install -r requirements.txt
CMD python bot.py