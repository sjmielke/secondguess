from difflib import SequenceMatcher
from typing import Dict, List
import multiprocessing
import itertools
import sys

import guess_helper
import guess_matching

def get_guessables_into(guesses: Dict[str, str], fulluniqlist: [str], ne_list: [str]) -> ([str], [str]):
  guessable_nes = []
  guessable_oovs = []
  for w in list(set(fulluniqlist)):
    # Filter out non-alphabetic tokens
    if not any(c.isalpha() for c in w):
      #print("{:<20} ~~> non-alpha token".format(w))
      guesses[w] = w
    elif w in ne_list:
      guessable_nes.append(w)
    else:
      guessable_oovs.append(w)
  return (guessable_nes, guessable_oovs)

def get_best_match(oov: str, lexword: str, matcher: SequenceMatcher) -> (str, (int, int, int)):
  matcher.set_seq1(oov)
  i_o, i_w, matchlength = matcher.find_longest_match(0, len(oov), 0, len(lexword))
  return (lexword, (i_o, i_w, matchlength))

def guess_actual_oov(ind: (int, int), oov: str, matchers: Dict[str, SequenceMatcher], translations: Dict[str, List[str]], cheat_guesses: Dict[str, str]) -> (str, str, str):
  print("({:3}/{:3}) ".format(ind[0]+1, ind[1]+1), end='')
  
  # Compare performance
  human = ''
  algo = ''
  result = ''
  
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
    if sys.argv[1] == "mono2affix_min5_match3" and matchlength < 3 or found_legal and matchlength < best_matchlength:
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
  
  # Okay! Matching done!
  if best_matchlength != 0:
    # Choose the matched lexword / best translation jointly!
    candidates = sorted(best_lexcandidates, key=lambda tup: len(tup[0]))
    # Can I find the "correct" solution?
    what_the_algo_says = min(sorted(translations[candidates[0][0]], key=len)) # sorted for determinism
    foundcheat = False
    for (lw, li, oi) in candidates:
      if cheat_guesses[oov] in translations[lw]:
        (lexword, lexindex, oovindex) = (lw, li, oi)
        besttranslation = cheat_guesses[oov]
        foundcheat = True
    if not foundcheat:
      (lexword, lexindex, oovindex) = candidates[0]
      besttranslation = what_the_algo_says
    
    # Statistics!
    if cheat_guesses[oov] != oov: # cheat=translate
      human = 'yes'
      algo = 'yes' if what_the_algo_says == cheat_guesses[oov] else 'wrong'
    else: # cheat=copy
      human = 'no'
      algo = 'yes'
    
    # Okay, now check that it's alright
    dowe = guess_matching.is_legal_match(lexword, oov, lexindex, oovindex, best_matchlength)
    perc_lex = best_matchlength / len(lexword)
    perc_oov = best_matchlength / len(oov)
    print("{:<36}{:<36}".format( # 20 + 4 * 4 = 36
        guess_helper.bold(oov    , oovindex, best_matchlength),
        guess_helper.bold(lexword, lexindex, best_matchlength)), end='')
    
    if dowe:
      result = besttranslation
    else:
      result = oov
    
    iseq = (result == cheat_guesses[oov]) # should be a consequence of copying!
    
    print(" {} {} {}    {:<20} ({:4.0%} of lexword, {:4.0%} of OOV)".format(\
      '✔' if dowe else '✗',\
      '❗' if foundcheat else ' ',\
      '=' if iseq else ' ',\
      besttranslation if dowe else "",\
      perc_lex, perc_oov))
  else:
    print("{:<20} ~~> none found!         {}".format(oov, '=' if cheat_guesses[oov] == oov else ' '))
    result = oov
    # Statistics
    human = 'yes' if cheat_guesses[oov] != oov else 'no'
    algo = 'no'
  
  return (oov, result, human, algo)

def guess_actual_oovs_into(oov_guesses: Dict[str, str], guessable_oovs: str, matchers: Dict[str, SequenceMatcher], translations: Dict[str, List[str]], cheat_guesses: Dict[str, str]) -> ((int, int), (int, int, int)):
  # Do it!
  preproc = lambda p: ((p[0], len(guessable_oovs)), p[1], matchers, translations, cheat_guesses)
  crunchabledata = map(preproc, zip(range(0, len(guessable_oovs)), sorted(guessable_oovs)))
  from contextlib import closing
  with closing(multiprocessing.Pool(processes = 4)) as pool:
    all_results = pool.starmap(guess_actual_oov, crunchabledata)
  
  # What came out?
  count_nocheat_noalg = 0
  count_nocheat_yesalg = 0
  count_yescheat_noalg = 0
  count_yescheat_wrongalg = 0
  count_yescheat_yesalg = 0
  for (oov, result, human, algo) in all_results:
    oov_guesses[oov] = result
    if human == 'no':
      if algo == 'no':
        count_nocheat_noalg += 1
      elif algo == 'yes':
        count_nocheat_yesalg += 1
    else:
      if algo == 'no':
        count_yescheat_noalg += 1
      elif algo == 'wrong':
        count_yescheat_wrongalg += 1
      elif algo == 'yes':
        count_yescheat_yesalg += 1
    
  return ((count_nocheat_noalg, count_nocheat_yesalg), (count_yescheat_noalg, count_yescheat_wrongalg, count_yescheat_yesalg))
