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
    tmux \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p -m 755 /etc/apt/keyrings && \
    out=$(mktemp) && wget -nv -O$out https://cli.github.com/packages/githubcli-archive-keyring.gpg && \
    cat $out | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null && \
    chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg && \
    mkdir -p -m 755 /etc/apt/sources.list.d && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null && \
    apt update && \
    apt install gh -y && \
    rm -rf $out

# Create fabric user with passwordless sudo
RUN useradd -m -s /bin/bash fabric && \
    echo "fabric ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/fabric && \
    chmod 0440 /etc/sudoers.d/fabric

# Bring in docker-side templates and optional token
COPY .docker/ /tmp/docker/

RUN mkdir -p /home/fabric/ /app && \
    chown -R fabric:fabric /home/fabric /app /tmp/docker/requirements.txt /tmp/docker && \
    cp /tmp/docker/entrypoint.sh /home/fabric/entrypoint.sh

USER fabric
WORKDIR /home/fabric

# Install Jupyter and project requirements as the fabric user
RUN python -m pip install --user --upgrade pip && \
    python -m pip install --user jupyter jupyterlab && \
    if [ -f /tmp/docker/requirements.txt ]; then python -m pip install --user -r /tmp/docker/requirements.txt; fi

RUN echo 'if [ -f "$HOME/.fabric/fabric_rc" ]; then . "$HOME/.fabric/fabric_rc"; fi' >> "$HOME/.bashrc"

EXPOSE 8888 3000 4000 5555

ENTRYPOINT ["/usr/bin/tini", "--"]

CMD ["bash", "-lc", ". \"$HOME/entrypoint.sh\""]