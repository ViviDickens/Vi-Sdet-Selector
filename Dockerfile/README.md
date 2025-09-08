# Docker Setup

This folder contains Dockerfiles for the project.

- **Dockerfile.api** → Builds the FastAPI backend container.
- **Dockerfile.playwright** → Builds the Playwright container for running SDK and tests.

Use the provided `docker-compose.yml` in the root folder to start both services together:

```bash
docker compose up --build