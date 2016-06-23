import sys

import guess_helper
import guess_matching
import guess_nes
import guess_logic

if __name__ == '__main__':

  datadir = "/home/sjm/documents/ISI/pyguess/data/"

  # Load a bunch of things
  (matchers, translations) = guess_matching.load_dictionary(datadir + "lexicon.norm")
  nes = guess_helper.load_file_lines(datadir + "mudeval.unique_nes.r1") # apparently untokenized! sucks e.g. for Mosoni-Dunaig
  oov_original_list = guess_helper.load_file_lines(datadir + "mud.oovlist")
  cheat_guesses = dict(zip(oov_original_list, guess_helper.load_file_lines(datadir + "mud.oovlist.trans_sw_uniq_human_dictonly")))

  # Start filling our guess dictionary!
  oov_guesses = {}

  (guessable_nes, guessable_oovs) = guess_logic.get_guessables_into(oov_guesses, oov_original_list, nes)
  print("{} distinct NEs and {} distinct OOVs to guess.\n".format(len(guessable_nes), len(guessable_oovs)))

  # Guess NEs
  all_ne_roots = guess_nes.guess_nes_into(oov_guesses, guessable_nes)

  # Then do the actual OOV guessing, while counting,
  # how often were we "better" than the human?
  # (Schema: count_human_thirdeye)
  ((c_nn, c_ny), (c_yn, c_yw, c_yy)) = guess_logic.guess_actual_oovs_into(oov_guesses, guessable_oovs, matchers, translations, cheat_guesses)

  # Statistics
  print("{}) {:<25} {:3} ({})".format(sys.argv[1],\
    "No cheat, no algo:", c_nn, "neither knew a translation"))
  print("{}) {:<25} {:3} ({})".format(sys.argv[1],\
    "No cheat, but algo:", c_ny, "we're either superhuman or translated stray NEs"))
  print("{}) {:<25} {:3} ({})".format(sys.argv[1],\
    "Cheat, but no algo:", c_yn, "didn't find any candidate, but human did"))
  print("{}) {:<25} {:3} ({})".format(sys.argv[1],\
    "Cheat, but wrong algo:", c_yw, "didn't find the human suggestion containing candidate, but found something else"))
  print("{}) {:<25} {:3} ({})".format(sys.argv[1],\
    "Cheat = algo:", c_yy, "found the human suggestion containing candidate!"))

  # Write our results in original order
  with open(datadir + "mud.oovlist.trans_" + sys.argv[1], 'w') as translist:
    for oov in oov_original_list:
      print(oov_guesses[oov], file=translist)


  """
    2
  111
    0
  121
   81
  """
