#!/bin/bash

T="$(date +%s)"

#bail out on any error
set -o errexit

# Check if snapshot parameter is supplied and there are 2 parameters
if [ "$2" != "int" ] && [ "$2" != "prod" ] && [ "$2" != "demo" ]
then
  echo "Error: Please specify 1) snapshot directoy and 2) target."
  exit 1
fi

SNAPSHOTDIR=/var/www/vhosts/service-alti/private/snapshots/$1

cwd=$(pwd)

# Go into snapshot directory to run nose-tests
SNAPSHOTDIR_CODE=$SNAPSHOTDIR/alti/code/alti
cd $SNAPSHOTDIR_CODE

# Run nose tests with target cluster db
if [ -z $3 ] || [ $3 != "notests" ]
then
    if [ "$2" == "int" ]
    then
      echo "Running nose tests with integration cluster in $SNAPSHOTDIR"
      scripts/nose_run.sh -i
    fi

    if [ "$2" == "prod" ]
    then
      echo "Running nose tests with production cluster in $SNAPSHOTDIR"
      scripts/nose_run.sh -p
    fi
else
    echo "You have disabled nosetests!"
fi

# Deterimine which deploy configuration to use
if [ -z $4 ] || [ $4 != "from_current_directory" ]
then
  echo "Using snapshot deploy configuration"
  DEPLOYCONFIG=$SNAPSHOTDIR_CODE/deploy/deploy.cfg
else
  echo "Using local deploy configuration"
  DEPLOYCONFIG=deploy/deploy.cfg
fi

# Back to working directory for the deploy command
cd $cwd

sudo -u deploy deploy -r $DEPLOYCONFIG $2 $SNAPSHOTDIR

T="$(($(date +%s)-T))"

printf "Deploy time: %02d:%02d:%02d:%02d\n" "$((T/86400))" "$((T/3600%24))" "$((T/60%60))" "$((T%60))"

