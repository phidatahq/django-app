from phidata.app.postgres import PostgresDb
from phidata.app.django import DjangoApp
from phidata.docker.config import DockerConfig
from phidata.docker.resource.image import DockerImage

from workspace.settings import ws_settings

#
# -*- Resources for the Development Environment
#

# -*- Development Image
dev_image = DockerImage(
    name=f"{ws_settings.image_repo}/{ws_settings.ws_name}",
    tag=ws_settings.dev_env,
    enabled=ws_settings.build_images,
    path=str(ws_settings.ws_root),
    dockerfile="dev.Dockerfile",
    pull=ws_settings.force_pull_images,
    push_image=ws_settings.push_images,
    skip_docker_cache=ws_settings.skip_image_cache,
)

# -*- Development Database running on port 9315
dev_db = PostgresDb(
    name=f"{ws_settings.dev_key}-db",
    enabled=ws_settings.dev_db_enabled,
    db_schema="dev",
    # Connect to this db on port 9315
    container_host_port=9315,
    # Read POSTGRES_USER and POSTGRES_PASSWORD from secrets/dev_db_secrets.yml
    secrets_file=ws_settings.ws_root.joinpath("workspace/secrets/dev_db_secrets.yml"),
)

# -*- DjangoApp running on port 8000
dev_django = DjangoApp(
    name=f"{ws_settings.dev_key}-app",
    enabled=ws_settings.dev_app_enabled,
    image=dev_image,
    command="python manage.py runserver 0.0.0.0:8000",
    env={
        "DEBUG": True,
        # Database configuration
        "DB_HOST": dev_db.get_db_host_docker(),
        "DB_PORT": dev_db.get_db_port_docker(),
        "DB_USER": dev_db.get_db_user(),
        "DB_PASS": dev_db.get_db_password(),
        "DB_SCHEMA": dev_db.get_db_schema(),
        # Migrate database on startup using python manage.py migrate in entrypoint.sh
        "MIGRATE_DB": ws_settings.dev_db_enabled,
        # Wait for database to be available before starting the application
        "WAIT_FOR_DB": ws_settings.dev_db_enabled,
    },
    mount_workspace=True,
    use_cache=ws_settings.use_cache,
    # Read secrets from secrets/dev_app_secrets.yml
    secrets_file=ws_settings.ws_root.joinpath("workspace/secrets/dev_app_secrets.yml"),
    # Uncomment to run in debug mode and keep the container after it exits
    # debug_mode=True,
)

# -*- DockerConfig defining the dev resources
dev_docker_config = DockerConfig(
    env=ws_settings.dev_env,
    network=ws_settings.ws_name,
    apps=[dev_db, dev_django],
)
