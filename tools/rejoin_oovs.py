import json
import sys

import argparse

parser = argparse.ArgumentParser(description='Do a lot of stuff with OOVs.')
parser.add_argument('alignfile', help='<- nbest2json output')
parser.add_argument('oovtransfile', help='<- translated OOVs')
parser.add_argument('transtransfile', help='-> postprocessed translations')
args = parser.parse_args()

with open(args.alignfile) as f,\
     open(args.transtransfile, "w") as transtrans_outfile,\
     open(args.oovtransfile) as trans_oovlist_file:
  data = json.load(f)['translation']
  transoovs = trans_oovlist_file.read().splitlines()
  for sentence in data:
    transtrans_sentence = []
    for token in sentence['alignment']['tokenized-target']:
      #print(len(transoovs))
      transtrans_sentence.append(transoovs.pop(0) if token['rule-class'] != "translation" else token['token'])
    print(" ".join(transtrans_sentence), file=transtrans_outfile)
