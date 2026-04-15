# ── Stage 1: Build React frontend ────────────────────────────────────────────
FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend

# Install dependencies first (cached layer)
COPY frontend/package*.json ./
RUN npm ci

# Build the production bundle
COPY frontend/ ./
RUN npm run build


# ── Stage 2: Python / Flask + built frontend ──────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source and scripts
COPY app.py generate_embeddings.py create_database.py ./

# Copy the React build output from stage 1
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Copy the pre-seeded database and generate embeddings during build.
# The embedding column + vectors are baked into the image so the
# container starts immediately without any runtime generation step.
COPY purdue_courses.db /app/data/purdue_courses.db
RUN DB_PATH=/app/data/purdue_courses.db python generate_embeddings.py

# Copy entrypoint
COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

VOLUME ["/app/data"]

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
