# set should be set
# runpreamble be sourced

# Clean batches up
rm -f data/${set}.sbmt.oov.scores.batch.*

# Prepare guessable batches
NOOFBATCHES=$(python3 $PYGUESSDIR/thirdeye.py\
	mode1_genbatches\
	500\
	data/${set}.sbmt.oov\
	nocheatref\
	data/${set}.sbmt.oov.catmorf\
	staticdata/emptyfile\
	data/${LEX}.fullmorfmatches)

# Submit many jobs
for i in $(seq 1 $NOOFBATCHES); do
	cat > data/${set}.sbmt.oov.scores.batch.$i.sh <<- EOT
		source $PYGUESSDIR/runpreamble.sh
		python3 $PYGUESSDIR/thirdeye.py\
			mode2_scorebatch\
			\
			data/${set}.sbmt.oov.scores.batch.$i\
			nocheatref\
			\
			staticdata/${LEX}\
			data/${set}.sbmt.oov.catmorf\
			staticdata/emptyfile\
			staticdata/train.target.agile\
			staticdata/leidos_unigrams\
			\
			data/${LEX}.fullmorfmatches\
			\
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
	EOT
	
	qsub -q isi -l walltime=100:00:00 -lnodes=1:quadcore -N score.$set.$i.sh data/${set}.sbmt.oov.scores.batch.$i.sh
	rm data/${set}.sbmt.oov.scores.batch.$i.sh
done

# Wait for all jobs
for f in $(eval echo data/${set}.sbmt.oov.scores.batch.{1..$NOOFBATCHES}.done); do
	echo "Now starting the wait for $f"
	wait-for-file $f
done

# Combine all results
python3 $PYGUESSDIR/thirdeye.py\
	mode3_combineresults\
	data/${set}.sbmt.oov\
	$NOOFBATCHES\
	data/${set}.sbmt.oov.trans_thirdeye

# Clean batches up
rm data/${set}.sbmt.oov.scores.batch.*

# Now restitch them into sbmt output
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
