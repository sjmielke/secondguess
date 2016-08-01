#! /bin/env bash

set -e

# doesn't seem to work in torque call, so make sure it's defined before!
#PYGUESSDIR="$(dirname "$(readlink -f "$0")")"

# Source python3 on HPC
if [ -z "$(command -v python3)" ]; then
	if [ -s /usr/usc/python/3.5.1/setup.sh ]; then
		source /usr/usc/python/3.5.1/setup.sh
	else
		echo "No python3 found! Exiting." >&2
		exit 1
	fi
fi

main-manysets ()
{
	     DATADIR="$(check-argument "main-manysets" "1" "$1" "DATADIR")"
	        SETS="$(check-argument "main-manysets" "2" "$2" "SETS list")"
	         LEX="$(check-argument "main-manysets" "3" "$3" "LEXICON")"
	    CALL_SET="$(check-argument "main-manysets" "4" "$4" "CALL for SET")"
	CALL_SETPART="$(check-argument "main-manysets" "5" "$5" "CALL for SETPARTs")"
	      REFDIR="$6"
	
	if [ -z "$REFDIR" ]; then
		echo 'No reference directory for BLEU ($6) specified, skipping BLEU calculation.' >&2
	fi

	SBMTSYSTEM="$(basename $DATADIR)"

	PREVDIR="$(pwd)"
	cd $DATADIR

	write-pyguess-config "$DATADIR" "$LEX"

	# This is what will come out of this phase:
	echo -n "" > "data/${LEX}.all.matchable.phraseparts"

	for set in $SETS; do
		# Get OOVs
		python3 "$PYGUESSDIR/tools/extract_tokens.py"\
			"inputdata/${set}.sbmt.align"\
			"data/${set}.sbmt."{tsv,oov}
		
		oovlist2phraseparts ${set} >> "data/${LEX}.all.matchable.phraseparts"
	done
	
	# Match all phraseparts against dictionary
	LC_COLLATE='UTF-8' sort -u "data/${LEX}.all.matchable.phraseparts" | \
		python3 $(get-scoop-params 4) "$PYGUESSDIR/guess_matching.py"
	# writes into "allmatches" file

	# Clean up the mess
	rm -f "data/${LEX}.all.matchable.phraseparts"

	echo -n "Starting actual guessing at: " >&2
	date >&2

	# Now do the actual guessing for all sets
	for set in $SETS; do
		cat > "${set}.${SBMTSYSTEM#isi-sbmt-}.sh" <<- EOT
			PYGUESSDIR="$PYGUESSDIR"
			source "$PYGUESSDIR/run.functions.sh"
			cd "$DATADIR"
			
			guess-set "$set" "$CALL_SETPART" "noscoop"
			
			rejoin-and-detok "$set"
			
			if [ ! -z "$REFDIR" ]; then
				try-to-calc-bleu $set $REFDIR
			fi
			
			package-result $set $SBMTSYSTEM
		EOT
		
		$CALL_SET "${set}.${SBMTSYSTEM#isi-sbmt-}.sh" && rm "${set}.${SBMTSYSTEM#isi-sbmt-}.sh"
	done

	cd "$PREVDIR"
}

main-singlefile ()
{
	       INFILE="$(check-argument "main-singlefile" "1" "$1" "INFILE")"
	STATICDATADIR="$(check-argument "main-singlefile" "2" "$2" "STATICDATADIR")"
	 CALL_SETPART="$(check-argument "main-singlefile" "3" "$3" "CALL_SETPART")"
	
	if [ ! -z $4 ]; then
		TMPDIR="$4"
	fi
	
	PREVDIR="$(pwd)"
	DATADIR="$(mktemp -d)"
	move-into-fresh-datadir "$DATADIR" "$STATICDATADIR"

	write-pyguess-config "$DATADIR" "$LEX"

	SETFILE="$(mktemp -p data/ --suffix=.sbmt.oov)"
	set="${SETFILE%.sbmt.oov}"

	# Matching
	oovlist2phraseparts ${set} | \
		LC_COLLATE='UTF-8' sort -u | \
		python3 $(get-scoop-params 4) "$PYGUESSDIR/guess_matching.py"

	# Guessing
	guess-set "$set" "$CALL_SETPART" "noscoop"

	# Output moving
	cp "data/${set}.sbmt.oov.guesses.1best.hyp"  "$INFILE.guessed.1best.hyp"
	cp "data/${set}.sbmt.oov.guesses.nbest.json" "$INFILE.guessed.nbest.json"

	# Cleanup
	cd "$PREVDIR"
	rm -r "$DATADIR"
}

check-argument ()
{
	CALLERFUNC="$1"
	PARAMNR="$2"
	PARAM="$3"
	PARAMNAME="$4"
	
	if [ -z "${PARAM}" ]; then
		echo "${CALLERFUNC}: No ${PARAMNAME} (\$${PARAMNR}) specified!" >&2
		exit 1
	fi
	
	echo "$3"
}

