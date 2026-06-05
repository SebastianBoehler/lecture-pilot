FROM node:22-slim AS build

WORKDIR /app
COPY package.json .npmrc ./
COPY apps/web/package.json apps/web/package.json
RUN npm install

COPY apps/web apps/web
RUN npm run build --workspace apps/web

FROM nginx:1.27-alpine
COPY --from=build /app/apps/web/dist /usr/share/nginx/html
EXPOSE 80
