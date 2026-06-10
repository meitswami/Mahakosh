FROM node:22-alpine AS base

WORKDIR /app/frontend

FROM base AS development
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend .
EXPOSE 3000
CMD ["npm", "run", "dev"]

FROM base AS builder
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM base AS production
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=builder /app/frontend/.next/standalone ./
COPY --from=builder /app/frontend/.next/static ./.next/static
COPY --from=builder /app/frontend/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
