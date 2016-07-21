#! /bin/env bash
source /home/nlg-05/sjm_445/pyguess/runpreamble.sh

# This is what will come out of this phase:
echo -n "" > data/${LEX}.all.matchable.phraseparts

for set in $SETS; do
	# Get OOVs
	python3 $PYGUESSDIR/tools/extract_tokens.py\
		inputdata/${set}.sbmt.align\
		data/${set}.sbmt.{tsv,oov_with_pipes}

	# Replace pipes with slashes to avoid flatcat category confusion
	tr '|' '/' < data/${set}.sbmt.oov_with_pipes > data/${set}.sbmt.oov

	# Morphsplit them
	# ... but only do that heavy work, if necessary.
	if [ ! -s data/${set}.sbmt.oov.catmorf ]; then
		morfessor -l staticdata/binary-baseline-model -T data/${set}.sbmt.oov --output-format '{analysis} ' --output-newlines \
			| sed -r 's/^ +//;s/ +$//' \
			| sed 's/ /|STM /g;s/$/|STM/' \
			> data/${set}.sbmt.oov.catmorf
	fi
	
	# Generate the matchable phrases for that set
	python3 $PYGUESSDIR/guess_matching.py\
		mode1_genphrases\
		data/${set}.sbmt.oov\
		data/${set}.sbmt.oov.catmorf\
		>> data/${LEX}.all.matchable.phraseparts
done

# Only match unique OOV phrases
LC_COLLATE='UTF-8' sort -u data/${LEX}.all.matchable.phraseparts > data/${LEX}.uniq.matchable.phraseparts


# Do slow and painful dictionary matching
# Make sure no previous runs clutter (-f to ignore inexistence)
rm -f data/${LEX}.fullmorfmatches.batch*

# Generate TODOs / batches
NOOFBATCHES=$(cat data/${LEX}.uniq.matchable.phraseparts |\
	python3 $PYGUESSDIR/guess_matching.py\
		mode1_joinphrases_genbatches\
		300\
		data/${LEX}.fullmorfmatches)

# Do we even have new TODOs?
if [ $NOOFBATCHES -gt 0 ]; then
	# Submit many jobs
	for i in $(seq 1 $NOOFBATCHES); do
		cat > data/${LEX}.fullmorfmatches.batch.$i.sh <<- EOT
			cd $DATADIR
			source /usr/usc/python/3.5.1/setup.sh
			python3 $PYGUESSDIR/guess_matching.py \
				mode2\
				staticdata/${LEX}\
				data/${LEX}.fullmorfmatches.batch.$i
		EOT
		qsub -q isi -l walltime=100:00:00 -lnodes=1:quadcore -N match.$i.sh data/${LEX}.fullmorfmatches.batch.$i.sh
		rm data/${LEX}.fullmorfmatches.batch.$i.sh
	done

	# Wait for all jobs
	for f in $(eval echo data/${LEX}.fullmorfmatches.batch.{1..$NOOFBATCHES}.done); do
		wait-for-file $f
	done

	# Now join!
	python3 $PYGUESSDIR/guess_matching.py\
		mode3\
		$NOOFBATCHES\
		data/${LEX}.fullmorfmatches
fi

# Clean up the mess
rm -f data/${LEX}.fullmorfmatches.batch*
rm -f data/${LEX}.{all,uniq}.matchable.phraseparts

echo "Starting actual guessing at:"
date

# Now do the actual guessing for all sets in parallel
for set in $SETS; do
	cat > data/run_${set}.sh <<- EOT
		#! /bin/env bash
		source $PYGUESSDIR/runpreamble.sh
		set=${set}
		source $PYGUESSDIR/runset.sh
	EOT
	qsub -q isi -l walltime=100:00:00 -lnodes=1:quadcore data/run_${set}.sh
	rm data/run_${set}.sh
done
