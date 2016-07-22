from scoop import futures, shared
from difflib import SequenceMatcher
from contextlib import closing
import typing # NamedTuple
import itertools
import sys
import argparse

import guess_helper
import guess_phrases

CandidateWord = typing.NamedTuple('CandidateWord', [('oov', str), ('lexword', str), ('i_lex', int), ('i_oov', int), ('matchlength', int), ('islegal', bool)])

# mono3affix_min6_match4 per word
def is_legal_match(s: str, i: int, l: int) -> bool:
	# First, find the two actually matching words of the string
	# Only one word? Then it's easy.
	if " " in s:
		for w in s.split():
			if len(w) <= i:
				i -= len(w) + 1
				continue
			# It can only be contained in this word!
			s = w
			break
	
	rest1 = i
	rest2 = len(s) - (i + l)
	
	return l >= 4 and (l / len(s) > 0.65 or (rest1 == 0 or rest2 == 0) and rest1 + rest2 <= 3 and l >= 6)

def get_best_match(oov: str, lexword: str, matcher: SequenceMatcher) -> (str, (int, int, int)):
	matcher.set_seq1(oov)
	i_o, i_w, matchlength = matcher.find_longest_match(0, len(oov), 0, len(lexword))
	return (lexword, (i_o, i_w, matchlength))

def lookup_oov(oov: str, matchers: "{str: SequenceMatcher}") -> "(str, [CandidateWord])":
	print("Looking up", oov, "...", end = '', flush = True)
	
	# Match search
	nextbest_lexcandidates = []
	nextbest_matchlength = 0
	best_lexcandidates = []
	best_matchlength = 0
	found_legal = False
	
	# First find LCS = match with lexword in a mapreduce fashion
	all_pairs = map(lambda w: (oov, w, matchers[w]), sorted(matchers.keys()))
	
	individual_bestmatches = itertools.starmap(get_best_match, all_pairs)
	
	print("...", end = '', flush = True)
	
	# Now compare all findings!
	for (lexword, (i_o, i_w, matchlength)) in individual_bestmatches:
		if found_legal and (matchlength < 3 or matchlength < best_matchlength):
			continue
		legal = is_legal_match(lexword, i_w, matchlength)
		if not found_legal or legal: # no legality regressions!
			if (legal and not found_legal # we find our first legal match...
					or matchlength > best_matchlength): # ...or a better one, regardless of legality status
				# Also get some more
				nextbest_lexcandidates = best_lexcandidates
				nextbest_matchlength = best_matchlength
				# Then update best
				best_lexcandidates = [CandidateWord(oov, lexword, i_w, i_o, matchlength, legal)]
				best_matchlength = matchlength
			elif matchlength == best_matchlength: # no improvement? just add a candidate
				best_lexcandidates.append(CandidateWord(oov, lexword, i_w, i_o, matchlength, legal))
		if legal:
			found_legal = True
	
	print("done!", flush = True)
	
	# If we didn't find anything legal, guess we just copy:
	if not found_legal or len(best_lexcandidates) > 75: # matching too much can't be right
		return (oov, [CandidateWord(oov, oov, -1, -1, len(oov), False)])
	elif nextbest_matchlength > 3 and nextbest_matchlength + 1 == best_matchlength and len(nextbest_lexcandidates) < 30:
		return (oov, best_lexcandidates + nextbest_lexcandidates)
	else:
		return (oov, best_lexcandidates)



if __name__ == '__main__':
	# Load matchers
	conf = guess_helper.load_config(None)
	(matchers, _) = guess_helper.load_dictionary(conf['global-files']['lexicon'])
	shared.setConst(matchers = matchers)
	
	all_uniq_phraseparts = sys.stdin.read().splitlines()
	print("Found", len(all_uniq_phraseparts), "phraseparts...", file = sys.stderr)
	
	# Filter those out that are already present in the matchfile
	try:
		with open(conf['global-files']['allmatches']) as f:
			prev_matches = eval(f.read())
	except:
		prev_matches = {}
	
	new_uniq_phraseparts = list(filter(lambda p: p not in prev_matches, all_uniq_phraseparts))
	print("... of which", len(new_uniq_phraseparts), "are new ones!", file = sys.stderr)
	
	result = dict(futures.map(lookup_oov, new_uniq_phraseparts))
	
	prev_matches.update(result)
	
	with open(conf['global-files']['allmatches'], 'w') as f:
		print(prev_matches, file = f)
