import itertools
import operator
from functools import reduce
from math import log

import guess_helper
import guess_matching

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
		(adjectivizers, prefixers, suffixers, untranslatables, noun_adjective_dict), # ([str], [(str, str)], [(str, str)], [str], {str: str})
		conf) = static_data
	
	def new_cw_for(foreign: str, is_legal = True):
		return guess_matching.CandidateWord(foreign, foreign, 0, 0, len(foreign), is_legal)
	
	#print("Phrase: ", phrase)
	
	candidatess = []
	for s in phrase:
		cw_list = all_matches[s]
		if any(p[0] == s for p in prefixers + suffixers) or any(suf == s for suf in untranslatables):
			cw_list.append(new_cw_for(s, is_legal = False))
		#print("  for {:10}".format(s), cw_list)
		candidatess.append(cw_list)
	
	lengths = list(map(len, candidatess))
	statstring = " x ".join(map(str, lengths)) + " = {}".format(reduce(operator.mul, lengths, 1))
	if debug_print:
		print (" » {:<20} » {:<20}".format(" ".join(phrase), statstring), end='', flush=True)
	
	unsorted_candidates = guess_helper.uniq_list(list(itertools.product(*candidatess)))
	
	
	# First we have to evaluate the candidates into translation candidates!
	def translate_candidate(candidate: "[CandidateWord]") -> "[([CandidateWord], [str])]":
		#print(" Candidate: ", candidate)
		
		candwordss  = [[]]
		transwordss = [[]]
		for cw in candidate:
			transword_opts = [t for t in translations[cw.lexword]] if cw.islegal else [cw.oov]
			new_candwordss  = [oldcandwords  + [cw]     for oldcandwords  in candwordss  for _      in transword_opts]
			new_transwordss = [oldtranswords + [option] for oldtranswords in transwordss for option in transword_opts]
			
			# Prefixes/suffixes proper
			prefix_opts = [p for p in prefixers if p[0] == cw.oov]
			suffix_opts = [p for p in suffixers if p[0] == cw.oov]
			dnew_candwordss   = [oldcandwords   + [new_cw_for(p[0])] for oldcandwords  in candwordss  for p in prefix_opts + suffix_opts]
			dnew_transwordss  = [[p[1].strip()] + oldtranswords      for oldtranswords in transwordss for p in prefix_opts]
			dnew_transwordss += [oldtranswords  + [p[1].strip()]     for oldtranswords in transwordss for p in suffix_opts]
			
			# Untranslatable suffixes from the grammar
			untr_opts = [u for u in untranslatables if u == cw.oov]
			print(cw.oov, untr_opts)
			#print("{:10} not in".format(cw.oov), sorted(untranslatables))
			dnew_candwordss  += [oldcandwords + [new_cw_for(u)] for oldcandwords  in candwordss  for u in untr_opts]
			dnew_transwordss += [oldtranswords                  for oldtranswords in transwordss for u in untr_opts]
			
			candwordss  = new_candwordss  + dnew_candwordss
			transwordss = new_transwordss + dnew_transwordss
		return [(candwords, transwords) for (candwords, transwords) in zip(candwordss, transwordss)]
	
	translated_unsorted_candidates = list(itertools.chain(*list(map(translate_candidate, unsorted_candidates))))
	
	# Now for the actual scoring!
	def is_already_english(s):
		# http://stackoverflow.com/a/18403812
		return len(s) == len(s.encode())
	
	def score_phrase(cand: "([CandidateWord], [str])") -> float:
		(cws, transwords) = cand
		
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
		training_count_penalty = min([0.000000005 * log(1 + train_target[tw]) for tw in transwords])
		
		# average LEIDOS frequency (surrogate for both in-domain-ness and general language model!) - only works for single words
		single_words = itertools.chain(*(tw.split() for tw in transwords))
		leidos_frequencies = [leidos_unigrams[trans] for trans in single_words]
		leidos_frequency = 0.000000001 * sum(leidos_frequencies) / len(leidos_frequencies)
		# reward english in-domain words
		# -> need domain-word-list
		# reward more common english words
		# -> need some huge unigram model
		# reward high-LM and punish low-LM phrases
		# -> need a good english LM
		
		# We want the english to be about as long as the input!
		inp_length = sum([len(cw.oov) for cw in cws])
		out_length = sum([len(tw)     for tw in transwords])
		# Data says english ~ 0.75 * uyghur
		lengthratio = 0.0000005 * abs(log(0.75 * (inp_length+0.00000001)/(out_length+0.00000001)))
		
		target_word_count_penalty = 0.5 * (sum([len(tw.split()) for tw in transwords]) - 1)
		
		# Give a score boost if we copied a full "OOV" that was already English!
		is_englishcopy = is_already_english(fulloov) and len(cws) == 1 and len(transwords) == 1 and cws[0].oov == transwords[0]
		
		feature_values = {'unmatchedpartweight':   -1 * nomatch_penalty,
		                  'perfectmatchweight':         perfectmatchbonus,
		                  'oovcoverageweight':          coverage,
		                  'sourcelexrestweight':   -1 * lexrest_penalty,
		                  'sourcepartcountweight':      part_count,
		                  'trainingcountweight':   -1 * training_count_penalty,
		                  'leidosfrequencyweight':      leidos_frequency,
		                  'lengthratioweight':     -1 * lengthratio,
		                  'resultwordcountweight': -1 * target_word_count_penalty,
		                  'englishcopyboost':           (1 if is_englishcopy else 0)}
		
		scoringweights = conf['scoring-weights']
		
		score = 0.0
		for feature in feature_values:
			score += scoringweights[feature] * feature_values[feature]
		
		# Small tie breaker to have deterministic results
		tiebreaker_hashes = list(map(hash, transwords))
		score += 0.000000000000000000000000000001 * sum(tiebreaker_hashes) / len(tiebreaker_hashes)
		
		return {'translation': " ".join(transwords),
		        'score': score,
		        'features': feature_values,
		        'lexwords': [cw.lexword for cw in cws],
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