sbmtnbest2alignfile ()
{
	      set="$(check-argument "sbmtnbest2alignfile" "1" "$1" "SET")"
	NBESTFILE="$(check-argument "sbmtnbest2alignfile" "2" "$2" "NBEST file")"
	
	/home/nlg-02/pust/nbest2json < ${NBESTFILE} > inputdata/${set}.sbmt.align
	echo "  ...read in set »${set}«." >&2
	
	echo "$set"
}

move-into-fresh-datadir ()
{
	      DATADIR="$(check-argument "move-into-fresh-datadir" "1" "$1" "DATADIR")"
	STATICDATADIR="$(check-argument "move-into-fresh-datadir" "2" "$2" "STATICDATADIR")"
	
	cd "${DATADIR}"
	mkdir data
	mkdir inputdata
	ln -s "${STATICDATADIR}" staticdata
}

write-pyguess-config ()
{
	DATADIR="$(check-argument "write-pyguess-config" "1" "$1" "DATADIR")"
	    LEX="$(check-argument "write-pyguess-config" "2" "$2" "LEXICON")"

	cat > pyguess.config <<- EOT
	{
		"auto-generated-with-params": "$@",
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
			"oovfile":     "$DATADIR/data/<<SET>>.sbmt.oov.nopipes",
			"catmorffile": "$DATADIR/data/<<SET>>.sbmt.oov.nopipes.catmorf",
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
			"resultwordcountweight": 2.0,
			"englishcopyboost":      50.0,
			"deletionscore":        -10.0,
			"copyscore":            -5.0,
			"targetlengthratio":     0.75
		}
	}
	EOT
}

get-scoop-params ()
{
	SCOOP_CORES_PER_NODE="$(check-argument "get-scoop-params" "1" "$1" "SCOOP_CORES_PER_NODE")"
	
	if [ "$SCOOP_CORES_PER_NODE" = "noscoop" ]; then
		return
	fi
	
	if [ -n "${PBS_NODEFILE}" ]; then
		hosts1=$(mktemp)
		hostsn=$(mktemp)
		uniq ${PBS_NODEFILE} > $hosts1
		for core in $(seq 1 ${SCOOP_CORES_PER_NODE}); do
			cat $hosts1 >> $hostsn
		done
		echo "-m scoop -vv --host $(cat $hostsn) -n $(cat $hostsn | wc -l)"
		rm $hosts1 $hostsn
	fi
}

wait-for-file ()
{
	while [ ! -s "$1" ]; do
		sleep 10
	done
}

oovlist2phraseparts ()
{
	set="$(check-argument "oovlist2phraseparts" "1" "$1" "SET")"
	ORIG_OOVLIST="data/${set}.sbmt.oov"
	
	# Replace pipes with slashes to avoid flatcat category confusion
	tr '|' '/' < $ORIG_OOVLIST > $ORIG_OOVLIST.nopipes
	
	# Morphsplit them
	# ... but only do that heavy work, if necessary.
	if [ ! -s $ORIG_OOVLIST.nopipes.catmorf ]; then
		morfessor -l staticdata/binary-baseline-model -T $ORIG_OOVLIST.nopipes --output-format '{analysis} ' --output-newlines \
			| sed -r 's/^ +//;s/ +$//' \
			| sed 's/ /|STM /g;s/$/|STM/' \
			> $ORIG_OOVLIST.nopipes.catmorf
	fi
	
	# Generate the matchable phrases for that set to stdout
	python3 $PYGUESSDIR/guess_phrases.py ${set}
}

split-set-prepend ()
{
	INFILE="$(basename "$1")"
	INDIR="$(dirname "$1")"
	
	rm -f "$INDIR/${INFILE}.split."*
	rm -f "$INDIR/"*"-${INFILE}"
	split -a 3 -l 200 "$INDIR/$INFILE" "$INDIR/${INFILE}.split."
	
	for f in "$INDIR/${INFILE}.split."*; do
		PARTFILE="$(basename "$f")"
		mv "$f" "$INDIR/${PARTFILE#${INFILE}.split.}-${INFILE}"
	done
}

