# Frontend-Only Dockerfile (Vite/React)
FROM node:20 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .

# Pass the backend URL as an environment variable during build
# Railway will need VITE_API_URL set in the service variables
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# Serve the static files using 'serve'
FROM node:20-slim
WORKDIR /app
RUN npm install -g serve
COPY --from=builder /app/dist ./dist

# Expose port (Vite typically builds to /dist)
EXPOSE 3000

# Start command
CMD ["serve", "-s", "dist", "-l", "3000"]
