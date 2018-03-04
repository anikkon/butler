#!/usr/bin/env bash
workingDir="/data/db/gts/"
dbDir="$workingDir/db"
logDir="$workingDir/log"
logName="mongodb.log"
host='localhost'

usage="$(basename "$0") -d DATA_SOURCE -- script to make your life easier setting up environment for git_to_slack integration.
where:
    -h  show this help text
    -d  where to get user data from"

if [ $# -eq 0 ]
  then
    echo "No arguments supplied!"
    echo "$usage" >&2
    exit 1
fi

# resolve arguments
while getopts ':h:p:d:' option; do
  case "$option" in
    h) echo "$usage"
       exit
       ;;
    d) data_from=$OPTARG
       ;;
    :) printf "missing argument for -%s\n" "$OPTARG" >&2
       echo "$usage" >&2
       exit 1
       ;;
    \?) printf "illegal option: -%s\n" "$OPTARG" >&2
       echo "$usage" >&2
       exit 1
       ;;
  esac
done
shift $((OPTIND - 1))
if  [ -z ${data_from+x} ]
then echo "Parameter is missing!"; echo "$usage"; exit 1;
fi

# create dirs
mkdir -p "$dbDir" "$logDir"
# install dependencies
pip install -q -r requirements.txt --no-index
# start mongod
res=$(mongod --config mongo.config.yaml --dbpath "$dbDir" --logpath "$logDir/$logName")
echo "$res"
if [[ ${res} = *"ERROR"* ]]; then
    exit 1
fi
# wait for the mongod to exit
sleep 2
# setup script
python3 ./src/setup.py --dataFrom "$data_from"
# shut down mongod
mongod --config mongo.config.yaml --dbpath "$dbDir" --shutdown

echo Done!

