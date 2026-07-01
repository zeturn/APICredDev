FROM node:20-alpine AS build
WORKDIR /app

COPY package*.json ./
RUN npm ci --include=optional \
  && npm install --no-save @rolldown/binding-linux-x64-musl

COPY . .
ARG VITE_API_BASE_URL
ARG VITE_BASALTPASS_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_BASALTPASS_BASE_URL=${VITE_BASALTPASS_BASE_URL}
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
