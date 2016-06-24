from difflib import SequenceMatcher
from typing import Dict, List

import guess_matching

def gen_phrases(segments: [str]) -> [[str]]:
  phrases = [["".join(segments)]]
  return phrases

def phraseguess_actual_oov(ind: (int, int), oov: str, matchers: Dict[str, SequenceMatcher], translations: Dict[str, List[str]], cheat_guesses: Dict[str, str]) -> (str, str):
  # Just do the whole for now.
  return guess_matching.lookup_oov(ind, oov, matchers, translations, cheat_guesses)
