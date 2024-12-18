# The builder image, used to build the virtual environment
FROM public.ecr.aws/docker/library/python:3.9.20-slim-bookworm AS builder


RUN pip install pipx && \
    pipx install poetry

# Put Poetry on the path.
ENV PATH=/root/.local/bin:$PATH

WORKDIR /app

COPY app/pyproject.toml app/poetry.toml ./

# Resolve Dependencies
RUN poetry lock

RUN poetry install --no-dev --no-root

# Copy the current directory contents into the container
COPY app /app

# Create .files if not exist
RUN mkdir -p /app/.files


# Add Write access to .files
RUN chmod 777 /app/.files


# Set a standard system user
RUN useradd -m appuser

# Set the user to appuser
USER appuser

# Run the FastAPI web service using Chainlit and uvicorn
CMD ["chainlit", "run", "main.py", "--host", "0.0.0.0", "--port", "8000"]
