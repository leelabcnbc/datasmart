#!/usr/bin/env bash
# script to start db

# defense against errors. from http://www.davidpashley.com/articles/writing-robust-shell-scripts/
set -o nounset
# set -o errexit  # can't be used since some command just has non zero return code.

# adapted from https://gist.github.com/ekristen/11254304
# ekristen/check_docker_container.sh
# Bash Script for Nagios to Check Status of Docker Container


if [ "$EUID" -ne 0 ]; then
    echo "Please run as root"
    exit 1
fi

# load in environment variables
. envs.sh
# make sure the dir exists
mkdir -p ${BACKUP_HOST_DIR}
# copy the setup script into it
cp setup_admin_script.js ${BACKUP_HOST_DIR}

RUNNING=$(docker inspect --format="{{ .State.Running }}" $CONTAINER 2> /dev/null)

if [ "$?" -eq 1 ]; then
    echo "UNKNOWN - ${CONTAINER} does not exist."
    # always try to remove the container first.
    if (docker volume ls -q | grep -w leelab-mongo-data); then
        docker volume rm ${DATA_CONTAINER}
    fi
    if (docker volume ls -q | grep -w leelab-mongo-data); then
        echo "cannot remove data volume ${DATA_CONTAINER}!"
        exit 1
    fi
    if !(docker volume create --name ${DATA_CONTAINER}); then
        echo "failed to create data volume ${DATA_CONTAINER}"
        exit 1
    fi

    # let's start it. two volumes. one for backup (actually here I only need it for transmitting init script),
    # another for putting actual data. Putting actual data in a separate volume means that I can stop this container,
    # start a temporary backup container connected to it, and then do the backup, and restart this container.
    if !(docker run --name ${CONTAINER} -v ${BACKUP_HOST_DIR}:${BACKUP_DOCKER_DIR} -v ${DATA_CONTAINER}:/data/db \
        -d -p ${HOST_PORT}:27017 \
        ${IMAGE_NAME} mongod --auth); then
        echo "failed to start docker!"
        exit 1
    fi
    echo "wait for some time for mongod to setup, so next line won't fail"
    sleep 10
    docker exec ${CONTAINER} bash -c "cd ${BACKUP_DOCKER_DIR} && echo ${BACKUP_DOCKER_DIR}  &&  mongo < setup_admin_script.js"
    echo "finished setup"
fi

if [ "$RUNNING" == "false" ]; then
    echo "CRITICAL - ${CONTAINER} is not running."
    # workaround for <https://github.com/docker/docker/issues/16816>
    service docker restart
    
    docker start ${CONTAINER}
else
    echo "${CONTAINER} is running".
fi
