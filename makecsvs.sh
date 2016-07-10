cd /home/nlg-05/sjm_445/pyguess/

Wseq="$(seq 0.00 0.05 1.00)"

setw1=0.80
setw2=0.80
setw3=0.80

SCOREPATH="data/out/results"

# 2 Params only

( for w2 in $Wseq; do
    echo -n ",$w2"
  done
  echo ""
  for w1 in $Wseq; do
    echo -n $w1
    for w2 in $Wseq; do
      echo -n ','
      cat $SCOREPATH/score_${w1}_${w2} | tr -d '\n'
      done
    echo ""
  done ) > $SCOREPATH/lengthparams.csv

exit


# Static scores

( for w2 in $Wseq; do
    echo -n ",$w2"
  done
  echo ""
  for w1 in $Wseq; do
    echo -n $w1
    for w2 in $Wseq; do
      echo -n ','
      cat $SCOREPATH/score_${setw1}_${w1}_${w2} | tr -d '\n'
      done
    echo ""
  done ) > $SCOREPATH/setw1_${setw1}.csv

( for w2 in $Wseq; do
    echo -n ",$w2"
  done
  echo ""
  for w1 in $Wseq; do
    echo -n $w1
    for w2 in $Wseq; do
      echo -n ','
      cat $SCOREPATH/score_${w1}_${setw2}_${w2} | tr -d '\n'
      done
    echo ""
  done ) > $SCOREPATH/setw2_${setw2}.csv

( for w2 in $Wseq; do
    echo -n ",$w2"
  done
  echo ""
  for w1 in $Wseq; do
    echo -n $w1
    for w2 in $Wseq; do
      echo -n ','
      cat $SCOREPATH/score_${w1}_${w2}_${setw3} | tr -d '\n'
      done
    echo ""
  done ) > $SCOREPATH/setw3_${setw3}.csv

# Maximal scores

( for w2 in $Wseq; do
    echo -n ",$w2"
  done
  echo ""
  for w1 in $Wseq; do
    echo -n $w1
    for w2 in $Wseq; do
      echo -n ','
      cat $SCOREPATH/score_*_${w1}_${w2} | sort -r | head -1 | tr -d '\n'
      done
    echo ""
  done ) > $SCOREPATH/maxw1.csv
  
( for w2 in $Wseq; do
    echo -n ",$w2"
  done
  for w1 in $Wseq; do
    echo -n $w1
    for w2 in $Wseq; do
      echo -n ','
      cat $SCOREPATH/score_${w1}_*_${w2} | sort -r | head -1 | tr -d '\n'
      done
    echo ""
  done ) > $SCOREPATH/maxw2.csv

( for w2 in $Wseq; do
    echo -n ",$w2"
  done
  for w1 in $Wseq; do
    echo -n $w1
    for w2 in $Wseq; do
      echo -n ','
      cat $SCOREPATH/score_${w1}_${w2}_* | sort -r | head -1 | tr -d '\n'
      done
    echo ""
  done ) > $SCOREPATH/maxw3.csv
