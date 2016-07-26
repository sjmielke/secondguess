from scoop import futures, shared
import multiprocessing
from contextlib import closing
from collections import Counter
import itertools
import sys # stderr
import json
import argparse
import os

import guess_helper
import guess_matching
import guess_phrases

from guess_matching import CandidateWord # to deserialize!

def load_global_data(conf):
	# Load dictionary
	(matchers, translations) = guess_helper.load_dictionary(conf['global-files']['lexicon'])
	
	# Load training data
	train_target = Counter(" ".join(guess_helper.load_file_lines(conf['global-files']['train-target'])).split())
	
	# Load LEIDOS unigrams statistics
	unigramlines = guess_helper.load_file_lines(conf['global-files']['leidos-unigrams'])
	unigramlines = filter(lambda l: len(l.split()) != 1, unigramlines) # filter out empty-string unigrams
	unigramlines = [(l.split()[1], int(l.split()[0])) for l in unigramlines] # parse `uniq -c` output
	leidos_unigrams = Counter(dict(unigramlines))
	
	# Load grammar
	(adjectivizers, prefixers, suffixers, noun_adjective_dict) = guess_helper.load_grammar(conf['global-files']['grammar'], conf['global-files']['pertainyms'])
	
	return ((matchers, translations), train_target, leidos_unigrams, (adjectivizers, prefixers, suffixers, noun_adjective_dict))

def prepare_guessing(oov_original_list, catmorfdict):
	# Start filling our guess dictionary!
	# oov_guesses = {oov: [(guess, score)]}
	oov_guesses = {}
	
	# Sort oovlist entries into non-alphabetic tokens and actual OOVs
	guessable_oovs = Counter()
	for w in oov_original_list:
		# Filter out purely non-alphabetic tokens
		if not any(c.isalpha() for c in w):
			#print("{:<20} ~~> non-alpha token".format(w))
			oov_guesses[w] = [{'translation': w, 'score': 1.0, 'features': []}]
		else:
			guessable_oovs[w] += 1
	
	return (oov_guesses, guessable_oovs)


