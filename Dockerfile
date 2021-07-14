FROM registry.access.redhat.com/ubi8/python-36:latest

LABEL name="fabric8-gemini-server" \
      description="bayesian Gemini Server" \
      git-url="https://github.com/fabric8-analytics/fabric8-gemini-server" \
      git-path="/" \
      target-file="Dockerfile" \
      app-license="GNU 3"

ENV LANG=en_US.UTF-8 PYTHONDONTWRITEBYTECODE=1 DB_CACHE_DIR="/db-cache"

RUN pip3 install --upgrade pip --no-cache-dir

COPY ./requirements.txt /
RUN pip3 install -r /requirements.txt --no-cache-dir
ADD scripts/entrypoint.sh /bin/entrypoint.sh
COPY ./src /src

ENTRYPOINT ["/bin/entrypoint.sh"]