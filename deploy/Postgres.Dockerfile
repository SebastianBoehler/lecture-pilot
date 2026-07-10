FROM postgres:16-alpine

RUN apk upgrade --no-cache \
    && apk add --no-cache su-exec \
    && rm /usr/local/bin/gosu \
    && sed -i 's/exec gosu postgres/exec su-exec postgres/' /usr/local/bin/docker-entrypoint.sh
