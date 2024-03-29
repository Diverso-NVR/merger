FROM python:3.8

ENV TZ=Europe/Moscow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN apt -y update && apt -y install ffmpeg libpq-dev postgresql postgresql-contrib

COPY ./merger /merger
COPY ./requirements.txt /

RUN pip3 install -r requirements.txt
RUN mkdir /root/vids
RUN mkdir /var/log/merger

CMD ["python", "/merger/app.py"]
