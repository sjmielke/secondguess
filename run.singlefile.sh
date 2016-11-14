#! /bin/env bash

PYGUESSDIR="$(dirname "$(readlink -f "$0")")"

# This is where the heavy lifting ~happens~ is defined
source $PYGUESSDIR/run.functions.sh

       INFILE="$(check-argument "run.singlefile.sh" "1" "$1" "INFILE")"
STATICDATADIR="$(check-argument "run.singlefile.sh" "2" "$2" "STATICDATADIR")"
          LEX="$(check-argument "run.singlefile.sh" "3" "$3" "LEX")"
       REFDIR="$(check-argument "run.singlefile.sh" "4" "$4" "REFDIR")"

MYTMPDIR="" # assume standard

main-singlefile "$INFILE" \
  "${STATICDATADIR}" \
  "${LEX}" \
  bash \
  bash \
  "$MYTMPDIR"
	"$REFDIR"
