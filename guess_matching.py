from difflib import SequenceMatcher
from collections import defaultdict
import typing # NamedTuple
import itertools

from guess_helper import load_file_lines

CandidateWord = typing.NamedTuple('CandidateWord', [('oov', str), ('lexword', str), ('i_lex', int), ('i_oov', int), ('matchlength', int), ('islegal', bool)])



# mono2affix_min5_match3
def is_legal_match(w1: str, w2: str, i1: int, i2: int, l: int) -> bool:
	i2_ = len(w1) - (i1 + l)
	return l >= 3 and (l / len(w1) > 0.9 or (i1 == 0 or i2_ == 0) and i1 + i2_ <= 2 and l >= 5)

def load_dictionary(path: str) -> ("Dict[str: SequenceMatcher]", "Dict[str: Set[str]]"):
	matchers = {}
	translations = defaultdict(set)
	for line in load_file_lines(path):
		(w, _, t) = line.split('\t')
		matchers[w] = SequenceMatcher(a=None, b=w, autojunk=False)
		translations[w].add(t)
	#print("{} distinct dictionary words to compare against loaded.".format(len(matchers.keys())))
	return (matchers, translations)

def get_best_match(oov: str, lexword: str, matcher: SequenceMatcher) -> (str, (int, int, int)):
	matcher.set_seq1(oov)
	i_o, i_w, matchlength = matcher.find_longest_match(0, len(oov), 0, len(lexword))
	return (lexword, (i_o, i_w, matchlength))

def lookup_oov(oov: str, matchers: "{str: SequenceMatcher}") -> "[CandidateWord]":
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
		if found_legal and (matchlength < 3 or matchlength < best_matchlength):
			continue
		legal = is_legal_match(lexword, oov, i_w, i_o, matchlength)
		if not found_legal or legal: # no legality regressions!
			if (legal and not found_legal # we find our first legal match...
					or matchlength > best_matchlength): # ...or a better one, regardless of legality status
				best_lexcandidates = [CandidateWord(oov, lexword, i_w, i_o, matchlength, legal)]
				best_matchlength = matchlength
			elif matchlength == best_matchlength: # no improvement? just add a candidate
				best_lexcandidates.append(CandidateWord(oov, lexword, i_w, i_o, matchlength, legal))
		if legal:
			found_legal = True
	#print("!")
	#print(" ")
	
	# If we didn't find anything legal, guess we just copy:
	if not found_legal:
		return [CandidateWord(oov, oov, -1, -1, len(oov), False)]
	else:
		return best_lexcandidates
