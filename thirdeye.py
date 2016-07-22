from scoop import futures
import itertools
import sys # stderr
from collections import Counter

import guess_helper
import guess_matching
import guess_nes
import guess_logic
import guess_phrases

from guess_matching import CandidateWord # to deserialize!

import argparse
import os

def print_human_algo_statistics(stats: ((int, int), (int, int, int, int))):
	ref = ""
	# (Schema: count_human_algo)
	((c_nn, c_ny), (c_yn, c_yw, c_yc, c_yy)) = stats
	print("{}> {:<27} {:3} ({})".format(ref, "No human, no algo:", \
		c_nn, "neither knew a translation"))
	print("{}> {:<27} {:3} ({})".format(ref, "No human, but algo:", \
		c_ny, "we're either superhuman or translated stray NEs"))
	print("{}> {:<27} {:3} ({})".format(ref, "Human, but no algo:", \
		c_yn, "didn't find any translation, but human did"))
	print("{}> {:<27} {:3} ({})".format(ref, "Human, but wrong algo:", \
		c_yw, "didn't find the human translation containing lexicon entry, but found another"))
	print("{}> {:<27} {:3} ({})".format(ref, "Human corrected algo:", \
		c_yc, "found the human suggestion containing lexicon entry, but wouldn't have chosen it"))
	print("{}> {:<27} {:3} ({})".format(ref, "Human = algo:", \
		c_yy, "found the human suggestion containing candidate and naturally chose it!"))

def load_global_data(conf):
	# Load dictionary
	(matchers, translations) = guess_helper.load_dictionary(conf['global-files']['lexfile'])
	
	# Load training data
	train_target = Counter(" ".join(guess_helper.load_file_lines(conf['global-files']['train-target'])).split())
	
	# Load LEIDOS unigrams statistics
	unigramlines = guess_helper.load_file_lines(conf['global-files']['leidos-unigrams'])
	unigramlines = filter(lambda l: len(l.split()) != 1, unigramlines) # filter out empty-string unigrams
	unigramlines = [(l.split()[1], int(l.split()[0])) for l in unigramlines] # parse `uniq -c` output
	leidos_unigrams = Counter(dict(unigramlines))
	
	return ((matchers, translations), train_target, leidos_unigrams)

def prepare_guessing(oov_original_list, nes, catmorfdict, reffile):
	# Load cheat/reference
	if reffile == "nocheatref":
		reffile = None
	if reffile != None:
		cheat_list = guess_helper.load_file_lines(reffile)
	else:
		cheat_list = ["THISVERYLONGANDOBSCURESTRINGSHOULDNOTBEINTHEDICTIONARY"] * len(oov_original_list)
	cheat_guesses = dict(zip(oov_original_list, cheat_list))
	
	# Start filling our guess dictionary!
	# oov_guesses = {oov: [(guess, score)]}
	oov_guesses = {}

	# Sort oovlist entries into NEs and actual OOVs
	(guessable_nes_counter, guessable_oovs_counter) = guess_logic.get_guessables_into(oov_guesses, oov_original_list, nes)
	# Guess NEs
	all_ne_roots = guess_nes.guess_nes_into(oov_guesses, catmorfdict, list(guessable_nes_counter))

	return (oov_guesses, (guessable_nes_counter, guessable_oovs_counter), cheat_guesses)


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
		import json
		
		# Load data
		conf = guess_helper.load_config(None)
		((matchers, translations), train_target, leidos_unigrams) = load_global_data(conf)
		
		morfmodel = morfessor.MorfessorIO().read_binary_model_file(conf['server-files']['morfmodel'])
		print("Loaded files")
		
		def do_one_shot(oov_original_list):
			catmorfdict = guess_helper.apply_list2dict(lambda w: list(zip(morfmodel.viterbi_segment(w)[0], itertools.repeat("STM"))), oov_original_list)
			print("Segmented words into " + str(catmorfdict))
			phraseparts = list(itertools.chain(*itertools.chain(*map(guess_phrases.gen_phrases, catmorfdict.values()))))
			uniq_phraseparts = guess_helper.uniq_list(phraseparts) # uniq for unhashable lists!
			all_matches = dict(itertools.starmap(guess_matching.lookup_oov, zip(uniq_phraseparts, itertools.repeat(matchers))))
			print("Matched phraseparts " + str(phraseparts))
			# Separate NEs and stuff
			(oov_guesses, (guessable_nes_counter, guessable_oovs_counter), cheat_guesses) \
				= prepare_guessing(oov_original_list, [], catmorfdict, None)
			# Then do the actual OOV guessing, while counting, how often were we "better" than the human
			stats = guess_logic.guess_actual_oovs_into(oov_guesses, list(guessable_oovs_counter), guessable_oovs_counter, all_matches, translations, catmorfdict, cheat_guesses, train_target, leidos_unigrams, conf)
			return oov_guesses
		
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
			print(list(params.items()))
			oov = params['oov']
			bottle.response.content_type = 'application/json'
			oov_guesses = do_one_shot([oov])
			return json.dumps(oov_guesses[oov])
		bottle.run(app, host='localhost', port=8080)

	elif args.which == 'mode_batch':
		# Load data
		conf = guess_helper.load_config(args.setname)
		((matchers, translations), train_target, leidos_unigrams) = load_global_data(conf)
		oov_original_list = guess_helper.load_file_lines(conf['set-files']['oovfile'])
		catmorfdict = guess_helper.load_catmorfdict(oov_original_list, conf['set-files']['catmorffile'])
		nes = list(guess_helper.load_file_lines(conf['set-files']['nefile'])) # Load NE list -> apparently untokenized! sucks e.g. for Mosoni-Dunaig
		
		# Load previously calculated matches
		with open(conf['global-files']['allmatches']) as f:
			all_matches = eval(f.read())
		
		# Prepare guessing data
		(oov_guesses, (guessable_nes_counter, guessable_oovs_counter), cheat_guesses) \
			= prepare_guessing(oov_original_list, nes, catmorfdict, conf['set-files']['reffile'])
		print("{} distinct NEs and {} distinct OOVs to guess.".format(len(guessable_nes_counter), len(guessable_oovs_counter)), file = sys.stderr)
		
		uniq_oov_list = list(guessable_oovs_counter)
		
		# Guess batch
		stats = guess_logic.guess_actual_oovs_into(oov_guesses, uniq_oov_list, guessable_oovs_counter, all_matches, translations, catmorfdict, cheat_guesses, train_target, leidos_unigrams, conf)
		
		print_human_algo_statistics(stats)
		
		# Write our results in original order into result file
		with open(conf['set-files']['1best-out'], 'w') as translist:
			for oov in oov_original_list:
				print(oov_guesses[oov][0][0], file=translist)
	else:
		print("Unknown mode", args.which)
		exit(1)
