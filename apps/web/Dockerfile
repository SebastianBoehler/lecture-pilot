FROM node:22-slim AS build

WORKDIR /app
COPY package.json package-lock.json .npmrc ./
COPY apps/web/package.json apps/web/package.json
RUN npm ci

COPY apps/web apps/web
ARG LECTUREPILOT_COMMIT_SHA=development
ENV LECTUREPILOT_COMMIT_SHA=${LECTUREPILOT_COMMIT_SHA}
RUN npm run build --workspace apps/web

FROM nginx:1.30.3-alpine3.23
ARG LECTUREPILOT_COMMIT_SHA=development
LABEL org.opencontainers.image.revision=${LECTUREPILOT_COMMIT_SHA}
RUN apk upgrade --no-cache
COPY --from=build /app/apps/web/dist /usr/share/nginx/html
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
