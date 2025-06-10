# Use a standard Python base image. 'slim' is a good balance of size and functionality.
FROM python:3.11-slim

# Set the agent's primary working directory inside the container
WORKDIR /agent

# Copy the entire 'ultron' source and the requirements file
COPY ultron /agent/ultron
COPY requirements.txt /agent/
COPY setup.py /agent/
COPY MANIFEST.in /agent/

# Install Ultron and its dependencies in editable mode so it can be run as a module
# This also installs common tools the agent might use via the shell.
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    make \
    cmake \
    xxd \
    procps \
    file \
    binutils \
    gdb \
    strace \
    valgrind \
    nmap \
    netcat-traditional \
    socat \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -e .

# Create the agent's sandboxed workspace and cache directory
# The workspace is where user's target code will be mounted
# The cache directory is needed for ultron's internal caching
RUN mkdir /workspace && mkdir -p /root/.cache/ultron

# Set the entrypoint to run ultron via the Python module
ENTRYPOINT ["python", "-m", "ultron.main_cli"] 