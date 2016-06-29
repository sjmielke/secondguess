#! /bin/env bash

set -e

TOOLDIR="/home/sjm/documents/ISI/oovextractor/aligntools"

cd data

for ref in mudeval.reference.detok mudeval.align.transtrans_sw_uniq_{reference,human};
do
  echo " "
  echo "Reference: $ref"
  for set in identity\
             thirdeye_against_{none,sw_uniq_{human,human_dictonly,reference,reference_dictonly}}\
      thirdeye_phrase_against_{none,uniq_{human,human_dictonly,reference,reference_dictonly}};
  do
    # Build translations
    python $TOOLDIR/rejoin_oovs.py mudeval.align mud.oovlist.trans_$set /tmp/_tok_$set
    # Truecase and detokenize
    < /tmp/_tok_$set perl $TOOLDIR/truecase.perl --model $TOOLDIR/eng.tc.model | $TOOLDIR/lw_detokenize.pl > /tmp/_detok_$set
    # Calculate Score
    printf "%-60s " $set
    java -jar /home/sjm/documents/ISI/meteor-1.5/meteor-1.5.jar /tmp/_detok_$set $ref -l en -norm 2>/dev/null | grep '^Final score:' | sed 's/^Final score: *//'
    # Cleanup
    rm /tmp/_{,de}tok_$set
  done;
done;
