FROM python:3.11.15-trixie

ENV DEBIAN_FRONTEND=noninteractive
ENV PATH=/home/fabric/.local/bin:$PATH

RUN apt-get update && apt-get install -y --no-install-recommends \
    sudo \
    openssh-client \
    git \
    ansible \
    curl \
    ca-certificates \
    bash-completion \
    tini \
    gh \
    && rm -rf /var/lib/apt/lists/*

# Create fabric user with passwordless sudo
RUN useradd -m -s /bin/bash fabric && \
    echo "fabric ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/fabric && \
    chmod 0440 /etc/sudoers.d/fabric

# Bring in docker-side templates and optional token
COPY .docker/ /tmp/docker/
COPY requirements.txt /tmp/requirements.txt

RUN mkdir -p /home/fabric/ /app && \
    chown -R fabric:fabric /home/fabric /app /tmp/requirements.txt /tmp/docker && \
    cp /tmp/docker/entrypoint.sh /home/fabric/entrypoint.sh

USER fabric
WORKDIR /app

# Install Jupyter and project requirements as the fabric user
RUN python -m pip install --user --upgrade pip && \
    python -m pip install --user jupyter jupyterlab && \
    if [ -f /tmp/requirements.txt ]; then python -m pip install --user -r /tmp/requirements.txt; fi

RUN echo 'if [ -f "$HOME/.fabric/fabric_rc" ]; then . "$HOME/.fabric/fabric_rc"; fi' >> "$HOME/.bashrc"

EXPOSE 8888 3000 4000 5555

ENTRYPOINT ["/usr/bin/tini", "--"]

CMD ["bash", "-lc", ". \"$HOME/entrypoint.sh\""]