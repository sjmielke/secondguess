cd /home/nlg-05/sjm_445/pyguess/

for w1 in $(seq 0.0 0.05 1.0); do
  echo "cd /home/nlg-05/sjm_445/pyguess/;source /usr/usc/python/3.5.1/setup.sh;w1=${w1};w2=${w2};" > _r_${w1}.sh
  echo "for w2 in \$(seq 0.0 0.05 1.0); do" >> _r_${w1}.sh
  echo "  for w3 in \$(seq 0.0 0.05 1.0); do" >> _r_${w1}.sh
  echo "    python3 thirdeye.py data/{mud.oovlist,mud.oovlist.catmorf,lexicon.norm,mudeval.unique_nes.r1,mud.oovlist.trans_none,mud.oovlist.fullmorfmatches,mud.oovlist.trans_thirdeye_phrase_against_none_weights_${w1}_\${w2}_\${w3}} $w1 \$w2 \$w3;" >> _r_${w1}.sh
  echo "    source evaluate_translations.sh" >> _r_${w1}.sh
  echo "  done;" >> _r_${w1}.sh
  echo "done;" >> _r_${w1}.sh
  qsub -q isi -l walltime=20:00:00 _r_${w1}.sh
done;
sleep 600
rm _r_*.sh
