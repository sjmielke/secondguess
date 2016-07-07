from contextlib import closing
from collections import Counter
import multiprocessing
import itertools

import guess_phrases
import guess_matching

def lookup_morf_combinations(catmorfdict: "{str: [(str, str)]}", matchers: "{str: SequenceMatcher}") -> "{str: [CandidateWord]}":
	all_phrases = []
	for _, segs in catmorfdict.items():
		all_phrases += itertools.chain(*guess_phrases.gen_phrases(segs))
	# http://stackoverflow.com/questions/10784390/python-eliminate-duplicates-of-list-with-unhashable-elements-in-one-line
	uniq_phrases = [k for k,v in itertools.groupby(sorted(all_phrases))]
	print("Matching {} ({} unique) phrases generated from {} unique words".format(len(all_phrases), len(uniq_phrases), len(catmorfdict.keys())))
	with closing(multiprocessing.Pool(processes = 4)) as pool:
		return dict(zip(all_phrases, pool.starmap(guess_matching.lookup_oov, zip(all_phrases, itertools.repeat(matchers)))))

def get_guessables_into(guesses: "{str: str}", fulllist: "[str]", ne_list: "[str]") -> "(Counter[str], Counter[str])":
	guessable_nes = Counter()
	guessable_oovs = Counter()
	for w in fulllist:
		# Filter out non-alphabetic tokens
		if not any(c.isalpha() for c in w):
			#print("{:<20} ~~> non-alpha token".format(w))
			guesses[w] = w
		elif w in ne_list:
			guessable_nes[w] += 1
		else:
			guessable_oovs[w] += 1
	return (guessable_nes, guessable_oovs)

def guess_actual_oovs_into(
		oov_guesses: "{str: str}",
		raw_guessable_oovs: "Counter[str]",
		all_matches: "{str: [CandidateWord]}",
		translations: "{str: Set[str]}",
		catmorfdict: "{str: [(str, str)]}",
		cheat_guesses: "{str: str}",
		train_target: "Counter[str]",
		leidos_unigrams: "Counter[str]"
	) -> ((int, int), (int, int, int)):
	# Sort
	sorted_guessable_oovs = sorted(list(raw_guessable_oovs))
	# Do
	preproc = lambda oov: ( oov,
	                        all_matches,
	                        translations,
	                        catmorfdict,
	                        cheat_guesses,
	                        raw_guessable_oovs,
	                        train_target,
	                        leidos_unigrams)
	#with closing(multiprocessing.Pool(processes = 4)) as pool:
	guess_results = list(itertools.starmap(guess_phrases.phraseguess_actual_oov, map(preproc, sorted_guessable_oovs)))
	all_results = sorted(zip(sorted_guessable_oovs, guess_results), key = lambda r: sum(r[1][1]), reverse = True)
	
	# What came out?
	count_nocheat_noalg = 0
	count_nocheat_yesalg = 0
	count_yescheat_noalg = 0
	count_yescheat_wrongalg = 0
	count_yescheat_correctedalg = 0
	count_yescheat_yesalg = 0
	
	for (oov, (result, scores, algo_eq_human)) in all_results:
		oov_guesses[oov] = result
		if cheat_guesses[oov] == oov: # human didn't know
			if algo_eq_human:
				count_nocheat_noalg += 1
			else:
				count_nocheat_yesalg += 1
		else: # human knew a translation
			if result == oov:
				count_yescheat_noalg += 1
			elif result != cheat_guesses[oov]:
				count_yescheat_wrongalg += 1
			elif not algo_eq_human:
				count_yescheat_correctedalg += 1
			else:
				count_yescheat_yesalg += 1
	
	for (oov, (result, scores, algo_eq_human)) in all_results[0:20] + [("[...]", ("[...]", [], False))] + all_results[-20:]:
		print("{:>20} -> {:<20}".format(oov, result), end='')
		for s in scores:
			print(" {:10.7f}".format(s), end='')
		if algo_eq_human:
			print(" (and correct!)", end='')
		print("")
	
	with open("/tmp/scores", 'w') as o:
		for (oov, (result, scores, algo_eq_human)) in all_results:
			print("{}\t{}\t{}\t{}".format(*scores, 0.2 if algo_eq_human else -0.1), file = o)
	
	return ((count_nocheat_noalg, count_nocheat_yesalg), (count_yescheat_noalg, count_yescheat_wrongalg, count_yescheat_correctedalg, count_yescheat_yesalg))
