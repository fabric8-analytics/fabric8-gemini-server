REGISTRY := quay.io
DEFAULT_TAG := latest

ifeq ($(TARGET),rhel)
  DOCKERFILE := Dockerfile
  REPOSITORY := openshiftio/rhel-fabric8-analytics-fabric8-gemini-server
else
  DOCKERFILE := Dockerfile
  REPOSITORY := openshiftio/fabric8-analytics-fabric8-gemini-server
endif

.PHONY: all docker-build fast-docker-build test get-image-name get-image-repository

all: fast-docker-build

docker-build:
	docker build --no-cache -t $(REGISTRY)/$(REPOSITORY):$(DEFAULT_TAG) -f $(DOCKERFILE) .

fast-docker-build:
	docker build -t $(REGISTRY)/$(REPOSITORY):$(DEFAULT_TAG) -f $(DOCKERFILE) .

test:
	./qa/runtests.sh

check-code-style:
	./qa/run-linter.sh

check-docs-style:
	./qa/check-docstyle.sh

get-image-name:
	@echo $(REGISTRY)/$(REPOSITORY):$(DEFAULT_TAG)

get-image-repository:
	@echo $(REPOSITORY)

get-push-registry:
	@echo $(REGISTRY)
