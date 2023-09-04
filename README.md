## Django App

This repo contains the code for running a Django App in 2 environments:

1. dev: A development env running on docker
2. prd: A production env running on AWS ECS

## Setup Workspace (for new users)

1. Clone the git repo

> from the `django-app` dir:

2. Create + activate a virtual env:

```sh
python3 -m venv appenv
source appenv/bin/activate
```

3. Install `phidata`:

```sh
pip install phidata
```

4. Setup workspace:

```sh
phi ws setup
```

5. Copy `workspace/example_secrets` to `workspace/secrets`:

```sh
cp -r workspace/example_secrets workspace/secrets
```

6. Optional: Create `.env` file:

```sh
cp example.env .env
```

## Run Django App locally using docker

The `workspace/dev_resources.py` file contains the code for the development resources. Install [docker desktop](https://www.docker.com/products/docker-desktop) and start the workspace using:

```sh
phi ws up dev:docker
```

Open [localhost:8000](http://localhost:8000) to view the Django server.

### Shut down workspace

Shut down resources using:

```sh
phi ws down
```
