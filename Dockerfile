FROM alpine:3.7

RUN apk add --no-cache python3 cdrkit

RUN mkdir -p /app

RUN pip3 install --no-cache-dir pyvmomi==6.7.0.2018.9 pyyaml

WORKDIR /app

USER nobody

ENTRYPOINT  [ "python3" ]
