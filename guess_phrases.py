import itertools
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
    break

def phraseguess_actual_oov(oov: str, matchers: Dict[str, SequenceMatcher], translations: Dict[str, List[str]], catmorfdict: Dict[str, List[Tuple[str, str]]], cheat_guesses: Dict[str, str]) -> (str, bool):
  all_translations = []
  for phrase in gen_phrases(catmorfdict[oov]):
    candidatess = []
    for phrase_segment in phrase:
      lookedup = guess_matching.lookup_oov(phrase_segment, matchers)
      foundlegal = lookedup[0][5] if lookedup else True
      for item in lookedup:
        if item[5] != foundlegal:
          print("Violation!", flush=True)
          exit(1)
      # If we didn't find anything, please don't blow up the result with crap!
      candidatess.append(lookedup if foundlegal else lookedup[:1])
    
    print("\n")
    for clist in candidatess:
      print ("{} x ".format(len(clist)), end='', flush=True)
    
    all_candidates = itertools.product(*candidatess)
    
    all_translations.append(guess_choice.choose_full_phrase_translation(all_candidates, translations, cheat_guesses))
  
  # Check if the correct one was in it
  for (t, aeh) in all_translations:
    if t == cheat_guesses[oov]:
      res = (t, aeh)
  
  # Otherwise return ... first translation?
  res = all_translations[0]
  
  print(" « {} {:<30}".format('=' if res[1] else ' ', res[0]))
  
  return res
