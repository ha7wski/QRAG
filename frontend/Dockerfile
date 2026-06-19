# Frontend image — Next.js 14 (standalone output).
# Multi-stage: install deps, build, then a slim runtime with only the standalone
# server bundle.
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:20-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# NEXT_PUBLIC_* is inlined at build time, so the backend URL must be set here
# (overridable via a build arg — see docker-compose.yml).
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

FROM node:20-alpine AS run
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
# Bind to all interfaces so the published port is reachable from the host.
ENV HOSTNAME=0.0.0.0
# `output: "standalone"` bundles server.js + a minimal node_modules.
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
