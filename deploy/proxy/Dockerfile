FROM node:22-alpine AS frontend-build

WORKDIR /frontend
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM caddy:2-alpine
COPY --from=frontend-build /frontend/dist /srv
