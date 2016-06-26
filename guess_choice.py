from typing import Dict, List

import guess_helper

def choose_translation(ind: (int, int), oov: str, found_legal: bool, matchlength: int, unsorted_candidates: [(str, int, int)], translations: Dict[str, List[str]], cheat_guesses: Dict[str, str]) -> (str, bool):
  # Compare performance
  what_the_algo_said = None
  #Return
  result = None
  
  # Okay! Matching done, now choose something nice!
  if matchlength == 0:
    #"""
    print("({:3}/{:3}) {:<20} ~~> none found!         {}".format(
      ind[0]+1, ind[1]+1,
      oov,
      '=' if cheat_guesses[oov] == oov else ' '))
    #"""
    what_the_algo_said = oov
    result = oov
  else:
    candidates = sorted(unsorted_candidates, key=lambda tup: len(tup[0])) # prefer shorter lexwords
    
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
    
    #"""
    # Output individual results
    print("({:3}/{:3}) {:<36}{:<36} {} {} {}   {:<20}".format( # 20 + 4 * 4 = 36
      ind[0]+1, ind[1]+1,
      guess_helper.bold(oov    , oovindex, matchlength),
      guess_helper.bold(lexword, lexindex, matchlength),
      '✔' if found_legal else '✗',
      '❗' if foundcheat else ' ',
      '=' if what_the_algo_said == cheat_guesses[oov] else ' ',
      result if result != oov else ""))
    #"""
  
  return (result, what_the_algo_said == cheat_guesses[oov])
