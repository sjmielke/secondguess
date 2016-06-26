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

def phraseguess_actual_oov(ind: (int, int), oov: str, matchers: Dict[str, SequenceMatcher], translations: Dict[str, List[str]], catmorfdict: Dict[str, List[Tuple[str, str]]], cheat_guesses: Dict[str, str]) -> (str, bool):
  all_translations = []
  # Just do the whole for now.
  for phrase in gen_phrases(catmorfdict[oov]):
    phrase_translation = []
    for phrase_segment in phrase:
      #print("lookup " + phrase_segment)
      (found_legal, matchlength, candidates) = guess_matching.lookup_oov(phrase_segment, matchers, translations)
      (translation, _) = guess_choice.choose_translation(ind, oov, found_legal, matchlength, candidates, translations, cheat_guesses)
      phrase_translation.append(translation)
    all_translations.append(" ".join(phrase_translation))
  
  # Check if the correct one was in it
  for t in all_translations:
    if t == cheat_guesses[oov]:
      return (t, False)
  
  # Otherwise return full word translation
  return (all_translations[0], False)

"""
 25 
 88 
  1 
 48 
 73 
 80 
"""
