# Stage 1: Build Angular app
FROM node:20-slim as builder
WORKDIR /app

# Copy package.json and patches first to utilize Docker's layer caching
COPY package.json package-lock.json .npmrc ./
COPY patches/ patches/

# Ensure SSR is disabled in Typescript config
COPY tsconfig.json tsconfig.app.json ./

# Install dependencies but allow esbuild to install its native modules
RUN npm install --include=optional

# Run the rollup native module patch manually
RUN node patches/fix-rollup-native.js

# Create node_modules symlink for any problematic dependencies
RUN mkdir -p /app/node_modules/lmdb && \
    ln -sf ../patches/mock-empty-modules.js /app/node_modules/lmdb/index.js

# Copy the rest of the app source
COPY . .

# Ensure the server files don't exist to prevent SSR-related errors
RUN if [ -f src/main.server.ts ]; then rm src/main.server.ts; fi
RUN if [ -f src/app/app.config.server.ts ]; then rm src/app/app.config.server.ts; fi 
RUN if [ -f src/app/app.routes.server.ts ]; then rm src/app/app.routes.server.ts; fi
RUN if [ -f src/server.ts ]; then rm src/server.ts; fi

# Build in production mode
# Set NODE_OPTIONS to avoid memory issues in container
ENV NODE_OPTIONS="--max-old-space-size=4096"
RUN npm run build -- --configuration production

# Stage 2: Serve with Nginx
FROM nginx:alpine
COPY --from=builder /app/dist/ui /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Add curl for healthcheck
RUN apk --no-cache add curl

# Configure healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:4200/ || exit 1

EXPOSE 4200
CMD ["nginx", "-g", "daemon off;"]