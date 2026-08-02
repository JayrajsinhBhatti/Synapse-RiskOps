# =====================================================
# Synapse RiskOps - Frontend Dockerfile
# Multi-stage: Development + Production
# =====================================================

# ----- Stage 1: Development -----
FROM node:20-alpine AS development

WORKDIR /app

# Copy package files for dependency caching
COPY package.json package-lock.json* ./
RUN npm ci

# Copy source code
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Run Vite dev server with host binding for Docker
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ----- Stage 2: Build for Production -----
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

# ----- Stage 3: Production (Nginx) -----
FROM nginx:alpine AS production

# Copy built assets to Nginx
COPY --from=build /app/dist /usr/share/nginx/html

# Copy Nginx configuration
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
