#!/bin/bash

cd ./cross-validation

FILES="./drives_list"

while IFS= read -r file
do
  [ -f "$f" ]
  echo "Processing $f file..."

  cat $f | sbp2json | jq -c "select(.msg_type==74 or .msg_type==522)"  > $f.json

  python3 ~/Documents/Tesla/Phase3/SWIF-177/env_classify.py $f.json
done < "$FILES"

# mv *.csv ../environment/csv/
# mv *.png ../environment/png/
# cp *.sbp ../environment/sbp/
# cp *.json ../environment/json/
#
# cd ..
