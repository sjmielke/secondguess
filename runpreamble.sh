# To be sourced by both `runall.sh` and the `runset.sh` instances it qsubs.

set -e
SETS="syscomb eval  dev domain test uroom"
SBMTSYSTEM="isi-sbmt-v5-comparelm"
DATADIR="/home/nlg-05/sjm_445/uyghur/on_top_of/$SBMTSYSTEM"
PYGUESSDIR="/home/nlg-05/sjm_445/pyguess"
LEX="guessing_input_lexicon.v12"

cd $DATADIR
source /usr/usc/python/3.5.1/setup.sh

wait-for-file ()
{
	while [ ! -s $1 ]; do
		sleep 10
	done
}
