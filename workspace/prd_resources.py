from phidata.app.django import DjangoApp
from phidata.aws.config import AwsConfig
from phidata.aws.resource.group import (
    AwsResourceGroup,
    DbInstance,
    DbSubnetGroup,
    SecretsManager,
    SecurityGroup,
    InboundRule,
)
from phidata.docker.config import DockerConfig, DockerImage
from phidata.resource.reference import AwsReference

from workspace.settings import ws_settings

#
# -*- Resources for the Production Environment
#
# Skip resource deletion when running `phi ws down`
skip_delete: bool = False
# Save resource outputs to workspace/outputs
save_output: bool = True
# Create load balancer for the application
create_load_balancer: bool = True

# -*- Production Images
prd_app_image = DockerImage(
    name=f"{ws_settings.image_repo}/{ws_settings.ws_name}",
    tag=ws_settings.prd_env,
    enabled=ws_settings.build_images,
    path=str(ws_settings.ws_root),
    dockerfile="prd.Dockerfile",
    platform="linux/amd64",
    pull=ws_settings.force_pull_images,
    push_image=ws_settings.push_images,
    skip_docker_cache=ws_settings.skip_image_cache,
)
prd_nginx_image = DockerImage(
    name=f"{ws_settings.image_repo}/django-nginx",
    tag=ws_settings.prd_env,
    enabled=ws_settings.build_images,
    path=str(ws_settings.ws_root.joinpath("nginx")),
    platform="linux/amd64",
    pull=ws_settings.force_pull_images,
    push_image=ws_settings.push_images,
    skip_docker_cache=ws_settings.skip_image_cache,
)

# -*- Secrets for production application
prd_app_secret = SecretsManager(
    name=f"{ws_settings.prd_key}-app-secret",
    # Create secret from workspace/secrets/prd_app_secrets.yml
    secret_files=[
        ws_settings.ws_root.joinpath("workspace/secrets/prd_app_secrets.yml")
    ],
    skip_delete=skip_delete,
    save_output=save_output,
)
# -*- Secrets for production database
prd_db_secret = SecretsManager(
    name=f"{ws_settings.prd_key}-db-secret",
    # Create secret from workspace/secrets/prd_db_secrets.yml
    secret_files=[ws_settings.ws_root.joinpath("workspace/secrets/prd_db_secrets.yml")],
    skip_delete=skip_delete,
    save_output=save_output,
)

# -*- Security Group for the load balancer
prd_lb_sg = SecurityGroup(
    name=f"{ws_settings.prd_key}-lb-security-group",
    enabled=create_load_balancer,
    description="Security group for the load balancer",
    inbound_rules=[
        InboundRule(
            description="Allow HTTP traffic from the internet",
            port=80,
            cidr_ip="0.0.0.0/0",
        ),
        InboundRule(
            description="Allow HTTPS traffic from the internet",
            port=443,
            cidr_ip="0.0.0.0/0",
        ),
    ],
    skip_delete=skip_delete,
    save_output=save_output,
)
# -*- Security Group for the api
prd_app_sg = SecurityGroup(
    name=f"{ws_settings.prd_key}-app-security-group",
    enabled=ws_settings.prd_app_enabled,
    description="Security group for the production api",
    inbound_rules=[
        InboundRule(
            description="Allow traffic from LB to the Django App",
            port=8000,
            source_security_group_id=AwsReference(prd_lb_sg.get_security_group_id),
        ),
        InboundRule(
            description="Allow traffic from LB to the Nginx proxy",
            port=80,
            source_security_group_id=AwsReference(prd_lb_sg.get_security_group_id),
        ),
    ],
    depends_on=[prd_lb_sg],
    skip_delete=skip_delete,
    save_output=save_output,
)
# -*- Security Group for the database
prd_db_port = 5432
prd_db_sg = SecurityGroup(
    name=f"{ws_settings.prd_key}-db-security-group",
    enabled=ws_settings.prd_app_enabled,
    description="Security group for the production database",
    inbound_rules=[
        InboundRule(
            description="Allow traffic from the FastAPI server to the database",
            port=prd_db_port,
            source_security_group_id=AwsReference(prd_app_sg.get_security_group_id),
        ),
    ],
    depends_on=[prd_app_sg],
    skip_delete=skip_delete,
    save_output=save_output,
)

