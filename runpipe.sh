PYGUESSDIR=`pwd`

#echo "2010 2011-يىلدىكى" | python3 $PYGUESSDIR/thirdeye.py pipe\

python3 $PYGUESSDIR/thirdeye.py mode_server\
	staticdata/binary-baseline-model\
	staticdata/v09.guessing_input_lexicon\
	staticdata/emptyfile\
	staticdata/train.target.agile\
	staticdata/leidos_unigrams\
	--unmatchedpartweight   1.0\
	--perfectmatchweight    1.0\
	--oovcoverageweight     0.9\
	--sourcelexrestweight   1.0\
	--sourcepartcountweight 0.3\
	--trainingcountweight   0.5\
	--leidosfrequencyweight 0.9\
	--lengthratioweight     0.4\
	--resultwordcountweight 1.0\
	--deletionscore        -100000.0\
	--copyscore            -50000.0
