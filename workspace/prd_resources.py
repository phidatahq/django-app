from os import getenv

from phi.aws.app.django import Django
from phi.aws.resource.ec2.security_group import InboundRule, SecurityGroup
from phi.aws.resources import AwsResources
from phi.aws.resource.rds.db_instance import DbInstance
from phi.aws.resource.rds.db_subnet_group import DbSubnetGroup
from phi.aws.resource.reference import AwsReference
from phi.aws.resource.secret.manager import SecretsManager
from phi.docker.resources import DockerResources
from phi.docker.resource.image import DockerImage

from workspace.settings import ws_settings

#
# -*- Resources for the Production Environment
#
# Skip resource deletion when running `phi ws down` (set to True after initial deployment)
skip_delete: bool = False
# Save resource outputs to workspace/outputs
save_output: bool = True
# Create load balancer for the application
create_load_balancer: bool = True

# -*- Production images
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
    name=f"{ws_settings.image_repo}/{ws_settings.ws_name}-nginx",
    tag=ws_settings.prd_env,
    enabled=ws_settings.build_images,
    path=str(ws_settings.ws_root.joinpath("nginx")),
    platform="linux/amd64",
    pull=ws_settings.force_pull_images,
    push_image=ws_settings.push_images,
    skip_docker_cache=ws_settings.skip_image_cache,
)

# -*- Secrets for production application
prd_secret = SecretsManager(
    name=f"{ws_settings.prd_key}-secret",
    group="app",
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
    group="db",
    # Create secret from workspace/secrets/prd_db_secrets.yml
    secret_files=[ws_settings.ws_root.joinpath("workspace/secrets/prd_db_secrets.yml")],
    skip_delete=skip_delete,
    save_output=save_output,
)

# -*- Security Group for the load balancer
prd_lb_sg = SecurityGroup(
    name=f"{ws_settings.prd_key}-lb-security-group",
    enabled=create_load_balancer,
    group="app",
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
# -*- Security Group for the application
prd_sg = SecurityGroup(
    name=f"{ws_settings.prd_key}-security-group",
    enabled=ws_settings.prd_app_enabled,
    group="app",
    description="Security group for the production application",
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
    group="db",
    description="Security group for the production database",
    inbound_rules=[
        InboundRule(
            description="Allow traffic from the FastAPI server to the database",
            port=prd_db_port,
            source_security_group_id=AwsReference(prd_sg.get_security_group_id),
        ),
    ],
    depends_on=[prd_sg],
    skip_delete=skip_delete,
    save_output=save_output,
)

# -*- RDS Database Subnet Group
prd_db_subnet_group = DbSubnetGroup(
    name=f"{ws_settings.prd_key}-db-sg",
    enabled=ws_settings.prd_db_enabled,
    group="db",
    subnet_ids=ws_settings.subnet_ids,
    skip_delete=skip_delete,
    save_output=save_output,
)

# -*- RDS Database Instance
db_engine = "postgres"
prd_db = DbInstance(
    name=f"{ws_settings.prd_key}-db",
    enabled=ws_settings.prd_db_enabled,
    group="db",
    db_name="app",
    engine=db_engine,
    port=prd_db_port,
    engine_version="15.3",
    allocated_storage=64,
    # NOTE: For production, use a larger instance type.
    # Last checked price: $0.0650 hourly = ~$50 per month
    db_instance_class="db.t4g.medium",
    availability_zone=ws_settings.aws_az1,
    db_subnet_group=prd_db_subnet_group,
    enable_performance_insights=True,
    db_security_groups=[prd_db_sg],
    aws_secret=prd_db_secret,
    skip_delete=skip_delete,
    save_output=save_output,
    # Do not wait for the db to be deleted
    wait_for_delete=False,
)

# -*- Django running on ECS
launch_type = "FARGATE"
prd_django = Django(
    name=ws_settings.prd_key,
    enabled=ws_settings.prd_app_enabled,
    image=prd_app_image,
    command="gunicorn --workers 3 --bind 0.0.0.0:8000 --max-requests 1000 app.wsgi:application",
    # Enable Nginx to serve static files
    enable_nginx=True,
    nginx_image=prd_nginx_image,
    # Run Nginx on port 80
    nginx_container_port=80,
    # Run the Django app on port 8000
    port_number=8000,
    ecs_task_cpu="2048",
    ecs_task_memory="4096",
    ecs_service_count=1,
    aws_secrets=[prd_secret],
    subnets=ws_settings.subnet_ids,
    security_groups=[prd_sg],
    # To enable HTTPS, create an ACM certificate and add the ARN below:
    # load_balancer_enable_https=True,
    # load_balancer_certificate_arn="LOAD_BALANCER_CERTIFICATE_ARN",
    load_balancer_security_groups=[prd_lb_sg],
    create_load_balancer=create_load_balancer,
    health_check_path="/health",
    env_vars={
        "DEBUG": True,
        "RUNTIME_ENV": "prd",
        # Get the OpenAI API key from the local environment
        "OPENAI_API_KEY": getenv("OPENAI_API_KEY"),
        # Database configuration
        "DB_HOST": AwsReference(prd_db.get_db_endpoint),
        "DB_PORT": AwsReference(prd_db.get_db_port),
        "DB_USER": AwsReference(prd_db.get_master_username),
        "DB_PASS": AwsReference(prd_db.get_master_user_password),
        "DB_SCHEMA": AwsReference(prd_db.get_db_name),
        # Wait for database to be available before starting the application
        "WAIT_FOR_DB": True,
        # Migrate database on startup using python manage.py migrate in entrypoint.sh
        "MIGRATE_DB": True,
    },
    use_cache=ws_settings.use_cache,
    skip_delete=skip_delete,
    save_output=save_output,
    # Do not wait for the service to stabilize
    wait_for_create=False,
    # Do not wait for the service to be deleted
    wait_for_delete=False,
)

# -*- Production DockerResources
prd_docker_config = DockerResources(
    env=ws_settings.prd_env,
    network=ws_settings.ws_name,
    images=[prd_app_image, prd_nginx_image],
)

# -*- Production AwsResources
prd_aws_config = AwsResources(
    env=ws_settings.prd_env,
    apps=[prd_django],
    resources=[
        prd_lb_sg,
        prd_sg,
        prd_db_sg,
        prd_secret,
        prd_db_secret,
        prd_db_subnet_group,
        prd_db,
    ],
)
