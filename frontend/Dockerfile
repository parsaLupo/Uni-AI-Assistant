# Static production build of the React app.
# docs/09-deployment.md section 1 serves the built assets from the reverse
# proxy; docker-compose uses the Vite dev server instead, so this image is for
# the deployment phase and is not built during Phase 00.
FROM node:22-alpine AS build

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
