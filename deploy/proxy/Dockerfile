FROM node:22-alpine AS frontend-build

WORKDIR /frontend
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=frontend-build /frontend/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
