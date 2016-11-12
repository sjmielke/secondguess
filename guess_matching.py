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

def lookup_oov(oov: str, matchers) -> "(str, [CandidateWord])":
	print("Looking up", oov, "...", end = '', flush = True, file = sys.stderr)
	
	# Match search
	nextbest_lexcandidates = []
	nextbest_matchlength = 0
	best_lexcandidates = []
	best_matchlength = 0
	found_legal = False
	
	# First find LCS = match with lexword in a mapreduce fashion
	all_pairs = map(lambda w: (oov, w, matchers[w]), sorted(matchers.keys()))
	
	individual_bestmatches = list(itertools.starmap(get_best_match, all_pairs))
	
	print("...", end = '', flush = True, file = sys.stderr)
	
	# Now compare all findings!
	all_lexcandidates = sorted([CandidateWord(oov, lexword, i_w, i_o, matchlength, is_legal_match(lexword, i_w, matchlength)) for (lexword, (i_o, i_w, matchlength)) in individual_bestmatches], key = lambda cw: cw.matchlength, reverse = True)
	
	if all_lexcandidates == []:
		return (oov, [])
	
	best_matchlength = all_lexcandidates[0].matchlength
	cur_matchlength  = all_lexcandidates[0].matchlength
	cur_wordcount = 0
	cur_wordlist = []
	result = []
	
	for cw in all_lexcandidates[:500]:
		if cw.matchlength == cur_matchlength:
			cur_wordcount += 1
		else:
			cur_matchlength = cw.matchlength
			cur_wordcount = 1
			result += cur_wordlist
			cur_wordlist = []
		if cur_wordcount > 75 or cur_matchlength + 4 < best_matchlength:
			break
		
		cur_wordlist.append(cw)
	
	print("done!", flush = True, file = sys.stderr)
	
	return (oov, result)

# STDIN: phraseparts
# STDOUT: match dict items
if __name__ == '__main__':
	# Load matchers
	conf = guess_helper.load_config(None)
	(matchers, _) = guess_helper.load_dictionary(conf['global-files']['lexicon'])
	
	# Read 'em all from stdin!
	all_uniq_phraseparts = guess_helper.uninorm(sys.stdin.read()).splitlines()
	print("Found", len(all_uniq_phraseparts), "phraseparts...", file = sys.stderr)
	
	# Filter those out that are already present in the matchfile
	try:
		# Load previously calculated matches
		with open(conf['global-files']['allmatches']) as f:
			prev_matches = dict([eval(guess_helper.uninorm(t)) for t in f.read().splitlines()])
	except:
		prev_matches = {}
	
	new_uniq_phraseparts = [p for p in all_uniq_phraseparts if p not in prev_matches]
	print("... of which", len(new_uniq_phraseparts), "are new ones!", file = sys.stderr)
	
	result = dict([lookup_oov(pp, matchers) for pp in new_uniq_phraseparts])
	
	prev_matches.update(result)
	
	for i in sorted(prev_matches.items(), key = lambda t: t[0]):
		print(i)
