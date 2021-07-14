FROM registry.centos.org/centos/centos:7

RUN yum install -y epel-release &&\
    yum install -y gcc git python36-pip python36-requests httpd httpd-devel python36-devel &&\
    yum clean all

RUN python3 -m pip install --upgrade pip

COPY ./requirements.txt /
RUN pip3 install -r requirements.txt && rm requirements.txt

ADD scripts/entrypoint.sh /bin/entrypoint.sh
COPY ./src /src

RUN chmod 777 /bin/entrypoint.sh

ENTRYPOINT ["/bin/entrypoint.sh"]
