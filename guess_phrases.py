import itertools
import operator # mul, itemgetter
from functools import reduce
from difflib import SequenceMatcher
from typing import Dict, List, Tuple

from guess_helper import mapfst
import guess_matching
import guess_choice

def gen_phrases(segments: [(str, str)]) -> [[str]]:
  segs_texts = list(mapfst(segments))
  for sl in itertools.product(*([["", " "]] * (len(segs_texts) - 1))):
    #print("gen {}".format(list(itertools.chain(*zip(segs_texts, sl))) + [segs_texts[-1]]))
    yield ("".join(list(itertools.chain(*zip(segs_texts, sl))) + [segs_texts[-1]])).split()
    # break # only full

def phraseguess_actual_oov(oov: str, all_matches: Dict[str, List[Tuple[str, str, int, int, int, bool]]], translations: Dict[str, List[str]], catmorfdict: Dict[str, List[Tuple[str, str]]], cheat_guesses: Dict[str, str]) -> (str, bool):
  all_translations = []
  print("\n")
  for phrase in gen_phrases(catmorfdict[oov]):
    candidatess = []
    for phrase_segment in phrase:
      candidatess.append(all_matches[phrase_segment])
    
    lengths = list(map(len, candidatess))
    statstring = " x ".join(map(str, lengths)) + " = {}".format(reduce(operator.mul, lengths, 1))
    print (" » {:<20} » {:<20}".format(" ".join(phrase), statstring), end='', flush=True)
    
    all_candidates = itertools.product(*candidatess)
    
    all_translations.append(guess_choice.choose_full_phrase_translation(all_candidates, translations, cheat_guesses))
  
  # Return best translation!
  res = min(all_translations, key = operator.itemgetter(1))[0:3:2] # get fst+trd
  
  # Or the correct one, if it was returned
  for (t, score, aeh) in all_translations:
    if t == cheat_guesses[oov]:
      res = (t, aeh)
  
  print(" « {} {:<30}".format('=' if res[1] else ' ', res[0]))
  
  return res
