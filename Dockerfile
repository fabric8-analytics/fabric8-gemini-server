FROM registry.centos.org/centos/centos:7

ENV F8A_WORKER_VERSION=6503230
ENV F8A_AUTH_VERSION=fff8f49

RUN yum install -y epel-release &&\
    yum install -y gcc git python36-pip python36-requests httpd httpd-devel python36-devel &&\
    yum clean all

RUN python3 -m pip install --upgrade pip>=10.0.0

RUN pip3 install git+https://github.com/fabric8-analytics/fabric8-analytics-worker.git@${F8A_WORKER_VERSION}
RUN pip3 install git+https://github.com/fabric8-analytics/fabric8-analytics-auth.git@${F8A_AUTH_VERSION}

COPY ./requirements.txt /
RUN pip3 install -r requirements.txt && rm requirements.txt

ADD scripts/entrypoint.sh /bin/entrypoint.sh
COPY ./src /src

RUN chmod 777 /bin/entrypoint.sh

ENTRYPOINT ["/bin/entrypoint.sh"]
