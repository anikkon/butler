#!/usr/bin/env bash
workingDir="/data/db/gts/"
dbDir="$workingDir/db"
logDir="$workingDir/log"
logName="mongodb.log"
host='localhost'

# create dirs
mkdir -p "$dbDir" "$logDir"
# install dependencies
cat requirements.txt | xargs -n 1 pip3 install
# start mongod
res=$(mongod --config mongo.config.yaml --dbpath "$dbDir" --logpath "$logDir/$logName")
echo "$res"
if [[ ${res} = *"ERROR"* ]]; then
    exit 1
fi
# wait for the mongod to exit
sleep 2
# setup script
python3 ./src/setup.py "$@"
# shut down mongod
mongod --config mongo.config.yaml --dbpath "$dbDir" --shutdown

echo Done!

