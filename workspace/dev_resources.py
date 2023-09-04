from phi.docker.app.django import Django
from phi.docker.app.postgres import PostgresDb
from phi.docker.resource.image import DockerImage
from phi.docker.resource.group import DockerResourceGroup

from workspace.settings import ws_settings

#
# -*- Resources for the Development Environment
#

# -*- Dev application image
dev_image = DockerImage(
    name=f"{ws_settings.image_repo}/{ws_settings.ws_name}",
    tag=ws_settings.dev_env,
    enabled=ws_settings.build_images,
    path=str(ws_settings.ws_root),
    dockerfile="dev.Dockerfile",
    pull=ws_settings.force_pull_images,
    # Uncomment to push the dev image
    # push_image=ws_settings.push_images,
    skip_docker_cache=ws_settings.skip_image_cache,
)

# -*- Dev database running on port 5432:5432
dev_db = PostgresDb(
    name=f"{ws_settings.dev_key}-db",
    enabled=ws_settings.dev_db_enabled,
    db_user="app",
    db_password="app",
    db_schema="app",
)

# -*- Django running on port 8000
dev_django = Django(
    name=ws_settings.dev_key,
    enabled=ws_settings.dev_app_enabled,
    image=dev_image,
    command="python manage.py runserver 0.0.0.0:8000",
    debug_mode=True,
    mount_workspace=True,
    env_vars={
        "DEBUG": True,
        # Database configuration
        "DB_HOST": dev_db.get_db_host(),
        "DB_PORT": dev_db.get_db_port(),
        "DB_USER": dev_db.get_db_user(),
        "DB_PASS": dev_db.get_db_password(),
        "DB_SCHEMA": dev_db.get_db_schema(),
        # Migrate database on startup using python manage.py migrate in entrypoint.sh
        "MIGRATE_DB": ws_settings.dev_db_enabled,
        # Wait for database to be available before starting the application
        "WAIT_FOR_DB": ws_settings.dev_db_enabled,
    },
    use_cache=ws_settings.use_cache,
    # Read secrets from secrets/dev_app_secrets.yml
    secrets_file=ws_settings.ws_root.joinpath("workspace/secrets/dev_app_secrets.yml"),
)

# -*- DockerResourceGroup defining the dev docker resources
dev_docker_resources = DockerResourceGroup(
    env=ws_settings.dev_env,
    network=ws_settings.ws_name,
    apps=[dev_db, dev_django],
)