if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Guess OOVs.')
	subparsers = parser.add_subparsers(title='action')
	
	mode_server = subparsers.add_parser('mode_server', help='Expose webservice for full pipeline')
	mode_server.set_defaults(which='mode_server')
	
	mode_batch = subparsers.add_parser('mode_batch', help='Score whole sets / batches')
	mode_batch.add_argument('setname')
	mode_batch.set_defaults(which='mode_batch')
	
	args = parser.parse_args()
	
	if args.which == 'mode_server':
		import morfessor
		import bottle
		
		# Load static data
		conf = guess_helper.load_config(None)
		((matchers, translations), train_target, leidos_unigrams, (adjectivizers, prefixers, suffixers, noun_adjective_dict)) = load_global_data(conf)
		
		morfmodel = morfessor.MorfessorIO().read_binary_model_file(conf['server-files']['morfmodel'])
		print("Loaded files")
		
		# Read data and crunch
		app = bottle.Bottle()
		@app.hook('after_request')
		def enable_cors(): # https://gist.github.com/richard-flosi/3789163
			bottle.response.headers['Access-Control-Allow-Origin'] = '*'
			bottle.response.headers['Access-Control-Allow-Methods'] = 'PUT, GET, POST, DELETE, OPTIONS'
			bottle.response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'
		@app.route('/lookupword')
		def crunch_word():
			params = bottle.request.query.decode()
			import unicodedata
			oov = guess_helper.uninorm(params['oov'])
			oov_original_list = [oov]
			
			catmorfdict = {oov: list(zip(morfmodel.viterbi_segment(oov)[0], itertools.repeat("STM")))}
			print("Segmented words into " + str(catmorfdict))
			
			phraseparts = list(itertools.chain(*itertools.chain(*map(guess_phrases.gen_phrases, catmorfdict.values()))))
			uniq_phraseparts = guess_helper.uniq_list(phraseparts) # uniq for unhashable lists!
			
			all_matches = dict(itertools.starmap(guess_matching.lookup_oov, zip(uniq_phraseparts, itertools.repeat(matchers))))
			print("Matched phraseparts " + str(phraseparts))
			
			(oov_guesses, guessable_oovs_counter) = prepare_guessing(oov_original_list, catmorfdict)
			
			# If it wasn't a non-OOV, do the painful thing
			if oov_guesses == {}:
				static_data = ( all_matches,
				                translations,
				                catmorfdict,
				                guessable_oovs_counter,
				                train_target,
				                leidos_unigrams,
				                (adjectivizers, prefixers, suffixers, noun_adjective_dict),
				                conf)
				oov_guesses[oov] = guess_phrases.phraseguess_actual_oov(oov, static_data = static_data)[:100]
			
			bottle.response.content_type = 'application/json'
			return json.dumps(oov_guesses[oov])
		
		bottle.run(app, host='localhost', port=8080)

	elif args.which == 'mode_batch':
		# Load static data
		conf = guess_helper.load_config(args.setname)
		((matchers, translations), train_target, leidos_unigrams, (adjectivizers, prefixers, suffixers, noun_adjective_dict)) = load_global_data(conf)
		
		oov_original_list = guess_helper.load_file_lines(conf['set-files']['oovfile'])
		catmorfdict = guess_helper.load_catmorfdict(oov_original_list, conf['set-files']['catmorffile'])
		
		# Load previously calculated matches
		with open(conf['global-files']['allmatches']) as f:
			all_matches = eval(guess_helper.uninorm(f.read()))
		
		# Prepare guessing data
		(oov_guesses, guessable_oovs_counter) = prepare_guessing(oov_original_list, catmorfdict)
		print("{} distinct OOVs to guess.".format(len(guessable_oovs_counter)), file = sys.stderr)
		
		# Guess batch
		#guess_actual_oovs_into(oov_guesses, guessable_oovs_counter, all_matches, translations, catmorfdict, train_target, leidos_unigrams, conf)
		
		# Sort
		raw_guessable_oovs = list(guessable_oovs_counter)
		sorted_guessable_oovs = sorted(raw_guessable_oovs)
		
		# Distribute static data
		static_data = ( all_matches,
		                translations,
		                catmorfdict,
		                guessable_oovs_counter,
		                train_target,
		                leidos_unigrams,
		                (adjectivizers, prefixers, suffixers, noun_adjective_dict),
		                conf)
		shared.setConst(static_data = static_data)
		
		# Here is where the SCOOP magic happens
		guess_results = list(futures.map(guess_phrases.phraseguess_actual_oov, sorted_guessable_oovs))
		
		all_results = sorted(list(zip(sorted_guessable_oovs, guess_results)), key = lambda r: r[1][0]['score'], reverse = True)
		
		def print_results(t):
			(oov, candidates) = t
			print("{:>20} -> {:<20}".format(oov, candidates[0]['translation']), end='')
			print("{:10.7f} <- ".format(candidates[0]['score']), end='')
			for s in candidates[0]['features'].values():
				print(" {:10.7f}".format(s), end='')
			print("")
		
		list(map(print_results, all_results[0:20]))
		print("  [...]")
		list(map(print_results, all_results[-20:]))
		
		oov_guesses.update(dict(all_results))
		
		# Write our results in original order into result file
		with open(conf['set-files']['1best-out'], 'w') as f:
			for oov in oov_original_list:
				print(oov_guesses[oov][0]['translation'], file = f)
		
		def nbest(t):
			oov, candidates = t
			return (oov, candidates[:10])
		
		with open(conf['set-files']['nbest-out'], 'w') as f:
			print(json.dumps(dict(map(nbest, oov_guesses.items()))), file = f)
	else:
		print("Unknown mode", args.which)
		exit(1)
