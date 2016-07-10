#! /bin/env bash

set -e

cd data/out
TOOLDIR="../../tools"

mkdir -p results

for ref in ../mudeval.reference.detok ; # mudeval.align.transtrans_{sw_,}uniq_{reference,human};
do
  echo " "
  echo "Reference: $ref"
  #for set in identity\
  #           thirdeye_against_{none,sw_uniq_{human,human_dictonly,reference,reference_dictonly}}\
  #    thirdeye_phrase_against_{none,uniq_{human,human_dictonly,reference,reference_dictonly}};
  for set in thirdeye_phrase_against_none_lengthratio_${w1}_${w2};
  do
    # Build translations
    python3 $TOOLDIR/rejoin_oovs.py ../mudeval.align ../out/mud.oovlist.trans_$set /tmp/_tok_$set
    # Truecase and detokenize
    < /tmp/_tok_$set perl $TOOLDIR/truecase.perl --model $TOOLDIR/eng.tc.model | $TOOLDIR/agile_tokenizer/lw_detokenize.pl > /tmp/_detok_$set
    # Calculate Score
    printf "%-60s " $set
    java -jar $TOOLDIR/meteor-1.5/meteor-1.5.jar /tmp/_detok_$set $ref -l en -norm 2>/dev/null | grep '^Final score:' | sed 's/^Final score: *//' > results/score_${w1}_${w2}
    # Cleanup
    rm /tmp/_{,de}tok_$set
  done;
done;

cd ../..
