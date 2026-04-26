FROM node:20-alpine AS deps
WORKDIR /app
COPY dashboard/package.json dashboard/package-lock.json ./
RUN npm ci --ignore-scripts

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
# Copy dashboard source and the shared types it imports via @shared alias
COPY dashboard/ ./dashboard/
COPY shared/ ./shared/
WORKDIR /app/dashboard
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
# Use npm start (no standalone output required)
COPY --from=builder /app/dashboard/.next ./.next
COPY --from=builder /app/dashboard/node_modules ./node_modules
COPY --from=builder /app/dashboard/package.json ./package.json
EXPOSE 3000
CMD ["npm", "start"]
