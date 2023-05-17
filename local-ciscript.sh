#!/bin/bash

echo "Node js/Python should be installed to execute the commands"
echo "Sleeping for 10 seconds"
sleep 10

echo "Executing command for Spell Check"
npm install -g cspell 
cspell --config cspell.json
if [ $? -eq 0 ]; then
 echo "No error"
fi

echo "Sleeping for 10 seconds"
sleep 10
echo "Executing command for Orphaned Content"
/usr/bin/python3 tests/orphaned-content.py
if [ $? -eq 0 ]; then
 echo "No error"
fi

echo "Sleeping for 10 seconds"
sleep 10
echo "Executing command for Wrapped Links"
/usr/bin/python3 tests/wrapped-links.py
if [ $? -eq 0 ]; then
 echo "No error"
fi
