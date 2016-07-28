import json
import sys

import argparse

parser = argparse.ArgumentParser(description='Do a lot of stuff with OOVs.')
parser.add_argument('alignfile', help='<- nbest2json output')
parser.add_argument('tsvfile'  , help='-> nice TSV of all target classes and tokens')
parser.add_argument('oovfile', help='-> list of OOVs to translate')
args = parser.parse_args()

with open(args.alignfile) as f,\
     open(args.tsvfile, "w") as alltok_outfile,\
     open(args.oovfile, "w") as oovlist_outfile:
  data = json.load(f)['translation']
  for sentence in data:
    for token in sentence['alignment']['tokenized-target']:
      # Defensiveness
      if token['rule-class'] != "translation" and token['source'][0]['token'] != token['token']:
        print(token['rule-class'] + ", but translated " + token['source'][0]['token'] + " -> " + token['token'], file=sys.stderr)
      # Lets first get the full TSV output out of the way:
      print(token['rule-class'] + "\t" + token['token'], file=alltok_outfile)
      # Output OOV list
      if token['rule-class'] != "translation":
        print(token['token'], file=oovlist_outfile)
