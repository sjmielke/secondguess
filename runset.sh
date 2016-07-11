#! /bin/env bash
source /usr/usc/python/3.5.1/setup.sh

set -e

PYGUESSDIR=/home/nlg-05/sjm_445/pyguess
DATADIR=$(pwd)

set=$1

wait-for-file ()
{
	while [ ! -s $1 ]; do
		sleep 10
	done
}

# Get OOVs
python3 $PYGUESSDIR/tools/extract_tokens.py\
	inputdata/${set}.sbmt.align\
	data/${set}.sbmt.{tsv,oov_with_pipes}

# Replace pipes with slashes to avoid flatcat category confusion
tr '|' '/' < data/${set}.sbmt.oov_with_pipes > data/${set}.sbmt.oov

# Morphsplit them
# ... but only do that heavy work, if necessary.
if [ ! -f data/${set}.sbmt.oov.catmorf ]; then
	morfessor -L staticdata/baseline-model.gz -T data/${set}.sbmt.oov --output-format '{analysis} ' --output-newlines \
		| sed 's/^ +//;s/ +$//' \
		| sed 's/ /|STM /g;s/$/|STM/' \
		> data/${set}.sbmt.oov.catmorf
fi

# Do slow and painful dictionary matching
# ...but again, only if necessary!
if [ ! -f data/${set}.sbmt.oov.fullmorfmatches ]; then
	# Make sure no previous runs clutter (-f to ignore inexistence)
	rm -f data/${set}.sbmt.oov.fullmorfmatches.batch*
	
	# Generate TODOs / batches
	NOOFBATCHES=$(python3 $PYGUESSDIR/guess_matching.py\
		mode1\
		data/${set}.sbmt.oov\
		data/${set}.sbmt.oov.catmorf\
		150\
		data/${set}.sbmt.oov.fullmorfmatches)
	
	# Submit many jobs
	for i in $(seq 1 $NOOFBATCHES); do
		echo "cd $DATADIR" > data/${set}.sbmt.oov.fullmorfmatches.batch.$i.sh
		echo "source /usr/usc/python/3.5.1/setup.sh" >> data/${set}.sbmt.oov.fullmorfmatches.batch.$i.sh
		echo "python3 $PYGUESSDIR/guess_matching.py mode2 staticdata/lexicon.norm data/${set}.sbmt.oov.fullmorfmatches.batch.$i" >> data/${set}.sbmt.oov.fullmorfmatches.batch.$i.sh
		qsub -q isi -l walltime=100:00:00 -N match.$set.$i.sh data/${set}.sbmt.oov.fullmorfmatches.batch.$i.sh
		rm data/${set}.sbmt.oov.fullmorfmatches.batch.$i.sh
	done
	
	# Wait for all jobs
	for f in $(eval echo data/${set}.sbmt.oov.fullmorfmatches.batch.{1..$NOOFBATCHES}.done); do
		wait-for-file $f
	done

	
	# Now join!
	python3 $PYGUESSDIR/guess_matching.py\
		mode3\
		$NOOFBATCHES\
		data/${set}.sbmt.oov.fullmorfmatches
	
	# Clean up the mess
	rm data/${set}.sbmt.oov.fullmorfmatches.batch*
fi

# Guess 'em all!
python3 $PYGUESSDIR/thirdeye.py\
	data/${set}.sbmt.oov\
	data/${set}.sbmt.oov.catmorf\
	staticdata/lexicon.norm\
	staticdata/emptyfile\
	nocheatref\
	staticdata/train.target.agile\
	staticdata/leidos_unigrams\
	data/${set}.sbmt.oov.fullmorfmatches\
	data/${set}.sbmt.oov.trans_thirdeye\
	1.0 0.9 1.0 0.5 0.4 0.6 50000.0 0.2

# Now restitch them
python3 $PYGUESSDIR/tools/rejoin_oovs.py\
	inputdata/${set}.sbmt.align\
	data/${set}.sbmt.oov.trans_thirdeye\
	data/${set}.sbmt.guessed.tok

# Detokenize and stuff
$PYGUESSDIR/tools/agile_tokenizer/lw_detokenize.pl < data/${set}.sbmt.guessed.tok | /home/rcf-40/jonmay/projects/lorelei/dryrun/il3/firstcap.py > data/${set}.sbmt.guessed.detok



# Do the first-word-hack
sed 's/ .*//' data/${set}.sbmt.oov.trans_thirdeye > data/${set}.sbmt.oov.trans_thirdeye_firstword

python3 $PYGUESSDIR/tools/rejoin_oovs.py\
        inputdata/${set}.sbmt.align\
        data/${set}.sbmt.oov.trans_thirdeye_firstword\
        data/${set}.sbmt.guessed_firstword.tok

$PYGUESSDIR/tools/agile_tokenizer/lw_detokenize.pl < data/${set}.sbmt.guessed_firstword.tok | /home/rcf-40/jonmay/projects/lorelei/dryrun/il3/firstcap.py > data/${set}.sbmt.guessed_firstword.detok


# Prepare packages for upload
for suffix in '' _firstword; do
	~jonmay//LE/mt2/v4/scripts/packagesbmt.sh data/${set}.sbmt.guessed${suffix}.detok inputdata/package/elisa.il3.package.y1r1.*/elisa.il3-eng.${set}.y1r1.*.xml.gz data/isi-sbmt-vanilla-guess${suffix}.il3-eng.${set}.y1r1.v1.xml.gz;
done
