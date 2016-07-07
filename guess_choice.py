import itertools
from math import log

import guess_helper

import sys

def print_dups(ss, prefix = ""):
	s = ss #s = list(filter(lambda c: c.islegal, ss))
	if len(list(s)) != len(list(set(s))):
		print(prefix + "{} -> {}".format(len(list(s)), len(list(set(s)))))

def choose_full_phrase_translation(
		unsorted_candidates: "[[CandidateWord]]",
		translations: "{str: Set[str]}",
		cheat_guesses: "{str: str}",
		all_oovs: "Counter[str]",
		train_target: "Counter[str]",
		leidos_unigrams: "Counter[str]",
		debug_print: bool = False
	) -> (str, "Tuple[float]", bool):
	
	#### HELPER FUNCTIONS
	
	def translate_candidate(candidate: "[CandidateWord]") -> "[[(CandidateWord, str)]]":
		translationss = []
		for cw in candidate:
			cw_translations = [(cw, t) for t in translations[cw.lexword]] if cw.islegal else [(cw, cw.oov)]
			print_dups(cw_translations, "cw_trans: ")
			translationss.append(cw_translations)
		result = list(itertools.product(*translationss))
		for c in result:
			if tuple(guess_helper.mapfst(c)) != candidate:
				print("{} != \n{}".format(list(guess_helper.mapfst(c)), candidate))
				exit(1)
		#print_dups(result, "translate_candidate / result: ")
		return result
	
	def get_trans(transcandidate: "[(CandidateWord, str)]") -> str: return " ".join(map(lambda c: c[1], transcandidate))
	
	def score_phrase(cand: "[(CandidateWord, str)]") -> float:
		cws = list(guess_helper.mapfst(cand))
		
		# SOURCE SIDE FEATURES
		
		# each illegal result results in penalty
		nomatch_penalty = 0.07 * sum(map(lambda w: 0 if w.islegal else 1, cws))
		# prefer more OOV coverage (sum of matchlength [not translating is a full match!] by total oov length)
		coverage = 0.15 * sum(map(lambda w: w.matchlength, cws)) / sum(map(lambda w: len(w.oov), cws))
		# prefer shorter lexwords
		lexlengths_penalty = 0.002 * sum(map(lambda w: len(w.lexword), cws))
		# reward hungarian subwords that also are OOVs
		part_count = 0.001 * sum(map(lambda w: all_oovs[w.oov], cws))
		
		
		# TARGET SIDE FEATURES
		
		# reward new english words (justified OOVs) - more precise: words that contain new stuff!
		training_count_penalty = min(map(lambda c: 0.000000005 * log(1 + train_target[c[1]]), cand))
		# reward english in-domain words
		# -> need domain-word-list
		
		# average LEIDOS frequency (surrogate for both in-domain-ness and general language model!) - only works for single words
		leidos_frequencies = list(map(lambda trans: leidos_unigrams[trans], itertools.chain(*map(lambda c: c[1].split() if c[1].split() != [] else [c[1]], cand))))
		leidos_frequency = 0.000000001 * sum(leidos_frequencies) / len(leidos_frequencies)
		
		# Combine the following two:?
		# reward more common english words
		# -> need some huge unigram model
		# reward high-LM and punish low-LM phrases
		# -> need a good english LM
		
		tiebreaker_hashes = list(map(hash, cand))
		tiebreaker = 0.0000000000000000000000000000000001 * sum(tiebreaker_hashes) / len(tiebreaker_hashes)
		
		return (float(sys.argv[-6]) * -1 * nomatch_penalty,
		        float(sys.argv[-5]) *      coverage,
		        float(sys.argv[-4]) * -1 * lexlengths_penalty,
		        float(sys.argv[-3]) *      part_count,
		        float(sys.argv[-2]) * -1 * training_count_penalty,
		        float(sys.argv[-1]) *      leidos_frequency,
		        tiebreaker)
	
	#### ACTUAL CHOICE PROCESS
	
	# Now, first we have to evaluate the candidates into translation candidates!
	translated_unsorted_candidates = list(itertools.chain(*list(map(translate_candidate, unsorted_candidates))))
	
	print_dups(translated_unsorted_candidates)
	# Then pick our favorite one!
	scored = sorted(translated_unsorted_candidates, key = lambda p: sum(score_phrase(p)), reverse = True)
	if len(scored) > 1 and sum(score_phrase(scored[0])) == sum(score_phrase(scored[1])):
		if scored[0] == scored[1]:
			print("WATTAFUK")
		else:
			print("TiE!\n{}\n{}\n".format(*scored[0:2]))
	besttranscand = scored[0]
	phrase = list(map(lambda cw: cw.oov, guess_helper.mapfst(besttranscand)))
	fullphrase = "".join(phrase)
	
	# First, what would the algo itself say?
	what_the_algo_said = get_trans(besttranscand)
	result_transcandidate = besttranscand
	
	# Now, can I find the "correct" solution? Then replace old result with it!
	foundcheat = False
	cheatsolution = cheat_guesses[fullphrase]
	for transcandidate in translated_unsorted_candidates:
		if get_trans(transcandidate) == cheatsolution:
			foundcheat = True
			result_transcandidate = transcandidate
			break
	
	if debug_print:
		# TODO prohibit inter-thread-foo
		print(" » {} {}".format(
			'❗' if foundcheat else ' ',
			'=' if what_the_algo_said == cheat_guesses[fullphrase] else ' '))
		for ((oov, lexword, lexindex, oovindex, matchlength, legal), trans) in result_transcandidate:
			if legal:
				print("     {:<36} ✔ {:<36} -> {:<20}".format( # 20 + 4 * 4 = 36
					guess_helper.bold(oov    , oovindex, matchlength),
					guess_helper.bold(lexword, lexindex, matchlength),
					trans))
			else:
				print("     {:<36} ✗ {:<20} -> {:<20}".format(
					guess_helper.bold(oov    , oovindex, matchlength),
					"---",
					oov))
	
	return (get_trans(result_transcandidate),
	        score_phrase(result_transcandidate),
	        what_the_algo_said == cheat_guesses[fullphrase])
