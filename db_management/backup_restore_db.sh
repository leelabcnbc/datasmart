#!/usr/bin/env bash
# script to backup/restore db

# defense against errors. from http://www.davidpashley.com/articles/writing-robust-shell-scripts/
set -o nounset
# set -o errexit  # can't be used since some command just has non zero return code.

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root"
    exit 1
fi

# load in environment variables
. envs.sh

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 BACKUP|RESTORE [BACKUP_FILE]"
    exit 1
fi

if [ "$1" == "BACKUP" ]; then
    if [ "$#" -ne 1 ]; then
        echo "syntax: $0 BACKUP"
        exit 1
    fi
    BACKUP_NAME=$(date --utc +%Y%m%d_%H%M%SZ).tar.gz
    EXEC_STRING="tar -czvf ${BACKUP_DOCKER_DIR}/${BACKUP_NAME} -C /data/db ."
elif [ "$1" == "RESTORE" ]; then
    if [ "$#" -ne 2 ]; then
        echo "syntax: $0 RESTORE BACKUP_FILE"
        exit 1
    fi
    BACKUP_NAME="$2"
    EXEC_STRING="rm -rf /data/db/* && tar -xzpvf ${BACKUP_DOCKER_DIR}/${BACKUP_NAME} -C /data/db ."
else
    echo "wrong syntax"
    exit 1
fi

# stop the container.
docker exec ${CONTAINER} mongod --shutdown
docker stop ${CONTAINER}  # double check. seems that sometimes after the previous command, the container is still running.

# check that indeed the container is stopped.
RUNNING=$(docker inspect --format="{{ .State.Running }}" $CONTAINER 2> /dev/null)
if [ "$?" -eq 1 ]; then
    echo "UNKNOWN - ${CONTAINER} does not exist."
    exit 1
fi

if [ "$RUNNING" == "true" ]; then
    echo "CRITICAL - ${CONTAINER} is still running."
    exit 1
else
    # start a transient container to do the work.
    echo "start backup of ${CONTAINER}"
    if !(docker run --rm -v ${BACKUP_HOST_DIR}:${BACKUP_DOCKER_DIR} -v ${DATA_CONTAINER}:/data/db \
        ${IMAGE_NAME} sh -c "${EXEC_STRING}"); then
        echo "failed to do backup!"
        exit 1
    fi
    echo "backup file ${BACKUP_NAME} at ${BACKUP_HOST_DIR}"
    echo "restart ${CONTAINER}"
# restart service first... see <https://github.com/docker/docker/issues/16816>
    #service docker restart
    # when running cron, the above line failed in Ubuntu 14.04. try this one instead.
    /sbin/restart docker
    docker start ${CONTAINER}
fi


