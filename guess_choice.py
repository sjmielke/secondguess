import itertools
import operator
from functools import reduce
from math import log

import guess_helper

import sys

def score_full_phrase_matches(
		fulloov: str,
		phrase: [str],
		static_data,
		debug_print: bool
	) -> "[{'translation': str, 'score': float, 'features': {str: float}, 'lexwords': str, 'candidate': (CandidateWord, str)}]":
	
	(all_matches, # {str: [CandidateWord]}
		translations, # {str: [str]}
		catmorfdict, # {str: [(str, str)]}
		all_oovs, # Counter[str]
		train_target, # Counter[str]
		leidos_unigrams, # Counter[str]
		conf) = static_data
	
	candidatess = [all_matches[s] for s in phrase]
	
	lengths = list(map(len, candidatess))
	statstring = " x ".join(map(str, lengths)) + " = {}".format(reduce(operator.mul, lengths, 1))
	if debug_print:
		print (" » {:<20} » {:<20}".format(" ".join(phrase), statstring), end='', flush=True)
	
	unsorted_candidates = list(itertools.product(*candidatess))
	
	# First we have to evaluate the candidates into translation candidates!
	def translate_candidate(candidate: "[CandidateWord]") -> "[[(CandidateWord, str)]]":
		translationss = []
		for cw in candidate:
			cw_translations = [(cw, t) for t in translations[cw.lexword]] if cw.islegal else [(cw, cw.oov)]
			translationss.append(cw_translations)
		result = list(itertools.product(*translationss))
		for c in result:
			if tuple(guess_helper.mapfst(c)) != candidate:
				print("{} != \n{}".format(list(guess_helper.mapfst(c)), candidate), file = sys.stderr)
				exit(1)
		return result
	
	translated_unsorted_candidates = list(itertools.chain(*list(map(translate_candidate, unsorted_candidates))))
	
	# Now for the actual scoring!
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
		single_words = itertools.chain(*(c[1].split() for c in cand))
		leidos_frequencies = [leidos_unigrams[trans] for trans in single_words]
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
		
		# Give a score boost if we copied a full "OOV" that was already English!
		englishcopy = 1 if (is_already_english(fulloov) and all(cw.oov == translation for (cw, translation) in cand)) else 0
		
		feature_values = {'unmatchedpartweight':   -1 * nomatch_penalty,
		                  'perfectmatchweight':         perfectmatchbonus,
		                  'oovcoverageweight':          coverage,
		                  'sourcelexrestweight':   -1 * lexrest_penalty,
		                  'sourcepartcountweight':      part_count,
		                  'trainingcountweight':   -1 * training_count_penalty,
		                  'leidosfrequencyweight':      leidos_frequency,
		                  'lengthratioweight':     -1 * lengthratio,
		                  'resultwordcountweight': -1 * target_word_count_penalty,
		                  'englishcopyboost':           englishcopy}
		
		scoringweights = conf['scoring-weights']
		
		score = 0.0
		for feature in feature_values:
			score += scoringweights[feature] * feature_values[feature]
		
		# Small tie breaker to have deterministic results
		tiebreaker_hashes = list(map(hash, cand))
		score += 0 * 0.00000000000000000000000001 * sum(tiebreaker_hashes) / len(tiebreaker_hashes)
		
		return {'translation': " ".join(cpart[1] for cpart in cand),
		        'score': score,
		        'features': feature_values,
		        'lexwords': [cpart[0].lexword for cpart in cand],
		        'candidate': cand}
	
	scored_unsorted_candidates = list(map(score_phrase, translated_unsorted_candidates))
	scored = sorted(scored_unsorted_candidates, key = lambda c: c['score'], reverse = True)
	
	if debug_print:
		for ((oov, lexword, lexindex, oovindex, matchlength, legal), trans) in scored[0]['candidate']:
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
	
	return scored
