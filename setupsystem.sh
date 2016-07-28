shopt -s extglob

if [ -z $1 ]; then
	echo 'No SBMT SYSTEM DIRECTORY ($1) specified!'
	exit 1
fi
if [ -z $2 ]; then
	echo 'No SETS list ($2) specified!'
	exit 1
fi
if [ -z $3 ]; then
	echo 'No LEXICON ($3) specified!'
	exit 1
fi

syspath="$1"
SETS="$2"
LEXICON="$3"
REFDIR="$4"

sysname=$(basename $syspath)
PYGUESSDIR="$(dirname "$(readlink -f "$0")")"

echo "# System: $sysname"

if [ ! -d "$sysname" ]; then
	echo "1) Making new directories"

	mkdir -p "$sysname"
	cd "$sysname"

	mkdir data
	mkdir inputdata
	ln -s ../__staticdata staticdata
else
	echo "1) No need to make new directories."
	cd "$sysname"
fi

echo "2) Reading SBMT output into inputdata directory"

for set in $SETS; do
	if [ -s     "$(ls -1v $syspath/decode-dev-${set}.+([0-9])/nbest.raw 2>/dev/null    | tail -n 1)" ]; then
		cat  $(ls -1v $syspath/decode-dev-${set}.+([0-9])/nbest.raw                | tail -n 1) | /home/nlg-02/pust/nbest2json > inputdata/${set}.sbmt.align
		foundsets="$foundsets $set"
	elif [ -s   "$(ls -1v $syspath/decode-dev-${set}.+([0-9])/nbest.raw.gz 2>/dev/null | tail -n 1)" ]; then
		zcat $(ls -1v $syspath/decode-dev-${set}.+([0-9])/nbest.raw.gz             | tail -n 1) | /home/nlg-02/pust/nbest2json > inputdata/${set}.sbmt.align
		foundsets="$foundsets $set"
	else
		echo "  ...didn't find set »${set}«"
	fi
done

echo "3) Starting guessing job for these sets:$foundsets"

echo "$PYGUESSDIR/runsets.sh '$sysname' '$foundsets' '$LEXICON' '$REFDIR'" > guess.${sysname#isi-sbmt-}.sh
qsub -q isi -l walltime=10:00:00 -l nodes=20:quadcore:ppn=8 guess.${sysname#isi-sbmt-}.sh
rm guess.${sysname#isi-sbmt-}.sh

cd ..
