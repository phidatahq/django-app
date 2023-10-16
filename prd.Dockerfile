FROM phidata/python:3.11.5

ARG USER=app
ARG APP_DIR=${USER_LOCAL_DIR}/${USER}
ENV APP_DIR=${APP_DIR}
# Add APP_DIR to PYTHONPATH
ENV PYTHONPATH="${APP_DIR}:${PYTHONPATH}"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create user and home directory
RUN groupadd -g 61000 ${USER} \
  && useradd -g 61000 -u 61000 -ms /bin/bash -d ${APP_DIR} ${USER}

WORKDIR ${APP_DIR}

# Update pip
RUN pip install --upgrade pip
# Copy pinned requirements
COPY requirements.txt .
# Install pinned requirements
RUN pip install -r requirements.txt

# Copy project files
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# To expose files from a Dockerfile to a data volume,
# the Amazon ECS data plane looks for a VOLUME directive.
# If the absolute path that's specified in the VOLUME directive
# is the same as the containerPath that's specified in the task definition,
# the data in the VOLUME directive path is copied to the data volume.
# https://docs.aws.amazon.com/AmazonECS/latest/developerguide/bind-mounts.html
VOLUME ["${APP_DIR}"]

COPY scripts /scripts
ENTRYPOINT ["/scripts/entrypoint.sh"]
CMD ["chill"]
