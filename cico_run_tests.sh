#!/bin/bash

set -ex

. cico_setup.sh

# not needed for tests, but we can check that the image actually builds
build_image
push_image

chmod +x ./runtests.sh
cat ./runtests.sh
./runtests.sh

