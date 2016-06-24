import itertools

import guess_helper
import guess_matching
import guess_nes
import guess_logic

def dict_only(oov_original_list_file: str, oov_cheat_list_file: str, datadir: str):
  (_, translations) = guess_matching.load_dictionary(datadir + "lexicon.norm")
  oov_original_list = guess_helper.load_file_lines(datadir + oov_original_list_file)
  oov_cheat_list    = guess_helper.load_file_lines(datadir + oov_cheat_list_file)
  
  all_translations = set(itertools.chain(*translations.values()))
  
  with open(datadir + oov_cheat_list_file + "_dictonly", 'w') as outfile:
    print("Writing to " + datadir + oov_cheat_list_file + "_dictonly")
    for (oov, trans) in zip(oov_original_list, oov_cheat_list):
      print(trans if trans in all_translations else oov, file=outfile)

def doit(oov_original_list_file: str, datadir: str, cheatfile: str):
  # Load a bunch of things
  oov_original_list = guess_helper.load_file_lines(datadir + oov_original_list_file)
  (matchers, translations) = guess_matching.load_dictionary(datadir + "lexicon.norm")
  nes = guess_helper.load_file_lines(datadir + "mudeval.unique_nes.r1") # apparently untokenized! sucks e.g. for Mosoni-Dunaig
  cheat_guesses = dict(zip(oov_original_list, guess_helper.load_file_lines(datadir + oov_original_list_file + ".trans_sw_uniq_" + cheatfile)))

  # Start filling our guess dictionary!
  oov_guesses = {}

  (guessable_nes, guessable_oovs) = guess_logic.get_guessables_into(oov_guesses, oov_original_list, nes)
  #print("{} distinct NEs and {} distinct OOVs to guess.\n".format(len(guessable_nes), len(guessable_oovs)))

  # Guess NEs
  all_ne_roots = guess_nes.guess_nes_into(oov_guesses, guessable_nes)

  # Then do the actual OOV guessing, while counting,
  # how often were we "better" than the human?
  # (Schema: count_human_thirdeye)
  ((c_nn, c_ny), (c_yn, c_yw, c_yc, c_yy)) = guess_logic.guess_actual_oovs_into(oov_guesses, guessable_oovs, matchers, translations, cheat_guesses)

  # Statistics
  print("Comparing against the human in " + cheatfile)
  print("> {:<27} {:3} ({})".format("No human, no algo:", \
    c_nn, "neither knew a translation"))
  print("> {:<27} {:3} ({})".format("No human, but algo:", \
    c_ny, "we're either superhuman or translated stray NEs"))
  print("> {:<27} {:3} ({})".format("Human, but no algo:", \
    c_yn, "didn't find any translation, but human did"))
  print("> {:<27} {:3} ({})".format("Human, but wrong algo:", \
    c_yw, "didn't find the human translation containing lexicon entry, but found another"))
  print("> {:<27} {:3} ({})".format("Human corrected algo:", \
    c_yc, "found the human suggestion containing lexicon entry, but wouldn't have chosen it"))
  print("> {:<27} {:3} ({})".format("Human = algo:", \
    c_yy, "found the human suggestion containing candidate and naturally chose it!"))

  # Write our results in original order
  with open(datadir + oov_original_list_file + ".trans_thirdeye_against_sw_uniq_" + cheatfile, 'w') as translist:
    for oov in oov_original_list:
      print(oov_guesses[oov], file=translist)

if __name__ == '__main__':
  datadir = "/home/sjm/documents/ISI/pyguess/data/"
  oovfile = "mud.oovlist"

  #dict_only(oovfile, "mud.oovlist.trans_sw_uniq_human", datadir)
  #dict_only(oovfile, "mud.oovlist.trans_sw_uniq_reference", datadir)

  for reference in ["human_dictonly", "human", "reference_dictonly", "reference"]:
    doit(oovfile, datadir, reference)
  
