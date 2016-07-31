#! /bin/env bash

PYGUESSDIR="$(dirname "$(readlink -f "$0")")"

# This is where the heavy lifting ~happens~ is defined
source run.functions.sh

INFILE="$1"

MYTMPDIR="" # assume standard

main-singlefile "$INFILE" \
  "/home/nlg-05/sjm_445/uyghur/on_top_of/__staticdata" \
  "bash" \
  "$MYTMPDIR"
