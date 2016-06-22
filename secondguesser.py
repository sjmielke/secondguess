import difflib
from collections import defaultdict
import sys

def bold(s: str, i: int, k: int) -> str:
  return "\x1b[2m" + s[0:i] + "\x1b[1m" + s[i:i+k] + "\x1b[2m" + s[i+k:] + "\x1b[0m"

def desuffixize_ne(ne: str) -> str:
  return ne

def is_legal_match(w1: str, w2: str, i1: int, i2: int, l: int) -> bool:
  justsmallaffix = lambda a,b: (a == 0 or b == 0) and a + b <= 2
  if w1 == "tározó":
    print((i1, len(w1) - (i1 + l)))
  w1_ok = l / len(w1) > 0.9 or justsmallaffix(i1, len(w1) - (i1 + l)) and l >= 5
  w2_ok = l / len(w2) > 0.9 or justsmallaffix(i2, len(w2) - (i2 + l)) and l >= 5
  if sys.argv[1] == "mono2affix_min5":
    return w1_ok
  elif sys.argv[1] == "anyaffix":
    return True
  elif sys.argv[1] == "noaffix":
    return l == len(w1)
  elif sys.argv[1] == "mono2affix_min5_both":
    return w1_ok and w2_ok
  else:
    print(sys.argv[1] + "is no real suffix")
    exit(1)

# 495 OOVs, 143156 lexicon entries
# => 0:14:47 runtime on my laptop, so ~1.79s per OOV
# => 0:06:33 with 53857 unified dict entries, so ~0.79s per OOV
# => 0:05:11 with 361 unified OOVs, so ~0.86s per OOV
# => 0:04:27 after beautifying and some fixing, so ~0.74s per OOV
# => 0:04:34 after I realized something was different and fiddled with *everything*, eventually yielding richer results
# => 0:05:04 after streamlining the legality checks, thereby finding even more matches

translations = defaultdict(list)
matchers = {}
with open("/home/sjm/documents/ISI/oovextractor/hundata/lexicon.norm") as dict_hun:
  for line in dict_hun.read().splitlines():
    (w, tag, t) = line.split('\t')
    translations[w].append(t)
    matchers[w] = difflib.SequenceMatcher(a=None, b=w, autojunk=False)

print("{} distinct dictionary words to compare against loaded.\n".format(len(matchers.keys())))

# These seem to be untokenized! That sucks e.g. for Mosoni-Dunaig
with open("/home/sjm/documents/ISI/oovextractor/guesser/rpi_ne__dryrun_submission/run1.tab.sws") as ne_list:
  nes = ne_list.read().splitlines()

oov_original_list = []
oov_guesses = {}
with open("/home/sjm/documents/ISI/oovextractor/hunalign/mudeval.align.oovlist") as oovlist_file:
  for oov in oovlist_file.read().splitlines():
    oov_original_list.append(oov)

oov_uniq = sorted(list(set(oov_original_list)))

guessable_oovs = []
guessable_nes = []
for w in oov_uniq:
  # Filter out non-alphabetic tokens
  if not any(c.isalpha() for c in w):
    print("{:<20} ~~> non-alpha token".format(w))
    oov_guesses[w] = w
  # NE check
  elif w in nes:
    guessable_nes.append(w)
  else:
    guessable_oovs.append(w)

print("\n{} distinct NEs and {} distinct OOVs to guess.\n".format(len(guessable_nes), len(guessable_oovs)))

# First desuffixize/group -> guess all NEs
for ne_suf in guessable_nes:
  ne = desuffixize_ne(ne_suf)
  print("{:<20} ~~> is NE           {} -> {:<20}".format(ne, '✔' if ne == ne_suf else '✗', ne))
  oov_guesses[ne_suf] = ne

# Then do the actual OOV guessing!
i = 0
for oov in guessable_oovs:
  i += 1
  print("({:3}/{:3}) ".format(i, len(guessable_oovs)), end='')
  # Match search
  bestmatch_lexword = 'X'*40
  bestmatch_matchlength = 0
  bestmatch_lexindex = 0
  bestmatch_oovindex = 0
  # If you think about it, this is basically mapreduce, so use sth. like:
  # http://stackoverflow.com/questions/1704401/is-there-a-simple-process-based-parallel-map-for-python
  found_legal = False
  for lexword in sorted(matchers.keys()):
    # First find LCS = match with lexword
    matcher = matchers[lexword]
    matcher.set_seq1(oov)
    i_o, i_w, matchlength = matcher.find_longest_match(0, len(oov), 0, len(lexword))
    # Otherwise, see if it's better than our current candidate(s)
    legal = is_legal_match(lexword, oov, i_w, i_o, matchlength)
    if legal and not found_legal:
      found_legal = True
    if ((not found_legal or legal) and ( # no legality regressions!
        matchlength >  bestmatch_matchlength or # more match is always better...
        matchlength == bestmatch_matchlength and len(lexword) < len(bestmatch_lexword) # ...otherwise prefer shorter lexwords
       )):
      bestmatch_lexword = lexword
      bestmatch_matchlength = matchlength
      bestmatch_lexindex = i_w
      bestmatch_oovindex = i_o
  dowe = is_legal_match(bestmatch_lexword, oov, bestmatch_lexindex, bestmatch_oovindex, bestmatch_matchlength)
  # My debug output
  if bestmatch_matchlength != 0:
    perc_lex = bestmatch_matchlength / len(bestmatch_lexword)
    perc_oov = bestmatch_matchlength / len(oov)
    print("{:<36}{:<36}".format( # 20 + 4 * 4 = 36
        bold(oov              , bestmatch_oovindex, bestmatch_matchlength),
        bold(bestmatch_lexword, bestmatch_lexindex, bestmatch_matchlength)), end='')
    if dowe:
      # Now actually figure out the best translation
      besttranslation = min(sorted(translations[bestmatch_lexword]), key=len) # sorted for determinism
      print(" {} -> {:<20} ({:4.0%} of lexword, {:4.0%} of OOV)".format('✔', besttranslation, perc_lex, perc_oov))
      oov_guesses[oov] = besttranslation
    else:
      print(" {}    {:<20} ({:4.0%} of lexword, {:4.0%} of OOV)".format('✗', "", perc_lex, perc_oov))
      oov_guesses[oov] = oov
  else:
    print("{:<20} ~~> none found!".format(oov))
    oov_guesses[oov] = oov

# Write our results in original order
with open("/home/sjm/documents/ISI/oovextractor/hunalign/mudeval.align.oovlist.trans_pysub_"+sys.argv[1], 'w') as translist:
  for oov in oov_original_list:
    print(oov_guesses[oov], file=translist)
