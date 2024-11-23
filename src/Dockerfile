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

# Add Write access to .files
RUN chmod 777 /app/.files


# Set a standard system user
RUN useradd -m appuser

# Set the user to appuser
USER appuser

# Run the FastAPI web service using Chainlit and uvicorn
CMD ["chainlit", "run", "main.py", "--host", "0.0.0.0", "--port", "8000"]







# RUN apt-get update

# # Install Poetry
# # RUN curl -sSL https://install.python-poetry.org | python3 - && \
# #   ln -s /root/.local/bin/poetry /usr/local/bin/poetry
# WORKDIR /app

# # Upgrade pip
# RUN python -m pip install --upgrade pip

# RUN pip install poetry==1.8.4

# ENV VIRTUAL_ENV=/app/.venv \
#   # PATH="/app/.venv/bin:$PATH" \
#   # POETRY_HOME="/app/.venv/bin" \
#   # PATH="$POETRY_HOME:$PATH" \
#   POETRY_NO_INTERACTION=1 \
#   POETRY_VIRTUALENVS_IN_PROJECT=1 \
#   POETRY_VIRTUALENVS_CREATE=1 \
#   POETRY_CACHE_DIR=/tmp/poetry_cache \
#   HOST=${CHAINLIT_HOST} \
#   LISTEN_PORT=${CHAINLIT_PORT}

# COPY app/pyproject.toml /app/

# # Resolve Dependencies
# RUN poetry lock

# # Install Dependencies
# RUN poetry install --no-dev --no-root && rm -rf ${POETRY_CACHE_DIR}

# # Udevse an official Python runtime as a parent image
# # FROM public.ecr.aws/docker/library/python:3.9.20-slim-bookworm AS builder

# # Use a minimal Python image for the final stage
# FROM public.ecr.aws/docker/library/python:3.9.20-slim-bookworm AS runtime

# ENV VIRTUAL_ENV=/app/.venv \
#   PATH="/app/.venv/bin:$PATH"
  
# # Set the working directory in the container
# WORKDIR /app

# # Copy the current directory contents into the container
# COPY app /app

# # COPY VENV from Builder Image (Previous one)
# COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

# # Set a standard system user
# RUN useradd -m appuser

# # Set the user to appuser
# USER appuser

# EXPOSE ${CHAINLIT_PORT:-8000}

# # Run the FastAPI web service using Chainlit and uvicorn
# CMD ["poetry","run", "chainlit", "run", "main.py", "--host", "${CHAINLIT_HOST:-0.0.0.0}", "--port", "${CHAINLIT_PORT:-8000}"]