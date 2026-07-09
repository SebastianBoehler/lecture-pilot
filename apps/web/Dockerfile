FROM node:22-slim AS build

WORKDIR /app
COPY package.json package-lock.json .npmrc ./
COPY apps/web/package.json apps/web/package.json
RUN npm ci

COPY apps/web apps/web
RUN npm run build --workspace apps/web

FROM nginx:1.27-alpine
COPY --from=build /app/apps/web/dist /usr/share/nginx/html
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
