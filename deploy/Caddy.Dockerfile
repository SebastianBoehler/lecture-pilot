FROM caddy:2.11.4-builder-alpine AS builder

RUN xcaddy build v2.11.4 --output /usr/bin/caddy

FROM caddy:2.11.4-alpine

RUN apk upgrade --no-cache
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
