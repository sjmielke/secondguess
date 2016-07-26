#! /bin/env bash

      SETS="syscomb dev domain test uroom devdomain domain2 eval"
SBMTSYSTEM="isi-sbmt-v5-uzb"
   DATADIR="/home/nlg-05/sjm_445/uyghur/on_top_of/$SBMTSYSTEM"
PYGUESSDIR="/home/nlg-05/sjm_445/pyguess"
       LEX="guessing_input_lexicon.v13"

set -e
cd $DATADIR

cat > pyguess.config <<- EOT
{
	"auto-generated-by": "runall.sh",
	"set-placeholder": "<<SET>>",
	"global-files": {
		"lexicon":         "$DATADIR/staticdata/${LEX}",
		"allmatches":      "$DATADIR/data/${LEX}.fullmorfmatches",
		"train-target":    "$DATADIR/staticdata/train.target.agile",
		"leidos-unigrams": "$DATADIR/staticdata/leidos_unigrams",
		"grammar":         "$DATADIR/staticdata/grammar.uig-v04.txt",
		"pertainyms":      "$DATADIR/staticdata/english.pertainyms.txt"
	},
	"set-files": {
		"oovfile":     "$DATADIR/data/<<SET>>.sbmt.oov",
		"catmorffile": "$DATADIR/data/<<SET>>.sbmt.oov.catmorf",
		"1best-out":   "$DATADIR/data/<<SET>>.sbmt.oov.guesses.1best.hyp",
		"nbest-out":   "$DATADIR/data/<<SET>>.sbmt.oov.guesses.nbest.json"
	},
	"server-files": {
		"morfmodel": "$DATADIR/staticdata/binary-baseline-model"
	},
	"scoring-weights": {
		"unmatchedpartweight":   1.0,
		"perfectmatchweight":    1.0,
		"oovcoverageweight":     0.9,
		"sourcelexrestweight":   1.0,
		"sourcepartcountweight": 0.3,
		"trainingcountweight":   0.5,
		"leidosfrequencyweight": 0.9,
		"lengthratioweight":     0.4,
		"resultwordcountweight": 5.0,
		"englishcopyboost":      50.0,
		"deletionscore":        -10.0,
		"copyscore":            -5.0
	}
}
EOT

source /usr/usc/python/3.5.1/setup.sh

if [ -n "${PBS_NODEFILE}" ]; then
	hosts1=$(mktemp)
	hostsn=$(mktemp)
	uniq ${PBS_NODEFILE} > $hosts1
	cat $hosts1 $hosts1 $hosts1 $hosts1 > $hostsn
	SCOOP_HOSTS="--host $(cat $hostsn) -n $(cat $hostsn | wc -l)"
	rm $hosts1 $hostsn
fi

wait-for-file ()
{
	while [ ! -s $1 ]; do
		sleep 10
	done
}

############################################################
#  Generate PHRASEparts and match them against dictionary  #
############################################################

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
	python3 $PYGUESSDIR/guess_phrases.py ${set} >> data/${LEX}.all.matchable.phraseparts
done

# Match all phraseparts against dictionary
LC_COLLATE='UTF-8' sort -u data/${LEX}.all.matchable.phraseparts | \
	python3 -m scoop -vv $(echo -n ${SCOOP_HOSTS}) $PYGUESSDIR/guess_matching.py
# writes into "allmatches" file

# Clean up the mess
rm -f data/${LEX}.all.matchable.phraseparts


################################################
#  Score / guess all OOVs using these matches  #
################################################

echo -n "Starting actual guessing at: "
date

# Now do the actual guessing for all sets
for set in $SETS; do
	# Do the heavy guesswork!
	python3 -m scoop -vv $(echo -n ${SCOOP_HOSTS}) $PYGUESSDIR/thirdeye.py mode_batch ${set}

	# Now restitch them into sbmt output
	python3 $PYGUESSDIR/tools/rejoin_oovs.py\
		inputdata/${set}.sbmt.align\
		data/${set}.sbmt.oov.guesses.1best.hyp\
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
	python3 $PYGUESSDIR/tools/rejoin_oovs.py\
		inputdata/${set}.sbmt.align\
		data/${set}.sbmt.oov\
		data/${set}.sbmt.unguessed.tok

	detok data/${set}.sbmt.unguessed.tok

	# Calculate BLEU scores
	reffile=/home/nlg-02/pust/elisa-trial/il3-eng-eval-2016-07-06/data/$set.target.orig
	if [ -s $reffile ]; then
		date > data/${set}.bleu_results.txt
		for lc in 0 1; do
			echo "LC: $lc" >> data/${set}.bleu_results.txt
			
			for f in data/$set.sbmt.unguessed.detok data/$set.sbmt.guessed.detok; do
				/home/nlg-02/data07/bin/bleu.pl -i $f -if xline -metric bleuNistVersion -lc $lc $reffile >> data/${set}.bleu_results.txt
			done
		done
	else
		echo "No BLEU calculatable, since $reffile doesn't exist." > data/${set}.bleu_results.txt
	fi
done
