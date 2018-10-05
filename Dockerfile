FROM alpine:3.7

RUN adduser -u 8888 -s /bin/false -S -G users regular

RUN apk add --no-cache python3 cdrkit

RUN mkdir -p /app

RUN pip3 install --no-cache-dir pyvmomi==6.7.0.2018.9 pyyaml

WORKDIR /app

USER regular

ENTRYPOINT  [ "python3" ]
