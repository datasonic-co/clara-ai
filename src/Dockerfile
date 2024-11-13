# Use an official Python runtime as a parent image
# To do: optimize image
FROM public.ecr.aws/docker/library/python:3.9.20-slim-bookworm

# Set environment variables for Poetry
ENV POETRY_HOME="/opt/poetry"
ENV PATH="$POETRY_HOME/bin:$PATH"

# Set a standard system user
RUN useradd -m appuser



# Set the working directory in the container
WORKDIR /app

# Copy only requirements first for dependency caching
COPY app/pyproject.toml /app/
COPY app/poetry.lock /app/


# Copy the current directory contents into the container at /app
COPY app /app

# Upgrade pip
RUN python -m pip install --upgrade pip

# Install poetry
RUN python -m pip install poetry 

# Resolve (sub)Dependencies and lock them in lock file
RUN python -m poetry lock 

# Install Dependencies
RUN python -m poetry install --no-root --no-dev

# Install system dependencies and Poetry
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential \
#     curl \
#   && curl -sSL https://install.python-poetry.org | python - \
#   && poetry config virtualenvs.create false \
#   && poetry install --no-root --no-dev \
#   && apt-get purge -y --auto-remove build-essential \
#   && rm -rf /var/lib/apt/lists/*

# Set the user to appuser
USER appuser

# Run the FastAPI web service using uvicorn
CMD ["chainlit", "run","main.py","-h"]