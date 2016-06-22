import sys

from guess_helper   import load_file_lines, bold
import guess_matching
import guess_nes
import guess_logic

datadir = "/home/sjm/documents/ISI/pyguess/data/"

# Load a bunch of things
(matchers, translations) = guess_matching.load_dictionary(datadir + "lexicon.norm")
nes = load_file_lines(datadir + "mudeval.unique_nes.r1") # apparently untokenized! sucks e.g. for Mosoni-Dunaig
oov_original_list = load_file_lines(datadir + "mud.oovlist")
cheat_guesses = dict(zip(oov_original_list, load_file_lines(datadir + "mud.oovlist.trans_sw_uniq_human_dictonly")))

# Start filling our guess dictionary!
oov_guesses = {}

(guessable_nes, guessable_oovs) = guess_logic.get_guessables_into(guesses = oov_guesses, fulluniqlist = oov_original_list, ne_list = nes)
print("{} distinct NEs and {} distinct OOVs to guess.\n".format(len(guessable_nes), len(guessable_oovs)))

# Guess NEs
all_ne_roots = guess_nes.guess_nes_into(guesses = oov_guesses, nes = guessable_nes)

# Then do the actual OOV guessing!
i = 0
# How often were we "better" than the human?
count_nocheat_noalg = 0
count_nocheat_yesalg = 0
count_yescheat_noalg = 0
count_yescheat_wrongalg = 0
count_yescheat_yesalg = 0
for oov in sorted(guessable_oovs):
  i += 1
  print("({:3}/{:3}) ".format(i, len(guessable_oovs)), end='')
  # Match search
  #bestmatch_lexword = 'X'*40
  best_lexcandidates = []
  best_matchlength = 0
  # If you think about it, this is basically mapreduce, so use sth. like:
  # http://stackoverflow.com/questions/1704401/is-there-a-simple-process-based-parallel-map-for-python
  found_legal = False
  for lexword in sorted(matchers.keys()):
    # First find LCS = match with lexword
    matcher = matchers[lexword]
    matcher.set_seq1(oov)
    i_o, i_w, matchlength = matcher.find_longest_match(0, len(oov), 0, len(lexword))
    
    # Otherwise, see if it's better than our current candidate(s)
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
      if what_the_algo_says == cheat_guesses[oov]:
        count_yescheat_yesalg += 1
      else:
        count_yescheat_wrongalg += 1
    else: # cheat=copy
      count_nocheat_yesalg += 1
    
    # Okay, now check that it's alright
    dowe = guess_matching.is_legal_match(lexword, oov, lexindex, oovindex, best_matchlength)
    perc_lex = best_matchlength / len(lexword)
    perc_oov = best_matchlength / len(oov)
    print("{:<36}{:<36}".format( # 20 + 4 * 4 = 36
        bold(oov    , oovindex, best_matchlength),
        bold(lexword, lexindex, best_matchlength)), end='')
    
    if dowe:
      oov_guesses[oov] = besttranslation
    else:
      oov_guesses[oov] = oov
    
    iseq = (oov_guesses[oov] == cheat_guesses[oov]) # should be a consequence of copying!
    
    print(" {} {} {}    {:<20} ({:4.0%} of lexword, {:4.0%} of OOV)".format(\
      '✔' if dowe else '✗',\
      '❗' if foundcheat else ' ',\
      '=' if iseq else ' ',\
      besttranslation if dowe else "",\
      perc_lex, perc_oov))
  else:
    print("{:<20} ~~> none found!         {}".format(oov, '=' if cheat_guesses[oov] == oov else ' '))
    oov_guesses[oov] = oov
    # Statistics
    if cheat_guesses[oov] != oov:
      count_yescheat_noalg += 1
    else:
      count_nocheat_noalg += 1

# Statistics
print("{}) {:<25} {:3} ({})".format(sys.argv[1],\
  "No cheat, no algo:", count_nocheat_noalg, "neither knew a translation"))
print("{}) {:<25} {:3} ({})".format(sys.argv[1],\
  "No cheat, but algo:", count_nocheat_yesalg, "we're either superhuman or translated stray NEs"))
print("{}) {:<25} {:3} ({})".format(sys.argv[1],\
  "Cheat, but no algo:", count_yescheat_noalg, "didn't find any candidate, but human did"))
print("{}) {:<25} {:3} ({})".format(sys.argv[1],\
  "Cheat, but wrong algo:", count_yescheat_wrongalg, "didn't find the human suggestion containing candidate, but found something else"))
print("{}) {:<25} {:3} ({})".format(sys.argv[1],\
  "Cheat = algo:", count_yescheat_yesalg, "found the human suggestion containing candidate!"))

# Write our results in original order
with open(datadir + "mud.oovlist.trans_" + sys.argv[1], 'w') as translist:
  for oov in oov_original_list:
    print(oov_guesses[oov], file=translist)
