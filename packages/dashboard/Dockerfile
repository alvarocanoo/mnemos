FROM node:22-bookworm-slim AS deps

WORKDIR /app
COPY packages/dashboard/package.json packages/dashboard/package.json
WORKDIR /app/packages/dashboard
RUN npm install --no-audit --no-fund


FROM node:22-bookworm-slim AS builder

WORKDIR /app
COPY --from=deps /app /app
COPY packages/dashboard packages/dashboard
WORKDIR /app/packages/dashboard
RUN npm run build


FROM node:22-bookworm-slim AS runtime

ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0

WORKDIR /app
COPY --from=builder /app/packages/dashboard/.next/standalone /app
COPY --from=builder /app/packages/dashboard/.next/static /app/packages/dashboard/.next/static
COPY --from=builder /app/packages/dashboard/public /app/packages/dashboard/public

EXPOSE 3000

HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=5 \
  CMD node -e "fetch('http://localhost:3000').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "packages/dashboard/server.js"]
