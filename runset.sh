#! /bin/env bash
set -e
SETS="dev domain eval syscomb test uroom"
SBMTSYSTEM="isi-sbmt-v4b"
DATADIR="/home/nlg-05/sjm_445/uyghur/on_top_of/$SBMTSYSTEM"
PYGUESSDIR="/home/nlg-05/sjm_445/pyguess"
LINES_PER_BATCH=200
LEX="v09.guessing_input_lexicon"

cd $DATADIR
source /usr/usc/python/3.5.1/setup.sh

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
		${LINES_PER_BATCH}\
		data/${LEX}.fullmorfmatches)

# Do we even have new TODOs?
if [ $NOOFBATCHES -gt 0 ]; then
	# Submit many jobs
	for i in $(seq 1 $NOOFBATCHES); do
		echo "cd $DATADIR" > data/${LEX}.fullmorfmatches.batch.$i.sh
		echo "source /usr/usc/python/3.5.1/setup.sh" >> data/${LEX}.fullmorfmatches.batch.$i.sh
		echo "python3 $PYGUESSDIR/guess_matching.py mode2 staticdata/${LEX} data/${LEX}.fullmorfmatches.batch.$i" >> data/${LEX}.fullmorfmatches.batch.$i.sh
		qsub -q isi -l walltime=100:00:00 -lnodes=1:quadcore -N match.$i.sh data/${LEX}.fullmorfmatches.batch.$i.sh
		rm data/${LEX}.fullmorfmatches.batch.$i.sh
	done

	# Wait for all jobs
	wait-for-file ()
	{
		while [ ! -s $1 ]; do
			sleep 10
		done
	}
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

# Now do the actual guessing for all sets
for set in $SETS; do
	# Guess 'em all!
	python3 $PYGUESSDIR/thirdeye.py\
		data/${set}.sbmt.oov\
		nocheatref\
		data/${set}.sbmt.oov.catmorf\
		staticdata/${LEX}\
		staticdata/emptyfile\
		staticdata/train.target.agile\
		staticdata/leidos_unigrams\
		data/${LEX}.fullmorfmatches\
		data/${set}.sbmt.oov.trans_thirdeye\
		--unmatchedpartweight   1.0\
		--perfectmatchweight    1.0\
		--oovcoverageweight     0.9\
		--sourcelexrestweight   1.0\
		--sourcepartcountweight 0.3\
		--trainingcountweight   0.5\
		--leidosfrequencyweight 0.9\
		--lengthratioweight     0.4\
		--resultwordcountweight 5.0\
		--deletionscore        -10.0\
		--copyscore            -5.0

	# Now restitch them
	python3 $PYGUESSDIR/tools/rejoin_oovs.py\
		inputdata/${set}.sbmt.align\
		data/${set}.sbmt.oov.trans_thirdeye\
		data/${set}.sbmt.guessed.tok

	# Detokenize and stuff
	detok ()
	{
		$PYGUESSDIR/tools/agile_tokenizer/lw_detokenize.pl < $1 | /home/rcf-40/jonmay/projects/lorelei/dryrun/il3/firstcap.py > ${1%.tok}.detok
	}
	detok data/${set}.sbmt.guessed.tok



	# Prepare packages for upload
	~jonmay//LE/mt2/v4/scripts/packagesbmt.sh data/${set}.sbmt.guessed.detok staticdata/package/elisa.il3-eng.${set}.y1r1.*.xml.gz data/${SBMTSYSTEM}-guess.il3-eng.${set}.y1r1.v1.xml.gz;


	# Compare against pure SBMT output!
	# (my | -> / versoin, for fairness)
	python3 $PYGUESSDIR/tools/rejoin_oovs.py\
		inputdata/${set}.sbmt.align\
		data/${set}.sbmt.oov\
		data/${set}.sbmt.unguessed.tok

	detok data/${set}.sbmt.unguessed.tok

	date > data/${set}.bleu_results.txt

	for lc in 0 1; do
		reffile=/home/nlg-02/pust/elisa-trial/il3-eng-eval-2016-07-06/data/$set.target.orig
		for f in data/$set.sbmt.unguessed.detok data/$set.sbmt.guessed.detok; do
			/home/nlg-02/data07/bin/bleu.pl -i $f -if xline -metric bleuNistVersion -lc $lc $reffile >> data/${set}.bleu_results.txt
		done
	done
done
