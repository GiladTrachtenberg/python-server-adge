FROM node:25-alpine AS deps

WORKDIR /app

RUN --mount=type=bind,source=package.json,target=package.json \
    --mount=type=bind,source=package-lock.json,target=package-lock.json \
    --mount=type=cache,target=/root/.npm \
    npm ci

FROM deps AS build

WORKDIR /app

COPY . .
COPY --from=deps /app/node_modules ./node_modules/

RUN npx vite build

FROM nginx:alpine AS runtime

COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

ENV API_UPSTREAM=localhost:8000

EXPOSE 80
