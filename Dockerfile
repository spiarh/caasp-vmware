FROM alpine:3.7

RUN apk add --no-cache python3 cdrkit

RUN mkdir -p /app

RUN pip3 install --no-cache-dir pyvmomi==6.7.0.2018.9 pyyaml PTable

WORKDIR /app

# uid=65534(nobody) gid=65534(nobody) groups=65534(nobody)
USER 65534

ENTRYPOINT  [ "python3" ]
