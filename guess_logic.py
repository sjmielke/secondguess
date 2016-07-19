from collections import Counter
import multiprocessing
from contextlib import closing
import itertools

import guess_phrases
import guess_matching

def get_guessables_into(oov_guesses: "{str: str}", fulllist: "[str]", ne_list: "[str]") -> "(Counter[str], Counter[str])":
	guessable_nes = Counter()
	guessable_oovs = Counter()
	for w in fulllist:
		# Filter out purely non-alphabetic tokens
		if not any(c.isalpha() for c in w):
			#print("{:<20} ~~> non-alpha token".format(w))
			oov_guesses[w] = [(w, 1.0)]
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
		leidos_unigrams: "Counter[str]",
		args: "argparse args"
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
	                        leidos_unigrams,
	                        args)
	with closing(multiprocessing.Pool(processes = 8)) as pool:
		guess_results = list(pool.starmap(guess_phrases.phraseguess_actual_oov, map(preproc, sorted_guessable_oovs)))
	all_results = sorted(zip(sorted_guessable_oovs, guess_results), key = lambda r: sum(r[1][0][1]), reverse = True)
	
	# What came out?
	count_nocheat_noalg = 0
	count_nocheat_yesalg = 0
	count_yescheat_noalg = 0
	count_yescheat_wrongalg = 0
	count_yescheat_correctedalg = 0
	count_yescheat_yesalg = 0
	
	for (oov, candidates) in all_results:
		(result, scores, algo_eq_human) = candidates[0]
		oov_guesses[oov] = list(map(lambda x: (x[0], sum(x[1])), candidates))
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
	
	for (oov, candidates) in all_results[0:20] + [("[...]", [("[...]", [], False)])] + all_results[-20:]:
		(result, scores, algo_eq_human) = candidates[0]
		print("{:>20} -> {:<20}".format(oov, result), end='')
		print("{:10.7f} <- ".format(sum(scores)), end='')
		for s in scores:
			print(" {:10.7f}".format(s), end='')
		if algo_eq_human:
			print(" (and correct!)", end='')
		print("")
	
	return ((count_nocheat_noalg, count_nocheat_yesalg), (count_yescheat_noalg, count_yescheat_wrongalg, count_yescheat_correctedalg, count_yescheat_yesalg))
