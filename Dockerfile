# Use the full Ubuntu LTS image. It provides a standard, writable environment.
FROM ubuntu:22.04

# Define a build-time variable for extra packages.
ARG EXTRA_APT_PACKAGES=""

# Set the agent's primary working directory.
WORKDIR /agent

# Copy your Ultron project files into the container.
COPY ultron /agent/ultron
COPY requirements.txt /agent/
COPY setup.py /agent/
COPY MANIFEST.in /agent/

# Set DEBIAN_FRONTEND to noninteractive to prevent apt from asking questions.
ENV DEBIAN_FRONTEND=noninteractive

# --- Install System Dependencies and Python ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    # --- CRITICAL: Install Python and PIP ---
    python3.11 \
    python3-pip \
    python3-venv \
    # --- A minimal, sensible set of base tools ---
    build-essential \
    git \
    cmake \
    binutils \
    socat \
    curl \
    make \
    xxd \
    file \
    # --- Install any extra packages specified during build ---
    $EXTRA_APT_PACKAGES \
    # --- THE FIX IS HERE ---
    # Now, install Ultron using the newly installed pip, with an increased timeout.
    && python3 -m pip install --no-cache-dir --timeout=100 -e . \
    # -----------------------
    # Finally, clean up the apt cache to keep the image smaller
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create the workspace where the target code will be mounted.
RUN mkdir /workspace

# Set the entrypoint to run Ultron.
# We use python3 to be explicit, as 'python' might not be linked by default.
ENTRYPOINT ["python3", "-m", "ultron.main_cli"]