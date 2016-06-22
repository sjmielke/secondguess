from difflib import SequenceMatcher
from collections import defaultdict
from typing import Dict, List
import sys

from guess_helper import load_file_lines

def is_legal_match(w1: str, w2: str, i1: int, i2: int, l: int) -> bool:
  justsmallaffix = lambda a,b: (a == 0 or b == 0) and a + b <= 2
  w1_ok = l / len(w1) > 0.9 or justsmallaffix(i1, len(w1) - (i1 + l)) and l >= 5
  w2_ok = l / len(w2) > 0.9 or justsmallaffix(i2, len(w2) - (i2 + l)) and l >= 5
  if sys.argv[1] == "mono2affix_min5":
    return w1_ok
  elif sys.argv[1] == "anyaffix":
    return True
  elif sys.argv[1] == "noaffix":
    return l == len(w1)
  elif sys.argv[1] == "mono2affix_min5_both":
    return w1_ok and w2_ok
  elif sys.argv[1] == "mono2affix_min5_match3":
    return w1_ok and l >= 3
  else:
    print(sys.argv[1] + "is no real suffix")
    exit(1)

def load_dictionary(path: str) -> (Dict[str, SequenceMatcher], Dict[str, List[str]]):
  matchers = {}
  translations = defaultdict(list)
  for line in load_file_lines(path):
    (w, _, t) = line.split('\t')
    matchers[w] = SequenceMatcher(a=None, b=w, autojunk=False)
    translations[w].append(t)
  #print("{} distinct dictionary words to compare against loaded.".format(len(matchers.keys())))
  return (matchers, translations)
