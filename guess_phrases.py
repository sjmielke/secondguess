import itertools
import operator # mul
import sys # stderr
from functools import reduce

import guess_helper
import guess_choice

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
		phrase = ("".join(components)).split()
		if phrase != [] and len(phrase) <= 4:
			result.append(phrase)
	
	return sorted(guess_helper.uniq_list(result))

def phraseguess_actual_oov(
		oov: str,
		static_data,
		debug_print: bool = True
	) -> [(str, float, bool)]:
	
	(all_matches, # {str: [CandidateWord]}
		translations, # {str: [str]}
		catmorfdict, # {str: [(str, str)]}
		all_oovs, # Counter[str]
		train_target, # Counter[str]
		leidos_unigrams, # Counter[str]
		(adjectivizers, prefixers, suffixers, untranslatables, noun_adjective_dict), # ([str], [(str, str)], [(str, str)], [str], {str: str})
		conf) = static_data
	
	if debug_print:
		print("\n")
	
	data = [(oov, phrase, static_data, debug_print) for phrase in gen_phrases(catmorfdict[oov])]
	
	all_translations = list(itertools.chain(*list(itertools.starmap(guess_choice.score_full_phrase_matches, data))))
	
	# Also allow full copying and deletion
	all_translations.append({'translation': "",
	                         'score': conf['scoring-weights']['deletionscore'],
	                         'features': {'deletionscore': conf['scoring-weights']['deletionscore']},
	                         'lexwords': ""})
	all_translations.append({'translation': oov,
	                         'score': conf['scoring-weights']['copyscore'],
	                         'features': {'copyscore': conf['scoring-weights']['copyscore']},
	                         'lexwords': ""})
	
	# Return best translation!
	result = sorted(all_translations, key = lambda x: x['score'], reverse = True)
	
	if debug_print:
		print(" « {:<30}".format(result[0]['translation']))
	
	# Filter duplicate hypotheses, keep best one
	transset = set()
	dupfree_result = []
	for d in result:
		if d['translation'] not in transset:
			dupfree_result.append(d)
			transset.add(d['translation'])
	
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
