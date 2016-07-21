import itertools
from math import log

import guess_helper

import sys

def print_dups(ss, prefix = ""):
	s = ss #s = list(filter(lambda c: c.islegal, ss))
	if len(list(s)) != len(list(set(s))):
		print(prefix + "{} -> {}".format(len(list(s)), len(list(set(s)))))

def score_full_phrase_translations(
		fulloov: str,
		unsorted_candidates: "[[CandidateWord]]",
		translations: "{str: Set[str]}",
		cheat_guesses: "{str: str}",
		all_oovs: "Counter[str]",
		train_target: "Counter[str]",
		leidos_unigrams: "Counter[str]",
		args: "argparse args",
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
	
	def get_trans(transcandidate: "[(CandidateWord, str)]") -> str:
		return " ".join(map(lambda c: c[1], transcandidate))
	
	def is_already_english(s):
		# http://stackoverflow.com/a/18403812
		return len(s) == len(s.encode())
	
	def score_phrase(cand: "[(CandidateWord, str)]") -> float:
		cws = list(guess_helper.mapfst(cand))
		
		# SOURCE SIDE FEATURES
		
		# each illegal result results in penalty
		nomatch_penalty = 0.07 * sum(map(lambda w: 0 if w.islegal or is_already_english(w.oov) else 1, cws))
		# perfect matches are really nice!
		perfectmatchbonus = 0.5 * sum(map(lambda w: 1 if (w.islegal or is_already_english(w.oov)) and w.matchlength == len(w.lexword) else 0, cws))
		# prefer more OOV coverage (sum of matchlength [not translating is a full match!] by total oov length)
		coverage = 0.15 * sum(map(lambda w: w.matchlength, cws)) / sum(map(lambda w: len(w.oov), cws))
		# prefer less umatched lexword chars
		lexrest_penalty = 0.02 * sum(map(lambda w: len(w.lexword) - w.matchlength, cws))
		# reward hungarian subwords that also are OOVs
		part_count = 0.001 * sum(map(lambda w: all_oovs[w.oov], cws))
		
		
		# TARGET SIDE FEATURES
		
		# reward new english words (justified OOVs) - more precise: words that contain new stuff!
		training_count_penalty = min(map(lambda c: 0.000000005 * log(1 + train_target[c[1]]), cand))
		
		# average LEIDOS frequency (surrogate for both in-domain-ness and general language model!) - only works for single words
		leidos_frequencies = list(map(lambda trans: leidos_unigrams[trans], itertools.chain(*map(lambda c: c[1].split() if c[1].split() != [] else [c[1]], cand))))
		leidos_frequency = 0.000000001 * sum(leidos_frequencies) / len(leidos_frequencies)
		# reward english in-domain words
		# -> need domain-word-list
		# reward more common english words
		# -> need some huge unigram model
		# reward high-LM and punish low-LM phrases
		# -> need a good english LM
		
		# We want the english to be about as long as the input!
		inp_length = sum(map(lambda pair: len(pair[0].oov), cand))
		out_length = sum(map(lambda pair: len(pair[1]), cand))
		# Data says english ~ 0.75 * uyghur
		lengthratio = 0.0000005 * abs(log(0.75 * (inp_length+0.00000001)/(out_length+0.00000001)))
		
		target_word_count_penalty = 0.5 * (sum(map(lambda pair: len(pair[1].split()), cand)) - 1)
		
		tiebreaker_hashes = list(map(hash, cand))
		tiebreaker = 0.0000000000000000000000000000000001 * sum(tiebreaker_hashes) / len(tiebreaker_hashes)
		
		return (args.unmatchedpartweight   * -1 * nomatch_penalty,
		        args.perfectmatchweight    *      perfectmatchbonus,
		        args.oovcoverageweight     *      coverage,
		        args.sourcelexrestweight   * -1 * lexrest_penalty,
		        args.sourcepartcountweight *      part_count,
		        args.trainingcountweight   * -1 * training_count_penalty,
		        args.leidosfrequencyweight *      leidos_frequency,
		        args.lengthratioweight     * -1 * lengthratio,
		        args.resultwordcountweight * -1 * target_word_count_penalty,
		        tiebreaker)
	
	#### ACTUAL CHOICE PROCESS
	
	# Now, first we have to evaluate the candidates into translation candidates!
	translated_unsorted_candidates = list(itertools.chain(*list(map(translate_candidate, unsorted_candidates))))
	
	print_dups(translated_unsorted_candidates)
	# Then pick our favorite one!
	scored = sorted(translated_unsorted_candidates, key = lambda p: sum(score_phrase(p)), reverse = True)
	besttranscand = scored[0]
	phrase = list(map(lambda cw: cw.oov, guess_helper.mapfst(besttranscand)))
	
	# First, what would the algo itself say?
	what_the_algo_said = get_trans(besttranscand)
	result_transcandidate = besttranscand
	
	# Now, can I find the "correct" solution? Then replace old result with it!
	foundcheat = False
	cheatsolution = cheat_guesses[fulloov]
	for transcandidate in translated_unsorted_candidates:
		if get_trans(transcandidate) == cheatsolution:
			foundcheat = True
			result_transcandidate = transcandidate
			break
	
	if debug_print:
		# TODO prohibit inter-thread-foo
		print(" » {} {}".format(
			'❗' if foundcheat else ' ',
			'=' if what_the_algo_said == cheat_guesses[fulloov] else ' '))
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
	
	def prepare_for_output(tc):
		return (get_trans(tc),
		        score_phrase(tc),
		        get_trans(tc) == what_the_algo_said and what_the_algo_said == cheat_guesses[fulloov])
	
	return sorted(list(map(prepare_for_output, scored)), key = lambda t: t[1], reverse = True)
