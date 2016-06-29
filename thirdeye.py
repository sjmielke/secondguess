import itertools

import guess_helper
import guess_matching
import guess_nes
import guess_logic

import argparse

def dict_only(oov_original_list_file: str, oov_cheat_list_file: str, datadir: str):
  (_, translations) = guess_matching.load_dictionary(datadir + "lexicon.norm")
  oov_original_list = guess_helper.load_file_lines(datadir + oov_original_list_file)
  oov_cheat_list    = guess_helper.load_file_lines(datadir + oov_cheat_list_file)
  
  all_translations = set(itertools.chain(*translations.values()))
  
  with open(datadir + oov_cheat_list_file + "_dictonly", 'w') as outfile:
    print("Writing to " + datadir + oov_cheat_list_file + "_dictonly")
    for (oov, trans) in zip(oov_original_list, oov_cheat_list):
      okay = all(map(lambda t: t in all_translations, trans.split()))
      print(trans if okay else oov, file=outfile)

def print_human_algo_statistics(ref: str, stats: ((int, int), (int, int, int, int))):
  # (Schema: count_human_algo)
  ((c_nn, c_ny), (c_yn, c_yw, c_yc, c_yy)) = stats
  print("{}> {:<27} {:3} ({})".format(ref, "No human, no algo:", \
    c_nn, "neither knew a translation"))
  print("{}> {:<27} {:3} ({})".format(ref, "No human, but algo:", \
    c_ny, "we're either superhuman or translated stray NEs"))
  print("{}> {:<27} {:3} ({})".format(ref, "Human, but no algo:", \
    c_yn, "didn't find any translation, but human did"))
  print("{}> {:<27} {:3} ({})".format(ref, "Human, but wrong algo:", \
    c_yw, "didn't find the human translation containing lexicon entry, but found another"))
  print("{}> {:<27} {:3} ({})".format(ref, "Human corrected algo:", \
    c_yc, "found the human suggestion containing lexicon entry, but wouldn't have chosen it"))
  print("{}> {:<27} {:3} ({})".format(ref, "Human = algo:", \
    c_yy, "found the human suggestion containing candidate and naturally chose it!"))

def load_files(files):
  # Load OOV list
  oov_original_list = guess_helper.load_file_lines(files.oovfile)
  # Load dictionary
  (matchers, translations) = guess_matching.load_dictionary(files.lexfile)
  # Load NE list
  # -> apparently untokenized! sucks e.g. for Mosoni-Dunaig
  nes = list(guess_helper.load_file_lines(files.nefile))
  # Load Morfessor splits
  morfoutput = guess_helper.load_file_lines(files.morffile)
  cleanmorfstring = lambda s: list(map(lambda seg: seg.split('|'), s.split()))
  catmorfdict = dict(zip(oov_original_list, map(cleanmorfstring, morfoutput)))
  
  # Load cheat/reference
  cheat_guesses = dict(zip(oov_original_list, guess_helper.load_file_lines(files.reffile)))

  return (oov_original_list, matchers, translations, nes, catmorfdict, cheat_guesses)

def doit(refname, outfile, oov_original_list, matchers, translations, nes, catmorfdict, cheat_guesses):
  # Start filling our guess dictionary!
  oov_guesses = {}

  # Sort oovlist entries into NEs and actual OOVs
  (guessable_nes, guessable_oovs) = guess_logic.get_guessables_into(oov_guesses, oov_original_list, nes)
  print("{} distinct NEs and {} distinct OOVs to guess.".format(len(guessable_nes), len(guessable_oovs)))
  
  # Guess NEs
  all_ne_roots = guess_nes.guess_nes_into(oov_guesses, catmorfdict, guessable_nes)


  #interesting_oovs = ["elöltött"] # ["iszap", "vörösiszap", "gipsszel", "iszapkatasztrófa", "katasztrófának", "Kolontárnál", "Devecseren"]
  #guess_logic.guess_actual_oovs_into(oov_guesses, interesting_oovs, matchers, translations, catmorfdict, cheat_guesses)
  #exit(0)


  # Then do the actual OOV guessing, while counting, how often were we "better" than the human
  stats = guess_logic.guess_actual_oovs_into(oov_guesses, guessable_oovs, matchers, translations, catmorfdict, cheat_guesses)
  print_human_algo_statistics(refname, stats)
  
  # Write our results in original order into result file
  with open(outfile, 'w') as translist:
    for oov in oov_original_list:
      print(oov_guesses[oov], file=translist)

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Guess OOVs.')
  parser.add_argument('oovfile' , help='<- original OOV list')
  parser.add_argument('morffile', help='<- morf-segmented/-categorized OOV list')
  parser.add_argument('lexfile' , help='<- normalized lexicon')
  parser.add_argument('nefile'  , help='<- NE list')
  parser.add_argument('reffile' , help='<- cheating reference translation')
  parser.add_argument('outfile' , help='-> output translation')
  parser.add_argument('weight1' , help='<-')
  parser.add_argument('weight2' , help='<-')
  parser.add_argument('weight3' , help='<-')
  args = parser.parse_args()
  
  #dict_only(oovfile, "mud.oovlist.trans_uniq_human", datadir)
  #dict_only(oovfile, "mud.oovlist.trans_uniq_reference", datadir)

  doit(args.reffile, args.outfile, *load_files(args))
