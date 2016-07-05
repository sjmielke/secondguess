cd /home/nlg-05/sjm_445/pyguess/

Wseq="$(seq 0.0 0.05 1.0)"

( for w2 in $Wseq; do
    echo -n ",$w2"
  done
  echo ""
  for w1 in $Wseq; do
    echo -n $w1
    for w2 in $Wseq; do
      echo -n ','
      cat data/results/score_*_${w1}_${w2} | sort -r | head -1 | tr -d '\n'
      done
    echo ""
  done ) > data/results/maxw1.csv
  
( for w2 in $Wseq; do
    echo -n ",$w2"
  done
  for w1 in $Wseq; do
    echo -n $w1
    for w2 in $Wseq; do
      echo -n ','
      cat data/results/score_${w1}_*_${w2} | sort -r | head -1 | tr -d '\n'
      done
    echo ""
  done ) > data/results/maxw2.csv

( for w2 in $Wseq; do
    echo -n ",$w2"
  done
  for w1 in $Wseq; do
    echo -n $w1
    for w2 in $Wseq; do
      echo -n ','
      cat data/results/score_${w1}_${w2}_* | sort -r | head -1 | tr -d '\n'
      done
    echo ""
  done ) > data/results/maxw3.csv


( for w2 in $Wseq; do
    echo -n ",$w2"
  done
  echo ""
  for w1 in $Wseq; do
    echo -n $w1
    for w2 in $Wseq; do
      echo -n ','
      cat data/results/score_0.50_${w1}_${w2} | tr -d '\n'
      done
    echo ""
  done ) > data/results/maxw1_0.5.csv

( for w2 in $Wseq; do
    echo -n ",$w2"
  done
  echo ""
  for w1 in $Wseq; do
    echo -n $w1
    for w2 in $Wseq; do
      echo -n ','
      cat data/results/score_${w1}_0.25_${w2} | tr -d '\n'
      done
    echo ""
  done ) > data/results/maxw2_0.25.csv

( for w2 in $Wseq; do
    echo -n ",$w2"
  done
  echo ""
  for w1 in $Wseq; do
    echo -n $w1
    for w2 in $Wseq; do
      echo -n ','
      cat data/results/score_${w1}_0.5_${w2} | tr -d '\n'
      done
    echo ""
  done ) > data/results/maxw2_0.5.csv
( for w2 in $Wseq; do
    echo -n ",$w2"
  done
  echo ""
  for w1 in $Wseq; do
    echo -n $w1
    for w2 in $Wseq; do
      echo -n ','
      cat data/results/score_${w1}_0.75_${w2} | tr -d '\n'
      done
    echo ""
  done ) > data/results/maxw2_0.75.csv

( for w2 in $Wseq; do
    echo -n ",$w2"
  done
  echo ""
  for w1 in $Wseq; do
    echo -n $w1
    for w2 in $Wseq; do
      echo -n ','
      cat data/results/score_${w1}_${w2}_0.50 | tr -d '\n'
      done
    echo ""
  done ) > data/results/maxw3_0.5.csv

