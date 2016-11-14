#! /bin/env bash

# Call this file in your guessing root directory,
# the script will create a subdirectory for the specified system.

PYGUESSDIR="$(dirname "$(readlink -f "$0")")"

# This is where the heavy lifting ~happens~ is defined
source $PYGUESSDIR/run.functions.sh

      syspath="$(check-argument "run.system.sh" "1" "$1" "SBMT SYSTEM DIRECTORY")"
         SETS="$(check-argument "run.system.sh" "2" "$2" "SETS list")"
STATICDATADIR="$(check-argument "run.system.sh" "3" "$(readlink -f "$3")" "STATICDATA dir")"
      LEXICON="$(check-argument "run.system.sh" "4" "$4" "LEXICON")"
       REFDIR="$5"

if [ -z "$REFDIR" ]; then
	echo 'No REFDIR ($5) specified, will skip BLEU calculation for all sets.' >&2
fi

# Full initial call for each system (has to survive everyting); used here at the bottom!
   CALL_SYSTEM="qsub -q isi -l walltime=30:00:00 -l nodes=1:quadcore:ppn=4"
# Call for matching the 100-line parts of all sets combined
CALL_MATCHPART="qsub -q isi -l walltime=15:00:00 -l nodes=1:quadcore:ppn=4"
# Call for scoring a set (including packaging, has to survive the following individual jobs)
      CALL_SET="qsub -q isi -l walltime=20:00:00 -l nodes=1:quadcore:ppn=4"
# Call for the 100-line parts of each set (scoring)
  CALL_SETPART="qsub -q isi -l walltime=15:00:00 -l nodes=1:quadcore:ppn=4"

# ---------------------------------------------------------------
# This is where the work starts!
# ---------------------------------------------------------------

sysname="$(basename $syspath)"
echo "# System: $sysname" >&2

if [ ! -d "$sysname" ]; then
	echo "1) Making new directories" >&2
	mkdir -p "$sysname"
	move-into-fresh-datadir ${sysname} ${STATICDATADIR}
else
	echo "1) No need to make new directories." >&2
	cd "$sysname"
fi

echo "2) Reading SBMT output into inputdata directory"

foundsets=""
for set in $SETS; do
	if [ -s "inputdata/${set}.sbmt.align" ]; then
		echo "  ...already read in set »${set}«." >&2
		foundsets="$foundsets $set"
	else
		shopt -s extglob # to do the +(0-9) stuff
		SET_UNCMPR="$(ls -1v $syspath/decode-*-${set}.+([0-9])/nbest.raw    2>/dev/null | tail -n 1)"
		SET_GZCMPR="$(ls -1v $syspath/decode-*-${set}.+([0-9])/nbest.raw.gz 2>/dev/null | tail -n 1)"
		if [ -s "$SET_UNCMPR" ]; then
			foundsets="$foundsets $(sbmtnbest2alignfile "${set}" "$SET_UNCMPR")"
		elif [ -s "$SET_GZCMPR" ]; then
			foundsets="$foundsets $(sbmtnbest2alignfile "${set}" <(zcat "$SET_GZCMPR"))"
		else
			echo "  ...didn't find set »${set}«!" >&2
		fi
	fi
done

echo "3) Starting guessing job for these sets:$foundsets" >&2

cat > "guess.${sysname#isi-sbmt-}.sh" <<- EOT
	PYGUESSDIR="$PYGUESSDIR"
	source "$PYGUESSDIR/run.functions.sh"
	main-manysets '$(pwd)' '$foundsets' '$LEXICON' '$CALL_MATCHPART' '$CALL_SET' '$CALL_SETPART' '$REFDIR'
EOT

$CALL_SYSTEM "guess.${sysname#isi-sbmt-}.sh" && rm "guess.${sysname#isi-sbmt-}.sh"

cd ..
