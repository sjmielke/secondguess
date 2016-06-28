from typing import Dict, List

import guess_helper

def candidate_eval(cand: [(str, int, int, int, bool)]):
  # each illegal result results in penalty
  nomatch_penalty = sum(map(lambda w: 0 if w[4] else 1, cand))
  # prefer shorter lexwords
  lexlengths = sum(map(len, guess_helper.mapfst(cand)))
  return (nomatch_penalty, lexlengths)

def choose_full_phrase_translation(unsorted_candidates: [[(str, str, int, int, int, bool)]], translations: Dict[str, List[str]], cheat_guesses: Dict[str, str]) -> (str, bool):
  # Compare performance
  what_the_algo_said = None
  # Return
  result = None
  
  candidates = sorted(list(unsorted_candidates), key = candidate_eval)
  
  phrase = list(guess_helper.mapfst(candidates[0]))
  fullphrase = "".join(phrase)
  
  
  # First, what would the algo itself say?
  result_candidate = candidates[0] # translate "best" candidate
  result_transwords = []
  
  algo_transwords = []
  for (oov, lexword, _, _, _, legal) in result_candidate:
    algo_transwords.append(min(translations[lexword], key=len) if legal else oov) # shortest translation, TODO sort while loading dict
  result_transwords = algo_transwords
  what_the_algo_said = " ".join(algo_transwords)
  result = what_the_algo_said
  
  # Now, can I find the "correct" solution? Then replace old result with it!
  foundcheat = False
  cheatsolution = cheat_guesses[fullphrase].split()
  if len(cheatsolution) == len(algo_transwords): # only if we have a chance
    for candidate in candidates:
      foundcheat = True
      for ((_, lexword, _, _, _, _), cheatword) in zip(candidate, cheatsolution):
        if not cheatword in translations[lexword]:
          foundcheat = False
          break
      if foundcheat:
        result_candidate = candidate
        result_transwords = cheatsolution
        result = cheat_guesses[fullphrase]
        break
  
  #"""
  # TODO prohibit inter-thread-foo
  print("\n » {:<20} » {} {}".format(
    " ".join(phrase),
    '❗' if foundcheat else ' ',
    '=' if what_the_algo_said == cheat_guesses[fullphrase] else ' '))
  for ((oov, lexword, lexindex, oovindex, matchlength, legal), trans) in zip(result_candidate, result_transwords):
    if legal:
      print("   {:<36} ✔ {:<36} -> {:<20}".format( # 20 + 4 * 4 = 36
        guess_helper.bold(oov    , oovindex, matchlength),
        guess_helper.bold(lexword, lexindex, matchlength),
        trans))
    else:
      print("   {:<36} ✗ {:<20} -> {:<20}".format(
        guess_helper.bold(oov    , oovindex, matchlength),
        "---",
        oov))
  #"""
  
  return (result, what_the_algo_said == cheat_guesses[fullphrase])

