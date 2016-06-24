from difflib import SequenceMatcher
from typing import Dict, List
import multiprocessing
import itertools

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

def guess_actual_oovs_into(oov_guesses: Dict[str, str], raw_guessable_oovs: str, matchers: Dict[str, SequenceMatcher], translations: Dict[str, List[str]], cheat_guesses: Dict[str, str]) -> ((int, int), (int, int, int)):
  # Do it!
  guessable_oovs = sorted(raw_guessable_oovs)
  preproc = lambda p: ((p[0], len(guessable_oovs)), p[1], matchers, translations, cheat_guesses)
  crunchabledata = map(preproc, zip(range(0, len(guessable_oovs)), guessable_oovs))
  from contextlib import closing
  with closing(multiprocessing.Pool(processes = 4)) as pool:
    all_results = pool.starmap(guess_actual_oov, crunchabledata)
  
  # What came out?
  count_nocheat_noalg = 0
  count_nocheat_yesalg = 0
  count_yescheat_noalg = 0
  count_yescheat_wrongalg = 0
  count_yescheat_correctedalg = 0
  count_yescheat_yesalg = 0
  
  edgecases = []
  
  for (oov, (result, algo_eq_human)) in zip(guessable_oovs, all_results):
    oov_guesses[oov] = result
    if cheat_guesses[oov] == oov: # human didn't know
      if algo_eq_human:
        count_nocheat_noalg += 1
      else:
        count_nocheat_yesalg += 1
        edgecases.append(oov)
    else: # human knew a translation
      if result == oov:
        count_yescheat_noalg += 1
      elif result != cheat_guesses[oov]:
        count_yescheat_wrongalg += 1
      elif not algo_eq_human:
        count_yescheat_correctedalg += 1
      else:
        count_yescheat_yesalg += 1
  
  #for oov in edgecases:
  #  print("{} -> {} (result) / {} (human)".format(oov, oov_guesses[oov], cheat_guesses[oov]))
  
  return ((count_nocheat_noalg, count_nocheat_yesalg), (count_yescheat_noalg, count_yescheat_wrongalg, count_yescheat_correctedalg, count_yescheat_yesalg))
