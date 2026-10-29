# syntax=docker/dockerfile:1

FROM node:22-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG VITE_USE_MOCKS=false
ARG VITE_API_URL=/api/v1
ARG VITE_ADMIN_URL=/admin/
ENV VITE_USE_MOCKS=$VITE_USE_MOCKS \
    VITE_API_URL=$VITE_API_URL \
    VITE_ADMIN_URL=$VITE_ADMIN_URL

RUN npm run build

FROM nginx:1.27-alpine AS runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD wget --spider --quiet http://127.0.0.1/ || exit 1