guess-set ()
{
	         set="$(check-argument "guess-set" "1" "$1" "SET")"
	CALL_SETPART="$(check-argument "guess-set" "2" "$2" "CALL for SETPARTs")"
	 CORES_MATCH="$(check-argument "guess-set" "3" "$3" "#CORES for matching")"
	
	SBMTSYSTEM="$(basename "$(pwd)")"
	
	# Again, the idea is to create a new 'artificial' set for pyguess - just like in main-singlefile!
	
	split-set-prepend "data/${set}.sbmt.oov.nopipes"
	split-set-prepend "data/${set}.sbmt.oov.nopipes.catmorf"
	
	# Kick all jobs off
	
	for f in "data/"*"-${set}.sbmt.oov.nopipes"; do
		SETNAME="$f"
		SETNAME="${SETNAME%.sbmt.oov.nopipes}"
		SETNAME="${SETNAME#data/}"
		cat > "${SETNAME}.${SBMTSYSTEM#isi-sbmt-}.sh" <<- EOT
			PYGUESSDIR="$PYGUESSDIR"
			source "$PYGUESSDIR/run.functions.sh"
			cd "$(pwd)"
			
			python3 \$(get-scoop-params $CORES_MATCH) "$PYGUESSDIR/thirdeye.py" mode_batch "${SETNAME}"
		EOT
		$CALL_SETPART "${SETNAME}.${SBMTSYSTEM#isi-sbmt-}.sh" && rm "${SETNAME}.${SBMTSYSTEM#isi-sbmt-}.sh"
	done
	
	# Wait for them to finish
	
	for f in "data/"*"-${set}.sbmt.oov.nopipes"; do
		echo -n "Now waiting for "
		echo "${f%.nopipes}.guesses.1best.hyp"
		wait-for-file "${f%.nopipes}.guesses.1best.hyp"
	done
	
	sleep 5
	
	# Join all 1bests (screw the nbests for now)
	
	echo -n "" > "data/${set}.sbmt.oov.guesses.1best.hyp"
	for f in "data/"*"-${set}.sbmt.oov.guesses.1best.hyp"; do
		cat $f >> "data/${set}.sbmt.oov.guesses.1best.hyp"
	done
	
	# Clean up
	
	rm data/*"-${set}.sbmt.oov.nopipes"
	rm data/*"-${set}.sbmt.oov.nopipes.catmorf"
	rm data/*"-${set}.sbmt.oov.guesses.1best.hyp"
}

rejoin-and-detok ()
{
	set="$(check-argument "rejoin-and-detok" "1" "$1" "SET")"
	
	# Now restitch them into sbmt output
	python3 $PYGUESSDIR/tools/rejoin_oovs.py\
		inputdata/${set}.sbmt.align\
		data/${set}.sbmt.oov.guesses.1best.hyp\
		data/${set}.sbmt.guessed.tok

	# Compare against pure SBMT output!
	python3 $PYGUESSDIR/tools/rejoin_oovs.py\
		inputdata/${set}.sbmt.align\
		data/${set}.sbmt.oov\
		data/${set}.sbmt.unguessed.tok

	# Detokenize and stuff
	detok ()
	{
		< $1 $PYGUESSDIR/tools/agile_tokenizer/lw_detokenize.pl | $PYGUESSDIR/tools/firstcap.py > ${1%.tok}.detok
	}

	detok data/${set}.sbmt.guessed.tok
	detok data/${set}.sbmt.unguessed.tok
}

try-to-calc-bleu ()
{
	# CAUTION: only runs on HPC, since the bleu.pl path is hardcoded below!
	
	   set="$(check-argument "try-to-calc-bleu" "1" "$1" "SET")"
	REFDIR="$(check-argument "try-to-calc-bleu" "2" "$2" "REFDIR")"
	
	if [ ! -s "/home/nlg-02/data07/bin/bleu.pl" ]; then
		echo "bleu.pl wasn't found, likely we are not on HPC? Skipping BLEU calculation for set $set." >&2
		return
	fi
	
	# Calculate BLEU scores
	reffile=${REFDIR}/$set.target.orig
	if [ -s $reffile ]; then
		date >> data/${set}.bleu_results.txt
		for lc in 0 1; do
			echo "LC: $lc" >> data/${set}.bleu_results.txt
			
			for f in data/$set.sbmt.unguessed.detok data/${set}.sbmt.guessed.detok; do
				/home/nlg-02/data07/bin/bleu.pl -i $f -if xline -metric bleuNistVersion -lc $lc $reffile >> data/${set}.bleu_results.txt
			done
		done
	else
		echo "No BLEU calculatable, since $reffile doesn't exist." >> data/${set}.bleu_results.txt
	fi
}

package-result ()
{
	       set="$(check-argument "package-result" "1" "$1" "SET")"
	SBMTSYSTEM="$(check-argument "package-result" "2" "$2" "SBMTSYSTEM name")"
	
	if [ ! -s "/home/rcf-40/jonmay/LE/mt2/v4/scripts/packagesbmt.sh" ]; then
		echo "packagesbmt.sh wasn't found, likely we are not on HPC? Skipping packaging for set $set." >&2
		return
	fi
	
	ALLPACKS="$(ls -1 staticdata/package/elisa.*-eng.${set}.y1r1.*.xml.gz)"
	if [ $(echo "$ALLPACKS" | wc -l) -gt 1 ]; then
		echo "Too many target packs for set ${set}, can't determine language code. Not building ELISA package." >&2
		return
	fi
	LANGPAIR=${ALLPACKS#staticdata/package/elisa.}
	LANGPAIR=${LANGPAIR%.${set}.y1r1.*.xml.gz}
	
	~jonmay//LE/mt2/v4/scripts/packagesbmt.sh \
		data/${set}.sbmt.guessed.detok \
		staticdata/package/extracted/${set}.source.orig \
		staticdata/package/elisa.${LANGPAIR}.${set}.y1r1.*.xml.gz \
		data/${SBMTSYSTEM}-guess.${LANGPAIR}.${set}.y1r1.v1.xml.gz
}
