cd /home/nlg-05/sjm_445/pyguess/

for w1 in 0.0 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9 1.0; do
 for w2 in 0.0 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9 1.0; do
  echo "cd /home/nlg-05/sjm_445/pyguess/;source /usr/usc/python/3.5.1/setup.sh;w1=${w1};w2=${w2};" > _r_${w1}_${w2}.sh
  echo "for w3 in 0.0 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9 1.0; do" >> _r_${w1}_${w2}.sh
  echo " python3 thirdeye.py data/{mud.oovlist,mud.oovlist.catmorf,lexicon.norm,mudeval.unique_nes.r1,mud.oovlist.trans_none,mud.oovlist.trans_thirdeye_phrase_against_none_weights_${w1}_${w2}_\${w3}} $w1 $w2 \$w3;" >> _r_${w1}_${w2}.sh
  echo " source evaluate_translations.sh" >> _r_${w1}_${w2}.sh
  echo "done;" >> _r_${w1}_${w2}.sh
  qsub -q isi -l walltime=20:00:00 _r_${w1}_${w2}.sh
 done;
done;
sleep 600
rm _r_*.sh
