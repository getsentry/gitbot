#!/bin/bash
# Use this script to turn the contents of a private key into one single string with \n after each new line
# The contents will be placed in your clipboard and is to be set as an env variable in Google Cloud Run.
while getopts ":k:" opt; do
    case ${opt} in
    k)
        PATH_TO_KEY=$OPTARG
        ;;
    *)
        echo "Invalid flag"
        exit 1
        ;;
    esac
done

if [ -z "$PATH_TO_KEY" ]; then
    echo >&2 "Call this script with -k path_to_private_key"
    exit 1
fi

content=""
while IFS="" read -r line || [ -n "$line" ]; do
    if [ "$content" == "" ]; then
        content="${line}"
    else
        content="${content}\n${line}"
    fi
done <"$PATH_TO_KEY"

echo -n "$content" | pbcopy
echo -e "\nThe contents of the key are now in your clipboard. Add it to your GCR app as an env variable."
