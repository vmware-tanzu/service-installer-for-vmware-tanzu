#!/bin/bash
vercomp() {
    if [[ $1 == $2 ]]
    then
        echo "$1"
        return $1
    fi
    local IFS=.
    local i ver1=($1) ver2=($2)
    # fill empty fields in ver1 with zeros
    for ((i=${#ver1[@]}; i<${#ver2[@]}; i++))
    do
        ver1[i]=0
    done
    for ((i=0; i<${#ver1[@]}; i++))
    do
        if [[ -z ${ver2[i]} ]]
        then
            # fill empty fields in ver2 with zeros
            ver2[i]=0
        fi
        if ((10#${ver1[i]} > 10#${ver2[i]}))
        then
            echo "$1"
            return 1
        fi
        if ((10#${ver1[i]} < 10#${ver2[i]}))
        then
            echo "$2"
            return 2
        fi
    done
    echo "$1"
    return 0
}
#loop through the all version available in txt and return bigger one
ARRAY=(`cat $1`)
# if only 1 version is present
if [[ ${#ARRAY[@]} == 1 ]]
then
   echo ${ARRAY[0]}
   exit 0

fi
max="0.0"
for t in ${ARRAY[@]}; do
        max=$(vercomp $max $t)
done
echo $max > $1