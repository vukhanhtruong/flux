FROM node:20-slim AS build

WORKDIR /app

COPY packages/web-ui/package*.json ./
RUN npm ci

COPY packages/web-ui .

ARG VITE_API_BASE_URL=http://localhost:8000
ARG VITE_USER_ID=demo-user
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_USER_ID=$VITE_USER_ID

RUN npm run build

FROM node:20-slim
WORKDIR /app
COPY --from=build /app/dist ./dist
COPY packages/web-ui/package*.json ./
RUN npm ci
EXPOSE 5173
CMD ["npx", "vite", "preview", "--host", "0.0.0.0", "--port", "5173"]
