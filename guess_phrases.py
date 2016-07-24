from scoop import futures, shared
import itertools
import operator # mul
import sys # stderr
from functools import reduce

import guess_helper
import guess_choice

def no_useless_suffix(s):
	return s not in ["ماق", "ىش", "دى", "تى", "دۇ", "تۇ", "دۈ", "تۈ", "غان", "قان", "گەن", "كەن", "غۇز", "قۇز", "گۈز", "كۇز", "دۇر", "تۇر", "دۈر", "تۈر", "لار", "لەر", "لىر", "نى", "لىق", "لىك", "لۇق", "لۈك", "سى", "ى", "كى", "مۇ", "مۇ", "ئىدى"]

def gen_phrases(segments: "[(str, str)]") -> "[[str]]":
	segs_texts = list(guess_helper.mapfst(segments))
	
	#print("Generating for ", segs_texts)
	
	fulloov = "".join(segs_texts)
	
	for s in ["t.co/", "://", "@"]:
		if s in fulloov:
			return [[fulloov]]
	if len(segs_texts) > 10:
		print("»{}« was longer than 10 segments!".format(" + ".join(segs_texts)), file = sys.stderr)
		return [[fulloov]]
	
	result = []
	for sl in itertools.product(*([["", " "]] * (len(segs_texts) - 1))):
		components = list(itertools.chain(*zip(segs_texts, sl))) + [segs_texts[-1]]
		phrase = ("".join(list(filter(no_useless_suffix, components)))).split()
		if phrase != [] and len(phrase) <= 4:
			#print("   ", phrase)
			result.append(phrase)
	
	return sorted(guess_helper.uniq_list(result))

def phraseguess_actual_oov(
		oov: str,
		debug_print: bool = True
	) -> (str, float, bool):
	
	static_data = shared.getConst('static_data')
	(all_matches, # {str: [CandidateWord]}
		translations, # {str: [str]}
		catmorfdict, # {str: [(str, str)]}
		cheat_guesses, # {str: str}
		all_oovs, # Counter[str]
		train_target, # Counter[str]
		leidos_unigrams, # Counter[str]
		conf) = static_data

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
		
		all_translations += guess_choice.score_full_phrase_translations(oov, all_candidates, translations, cheat_guesses, all_oovs, train_target, leidos_unigrams, conf['scoring-weights'], debug_print)
	
	# Also allow full copying and deletion
	all_translations.append(("",  [conf['scoring-weights']['deletionscore']], cheat_guesses[oov] == ""))
	all_translations.append((oov, [conf['scoring-weights']['copyscore']],     cheat_guesses[oov] == oov))
	
	# Return best translation!
	res = sorted(all_translations, key = lambda x: sum(x[1]), reverse = True)
	
	# Or the correct one, if it was returned
	for (t, score, aeh) in all_translations:
		if t == cheat_guesses[oov]:
			res = [(t, score, aeh)]
	
	# Or return the word itself, if the OOV wasn't arabic script!
	if not any(map(lambda c: ord(c) >= 1536 and ord(c) <= 1791, oov)):
		res = [(oov, [1.0 + sum(res[0][1])], cheat_guesses[oov] == oov)] + res
	
	if debug_print:
		print(" « {} {:<30}".format('=' if res[0][2] else ' ', res[0][0]))
	
	# Filter duplicate hypotheses, keep best one
	transset = set()
	dupfree_result = []
	for (t, scores, aeh) in res:
		if t not in transset:
			dupfree_result.append((t, scores, aeh))
			transset.add(t)
	
	return dupfree_result

if __name__ == "__main__":
	conf = guess_helper.load_config(sys.argv[1])
	
	# First load data
	oov_original_list = guess_helper.load_file_lines(conf['set-files']['oovfile'])
	catmorfdict = guess_helper.load_catmorfdict(oov_original_list, conf['set-files']['catmorffile'])
	
	# Then generate all phrases
	all_phraseparts = []
	for _, segs in catmorfdict.items():
		all_phraseparts += itertools.chain(*gen_phrases(segs))
	uniq_phraseparts = guess_helper.uniq_list(all_phraseparts) # uniq for unhashable lists!
	print("Matching {} ({} unique) phrases generated from {} unique words".format(len(all_phraseparts), len(uniq_phraseparts), len(catmorfdict.keys())), flush = True, file = sys.stderr)
	
	# ... to stdout!
	print("\n".join(uniq_phraseparts))