# -*- RDS Database Subnet Group
prd_db_subnet_group = DbSubnetGroup(
    name=f"{ws_settings.prd_key}-db-sg",
    enabled=ws_settings.prd_db_enabled,
    subnet_ids=ws_settings.subnet_ids,
    skip_delete=skip_delete,
    save_output=save_output,
)

# -*- RDS Database Instance
db_engine = "postgres"
prd_db = DbInstance(
    name=f"{ws_settings.prd_key}-db",
    enabled=ws_settings.prd_db_enabled,
    db_name="prd",
    engine=db_engine,
    port=prd_db_port,
    engine_version="15.3",
    allocated_storage=64,
    # NOTE: For production, use a larger instance type.
    # Last checked price: $0.0320 per hour = ~$25 per month
    db_instance_class="db.t4g.small",
    availability_zone=ws_settings.aws_az1,
    db_subnet_group=prd_db_subnet_group,
    enable_performance_insights=True,
    db_security_groups=[prd_db_sg],
    aws_secret=prd_db_secret,
    # Uncomment to read secrets from secrets/prd_db_secrets.yml
    # secrets_file=ws_settings.ws_root.joinpath("workspace/secrets/prd_db_secrets.yml"),
    skip_delete=skip_delete,
    save_output=save_output,
)

# -*- DjangoApp running on ECS
launch_type = "FARGATE"
prd_django = DjangoApp(
    name=ws_settings.prd_key,
    enabled=ws_settings.prd_app_enabled,
    image=prd_app_image,
    command="gunicorn --workers 3 --bind 0.0.0.0:8000 --max-requests 1000 app.wsgi:application",
    # Enable nginx to serve static files
    enable_nginx=True,
    nginx_image=prd_nginx_image,
    ecs_task_cpu="1024",
    ecs_task_memory="2048",
    ecs_service_count=1,
    aws_subnets=ws_settings.subnet_ids,
    aws_secrets=[prd_app_secret],
    aws_security_groups=[prd_app_sg],
    load_balancer_security_groups=[prd_lb_sg],
    create_load_balancer=create_load_balancer,
    health_check_path="/health",
    env={
        "DEBUG": True,
        "RUNTIME_ENV": "prd",
        # Database configuration
        "DB_HOST": AwsReference(prd_db.get_db_endpoint),
        "DB_PORT": AwsReference(prd_db.get_db_port),
        "DB_USER": AwsReference(prd_db.get_master_username),
        "DB_PASS": AwsReference(prd_db.get_master_user_password),
        "DB_SCHEMA": AwsReference(prd_db.get_db_name),
        # Migrate database on startup using python manage.py migrate in entrypoint.sh
        "MIGRATE_DB": True,
        # Wait for database to be available before starting the application
        "WAIT_FOR_DB": True,
    },
    use_cache=ws_settings.use_cache,
    skip_delete=skip_delete,
    save_output=save_output,
    # Do not wait for the service to stabilize
    wait_for_creation=False,
    # Uncomment to read secrets from secrets/prd_app_secrets.yml
    # secrets_file=ws_settings.ws_root.joinpath("workspace/secrets/prd_app_secrets.yml"),
)

# -*- DockerConfig defining the prd resources
prd_docker_config = DockerConfig(
    env=ws_settings.prd_env,
    network=ws_settings.ws_name,
    images=[prd_app_image, prd_nginx_image],
)

# -*- AwsConfig defining the prd resources
prd_aws_config = AwsConfig(
    env=ws_settings.prd_env,
    apps=[prd_django],
    resources=AwsResourceGroup(
        db_subnet_groups=[prd_db_subnet_group],
        db_instances=[prd_db],
        secrets=[prd_app_secret, prd_db_secret],
        security_groups=[prd_lb_sg, prd_app_sg, prd_db_sg],
    ),
)
