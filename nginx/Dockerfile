FROM nginx:1.25.2-alpine

RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d

# To expose files from a Dockerfile to a data volume
# the Amazon ECS data plane looks for a VOLUME directive.
# If the absolute path that's specified in the VOLUME directive
# is the same as the containerPath that's specified in the task definition,
# the data in the VOLUME directive path is copied to the data volume.
# https://docs.aws.amazon.com/AmazonECS/latest/developerguide/bind-mounts.html
RUN mkdir -p /usr/local/app
VOLUME ["/usr/local/app"]

EXPOSE 80
