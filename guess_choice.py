import itertools

import guess_helper

import sys

def choose_full_phrase_translation(
		unsorted_candidates: "[[CandidateWord]]",
		translations: "{str: [str]}",
		cheat_guesses: "{str: str}",
		debug_print: bool = False
	) -> (str, "Tuple[float]", bool):
	
	#### HELPER FUNCTIONS
	
	def translate_candidate(candidate: "[CandidateWord]") -> "[[(CandidateWord, str)]]":		
		translationss = []
		for cw in candidate:
			translationss.append([(cw, t) for t in translations[cw.lexword]] if cw.islegal else [(cw, cw.oov)])
		return list(itertools.product(*translationss))
	
	def get_trans(transcandidate: "[(CandidateWord, str)]") -> str: return " ".join(map(lambda c: c[1], transcandidate))
	
	def score_phrase(cand: "[(CandidateWord, str)]") -> float:
		cws = list(guess_helper.mapfst(cand))
		# each illegal result results in penalty
		nomatch_penalty = 0.07 * sum(map(lambda w: 0 if w.islegal else 1, cws))
		# prefer more OOV coverage (sum of matchlength [not translating is a full match!] by total oov length)
		coverage = 0.15 * sum(map(lambda w: w.matchlength, cws)) / sum(map(lambda w: len(w.oov), cws))
		# prefer shorter lexwords (0.05 is arbitrary)
		lexlengths_penalty = 0.02 * sum(map(lambda w: len(w.lexword), cws))
		
		# New features:
		# reward new english words (justified OOVs)
		# -> need the training target
		# reward english in-domain words
		# -> need domain-word-list
		# reward hungarian words that also are OOVs
		
		# Combine the following two:?
		# reward more common english words
		# -> need some huge unigram model
		# reward high-LM and punish low-LM phrases
		# -> need a good english LM
		
		return (float(sys.argv[-3]) * -1 * nomatch_penalty,
		        float(sys.argv[-2]) *      coverage,
		        float(sys.argv[-1]) * -1 * lexlengths_penalty)
	
	#### ACTUAL CHOICE PROCESS
	
	# Now, first we have to evaluate the candidates into translation candidates!
	translated_unsorted_candidates = list(itertools.chain(*list(map(translate_candidate, unsorted_candidates))))
	# Then pick our favorite one!
	besttranscand = max(translated_unsorted_candidates, key = score_phrase)
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
		for ((oov, lexword, lexindex, oovindex, matchlength, legal), trans) in zip(result_candidate, result_transwords):
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
