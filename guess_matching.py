from difflib import SequenceMatcher
from collections import defaultdict
from typing import Dict, List

from guess_helper import load_file_lines

# mono2affix_min5_match3
def is_legal_match(w1: str, w2: str, i1: int, i2: int, l: int) -> bool:
  i2_ = len(w1) - (i1 + l)
  return l >= 3 and (l / len(w1) > 0.9 or (i1 == 0 or i2_ == 0) and i1 + i2_ <= 2 and l >= 5)

def load_dictionary(path: str) -> (Dict[str, SequenceMatcher], Dict[str, List[str]]):
  matchers = {}
  translations = defaultdict(list)
  for line in load_file_lines(path):
    (w, _, t) = line.split('\t')
    matchers[w] = SequenceMatcher(a=None, b=w, autojunk=False)
    translations[w].append(t)
  #print("{} distinct dictionary words to compare against loaded.".format(len(matchers.keys())))
  return (matchers, translations)

def get_best_match(oov: str, lexword: str, matcher: SequenceMatcher) -> (str, (int, int, int)):
  matcher.set_seq1(oov)
  i_o, i_w, matchlength = matcher.find_longest_match(0, len(oov), 0, len(lexword))
  return (lexword, (i_o, i_w, matchlength))

def guess_actual_oov(ind: (int, int), oov: str, matchers: Dict[str, SequenceMatcher], translations: Dict[str, List[str]], cheat_guesses: Dict[str, str]) -> (str, str):
  # Compare performance
  what_the_algo_said = None
  # Return
  result = None
  
  # Match search
  best_lexcandidates = []
  best_matchlength = 0
  found_legal = False
  
  # First find LCS = match with lexword in a mapreduce fashion
  all_pairs = map(lambda w: (oov, w, matchers[w]), sorted(matchers.keys()))
  
  individual_bestmatches = itertools.starmap(get_best_match, all_pairs)
  
  # Now compare all findings!
  #print(" ")
  #print("?")
  for (lexword, (i_o, i_w, matchlength)) in individual_bestmatches:
    if found_legal and (matchlength < 3 or matchlength < best_matchlength):
      continue
    legal = guess_matching.is_legal_match(lexword, oov, i_w, i_o, matchlength)
    if not found_legal or legal: # no legality regressions!
      if matchlength == best_matchlength: # no improvement? just add a candidate
        best_lexcandidates.append((lexword, i_w, i_o))
      elif (legal and not found_legal # we find our first legal match...
          or matchlength >= best_matchlength): # ...or a better one, regardless of legality status
        best_lexcandidates = [(lexword, i_w, i_o)]
        best_matchlength = matchlength
    if legal:
      found_legal = True
  #print("!")
  #print(" ")
  
  # Okay! Matching done, now choose something nice!
  if best_matchlength == 0:
    """
    print("({:3}/{:3}) {:<20} ~~> none found!         {}".format(
      ind[0]+1, ind[1]+1,
      oov,
      '=' if cheat_guesses[oov] == oov else ' '))
    """
    what_the_algo_said = oov
    result = oov
  else:
    candidates = sorted(best_lexcandidates, key=lambda tup: len(tup[0])) # prefer shorter lexwords
    
    # First, what would the algo itself say?
    what_the_algo_said = min(sorted(translations[candidates[0][0]], key=len)) if found_legal else oov
    (lexword, lexindex, oovindex) = candidates[0]
    result = what_the_algo_said
    
    # Now, can I find the "correct" solution? Then replace old result with it!
    foundcheat = False
    for (lw, li, oi) in candidates:
      if cheat_guesses[oov] in translations[lw]:
        (lexword, lexindex, oovindex) = (lw, li, oi)
        result = cheat_guesses[oov]
        foundcheat = True
        break
    
    """
    # Output individual results
    print("({:3}/{:3}) {:<36}{:<36} {} {} {}   {:<20}".format( # 20 + 4 * 4 = 36
      ind[0]+1, ind[1]+1,
      guess_helper.bold(oov    , oovindex, best_matchlength),
      guess_helper.bold(lexword, lexindex, best_matchlength),
      '✔' if found_legal else '✗',
      '❗' if foundcheat else ' ',
      '=' if what_the_algo_said == cheat_guesses[oov] else ' ',
      result if result != oov else ""))
    """
  
  return (result, what_the_algo_said == cheat_guesses[oov])
