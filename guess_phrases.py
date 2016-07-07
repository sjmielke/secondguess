import itertools
import operator # mul, itemgetter
from functools import reduce

from guess_helper import mapfst
import guess_choice

def gen_phrases(segments: "[(str, str)]") -> "[[str]]":
	segs_texts = list(mapfst(segments))
	for sl in itertools.product(*([["", " "]] * (len(segs_texts) - 1))):
		yield ("".join(list(itertools.chain(*zip(segs_texts, sl))) + [segs_texts[-1]])).split()
		# break # only full

def phraseguess_actual_oov(
		oov: str,
		all_matches: "{str: [CandidateWord]}",
		translations: "{str: [str]}",
		catmorfdict: "{str: [(str, str)]}",
		cheat_guesses: "{str: str}",
		all_oovs: "Counter[str]",
		train_target: "Counter[str]",
		leidos_unigrams: "Counter[str]",
		debug_print: bool = True,
	) -> (str, float, bool):
	
	all_translations = []
	if debug_print:
		print("\n")
	for phrase in gen_phrases(catmorfdict[oov]):
		candidatess = []
		for phrase_segment in phrase:
			candidatess.append(all_matches[phrase_segment])
		
		lengths = list(map(len, candidatess))
		statstring = " x ".join(map(str, lengths)) + " = {}".format(reduce(operator.mul, lengths, 1))
		if debug_print:
			print (" » {:<20} » {:<20}".format(" ".join(phrase), statstring), end='', flush=True)
		
		all_candidates = list(itertools.product(*candidatess))
		
		all_translations.append(guess_choice.choose_full_phrase_translation(all_candidates, translations, cheat_guesses, all_oovs, train_target, leidos_unigrams, debug_print))
	
	# Return best translation!
	res = max(all_translations, key = lambda x: sum(x[1]))
	
	# Or the correct one, if it was returned
	for (t, score, aeh) in all_translations:
		if t == cheat_guesses[oov]:
			res = (t, score, aeh)
	
	if debug_print:
		print(" « {} {:<30}".format('=' if res[1] else ' ', res[0]))
	
	return res
