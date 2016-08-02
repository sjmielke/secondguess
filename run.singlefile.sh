#! /bin/env bash

PYGUESSDIR="$(dirname "$(readlink -f "$0")")"

# This is where the heavy lifting ~happens~ is defined
source run.functions.sh

       INFILE="$1"
STATICDATADIR="$2"
          LEX="$3"

MYTMPDIR="" # assume standard

main-singlefile "$INFILE" \
  "${STATICDATADIR}" \
  "${LEX}" \
  bash \
  "$MYTMPDIR"
