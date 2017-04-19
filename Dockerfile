FROM alpine

RUN apk update
RUN apk add py-twisted
ADD simple_server.py /simple_server.py

CMD python simple_server.py tcp:2000
