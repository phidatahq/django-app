from pathlib import Path

from phi.workspace.settings import WorkspaceSettings

#
# -*- Define workspace settings using a WorkspaceSettings object
# these values can also be set using environment variables or a .env file
#
ws_settings = WorkspaceSettings(
    # Workspace name: used for naming cloud resources
    ws_name="django",
    # Path to the workspace root
    ws_root=Path(__file__).parent.parent.resolve(),
    # -*- Dev settings
    dev_env="dev",
    # -*- Dev Apps
    dev_app_enabled=True,
    dev_db_enabled=True,
    # -*- Production settings
    prd_env="prd",
    # -*- Production Apps
    prd_app_enabled=True,
    prd_db_enabled=True,
    # -*- AWS settings
    # Region for AWS resources
    aws_region="us-east-2",
    # Availability Zones for AWS resources
    aws_az1="us-east-2a",
    aws_az2="us-east-2b",
    # Subnet IDs for AWS resources
    # subnet_ids=["subnet-xyz", "subnet-xyz"],
    # -*- Image Settings
    # Repository for images (for example, to use ECR use the following format)
    # image_repo="[ACCOUNT_ID].dkr.ecr.us-east-2.amazonaws.com",
    # Build images locally
    # build_images=True,
    # Push images after building
    # push_images=True,
)
