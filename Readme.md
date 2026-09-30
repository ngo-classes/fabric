# Local FABRIC Environment

This repository builds a local JupyterLab environment for working with the
FABRIC testbed course notebooks.

## Build and configure

Run these commands from the repository root.

1. Build the Docker image:

   ```bash
   docker compose build --no-cache
   ```

   Docker Compose tags the resulting image as `linhbngo/fabric:local`. Feel free to customize this tag in `docker-compose.yml` to your DockerHub ID. 

2. Create the FABRIC environment file from the provided template:

   ```bash
   cp .docker/fabric_env.sh.template home/fabric/.fabric/fabric_rc
   ```

   Edit `home/fabric/.fabric/fabric_rc` and replace
   `__FABRIC_PROJECT_ID__` and `__FABRIC_BASTION_USERNAME__` with your FABRIC
   values. Place your current FABRIC token at
   `home/fabric/.fabric/id_token.json`.

3. Generate the slice (sliver) and bastion SSH key pairs:

    You can generate them locally:

   ```bash
   ssh-keygen -t rsa -b 3072 -N "" -f home/fabric/.ssh/slice_key
   ssh-keygen -t rsa -b 3072 -N "" -f home/fabric/.ssh/fabric-bastion-key
   ```
    
   Register `fabric-bastion-key.pub` with your FABRIC bastion account. The
   slice public key, `slice_key.pub`, is used when creating FABRIC slivers.

    **or, you can go online and generate the pairs via FABRIC Portal's tool and download the resulting files.**

## Launch

Start the container in the background:

```bash
docker compose up -d
```

Open the first CSC 468 notebook directly at:

<http://localhost:8888/lab/tree/csc468/01_intro/single.ipynb>

JupyterLab is configured without a local token or password, so only expose
port 8888 on a trusted machine.

Stop the environment with:

```bash
docker compose down
```

## Mounted directories

Docker Compose bind-mounts these host directories into `/home/fabric`:

- `csc468/` as `/home/fabric/csc468`
- `csc478/` as `/home/fabric/csc478`
- `home/fabric/.ssh/` as `/home/fabric/.ssh`
- `home/fabric/.fabric/` as `/home/fabric/.fabric`
- `home/fabric/workspace/` as `/home/fabric/workspace`

Changes made in these locations from JupyterLab or the container are written
back to the corresponding host directories and survive container recreation.
A bind mount replaces the image's contents at the same container path while
the container is running.

The `.gitignore` files in the runtime directories ignore additional generated
content, including credentials, tokens, private keys, and workspace files.
Only the placeholder `.gitignore` files (and the explicitly retained
entrypoint script) are intended to be tracked. Do not commit FABRIC
credentials or private keys.
