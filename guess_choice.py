from typing import Dict, List, Tuple

import guess_helper

import sys

def score_phrase(cand: [(str, str, int, int, int, bool)]) -> float:
  # each illegal result results in penalty
  nomatch_penalty = 0.07 * sum(map(lambda w: 0 if w[5] else 1, cand))
  # prefer more OOV coverage (sum of matchlength [not translating is a full match!] by total oov length)
  coverage = 0.15 * sum(map(lambda w: w[4], cand)) / sum(map(lambda w: len(w[0]), cand))
  # prefer shorter lexwords (0.05 is arbitrary)
  lexlengths_penalty = 0.02 * sum(map(lambda w: len(w[1]), cand))
  # We want to minimize this!
  scores = (float(sys.argv[-3]) * -1 * nomatch_penalty,
            float(sys.argv[-2]) *      coverage,
            float(sys.argv[-1]) * -1 * lexlengths_penalty)
  return scores

def choose_full_phrase_translation(unsorted_candidates: [[(str, str, int, int, int, bool)]], translations: Dict[str, List[str]], cheat_guesses: Dict[str, str]) -> (str, Tuple[float], bool):
  # Compare performance
  what_the_algo_said = None
  # Return
  result = None
  
  candidates = sorted(list(unsorted_candidates), key = score_phrase, reverse = True)
  
  phrase = list(guess_helper.mapfst(candidates[0]))
  fullphrase = "".join(phrase)
  
  
  # First, what would the algo itself say?
  result_candidate = candidates[0] # translate "best" candidate
  result_transwords = []
  
  algo_transwords = []
  for (oov, lexword, _, _, _, legal) in result_candidate:
    algo_transwords.append(min(translations[lexword], key=len) if legal else oov)
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
  
  """
  # TODO prohibit inter-thread-foo
  print(" » {} {}".format(
    '❗' if foundcheat else ' ',
    '=' if what_the_algo_said == cheat_guesses[fullphrase] else ' '))
  for ((oov, lexword, lexindex, oovindex, matchlength, legal), trans) in zip(result_candidate, result_transwords):
    if legal:
      print("     {:<36} ✔ {:<36} -> {:<20}".format( # 20 + 4 * 4 = 36
        guess_helper.bold(oov    , oovindex, matchlength),
        guess_helper.bold(lexword, lexindex, matchlength),
        trans))
    else:
      print("     {:<36} ✗ {:<20} -> {:<20}".format(
        guess_helper.bold(oov    , oovindex, matchlength),
        "---",
        oov))
  #"""
  
  return (result, score_phrase(result_candidate), what_the_algo_said == cheat_guesses[fullphrase])

