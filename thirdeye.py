import itertools
from collections import Counter

import guess_helper
import guess_matching
import guess_nes
import guess_logic
import guess_phrases

from guess_matching import CandidateWord # to deserialize!

import argparse
import os

def print_human_algo_statistics(ref: str, stats: ((int, int), (int, int, int, int))):
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

def load_data():
	parser = argparse.ArgumentParser(description='Guess OOVs.')
	
	parser.add_argument('oovfile'   , help='<- original OOV list')
	parser.add_argument('reffile'   , help='<- cheating reference translation')
	
	parser.add_argument('morffile'  , help='<- morf-segmented/-categorized OOV list (batch mode) / morfessor model (pipe mode)')
	parser.add_argument('lexfile'   , help='<- normalized lexicon')
	parser.add_argument('nefile'    , help='<- NE list')
	parser.add_argument('trainfile' , help='<- tokenized training target (English)')
	parser.add_argument('leidosfile', help='<- counted leidos unigrams')
	
	parser.add_argument('matchfile' , help='<> all morphcombination matches')
	parser.add_argument('outfile'   , help='-> output translation')
	
	parser.add_argument('--unmatchedpartweight', type=float)
	parser.add_argument('--perfectmatchweight', type=float)
	parser.add_argument('--oovcoverageweight', type=float)
	parser.add_argument('--sourcelexrestweight', type=float)
	parser.add_argument('--sourcepartcountweight', type=float)
	parser.add_argument('--trainingcountweight', type=float)
	parser.add_argument('--leidosfrequencyweight', type=float)
	parser.add_argument('--lengthratioweight', type=float)
	parser.add_argument('--resultwordcountweight', type=float)
	parser.add_argument('--deletionscore', type=float)
	parser.add_argument('--copyscore', type=float)
	
	args = parser.parse_args()
	
	print("Parsed args")
	
	# Load dictionary
	(matchers, translations) = guess_helper.load_dictionary(args.lexfile)
	
	# Load NE list
	# -> apparently untokenized! sucks e.g. for Mosoni-Dunaig
	nes = list(guess_helper.load_file_lines(args.nefile))
	
	# Load training data
	train_target = Counter(" ".join(guess_helper.load_file_lines(args.trainfile)).split())
	
	# Load LEIDOS unigrams statistics
	leidos_unigrams = Counter(dict([(l.split()[1], int(l.split()[0])) for l in guess_helper.load_file_lines(args.leidosfile) if len(l.split()) != 1]))
	
	return (args, ((matchers, translations), nes, train_target, leidos_unigrams))

def do_guessing(oov_original_list, nes, all_matches, translations, catmorfdict, train_target, leidos_unigrams, args):
	# Load cheat/reference
	cheat_list = guess_helper.load_file_lines(args.reffile) if "nocheatref" not in args.reffile else ["THISVERYLONGANDOBSCURESTRINGSHOULDNOTBEINTHEDICTIONARY"] * len(oov_original_list)
	cheat_guesses = dict(zip(oov_original_list, cheat_list))
	
	# Start filling our guess dictionary!
	# oov_guesses = {oov: [(guess, score)]}
	oov_guesses = {}

	# Sort oovlist entries into NEs and actual OOVs
	(guessable_nes_counter, guessable_oovs_counter) = guess_logic.get_guessables_into(oov_guesses, oov_original_list, nes)
	print("{} distinct NEs and {} distinct OOVs to guess.".format(len(guessable_nes_counter), len(guessable_oovs_counter)))
	
	# Guess NEs
	all_ne_roots = guess_nes.guess_nes_into(oov_guesses, catmorfdict, list(guessable_nes_counter))

	# Then do the actual OOV guessing, while counting, how often were we "better" than the human
	stats = guess_logic.guess_actual_oovs_into(oov_guesses, guessable_oovs_counter, all_matches, translations, catmorfdict, cheat_guesses, train_target, leidos_unigrams, args)
	
	return (oov_guesses, stats)

if __name__ == '__main__':
	# Static simple stuff we have to do anyway
	(args, ((matchers, translations), nes, train_target, leidos_unigrams)) = load_data()
	
	print("Loaded data")
	
	if args.oovfile in ['pipe', 'server']:
		assert args.reffile == 'nocheatref'
		assert args.matchfile == 'pipe'
		assert args.outfile == 'pipe'
		# Load morfessor
		import morfessor
		morfmodel = morfessor.MorfessorIO().read_binary_model_file(args.morffile)
		print("Loaded morf")
		
		def do_one_shot(oov_original_list):
			catmorfdict = guess_helper.apply_list2dict(lambda w: list(zip(morfmodel.viterbi_segment(w)[0], itertools.repeat("STM"))), oov_original_list)
			print("Segmented words into " + str(catmorfdict))
			phraseparts = list(itertools.chain(*itertools.chain(*map(guess_phrases.gen_phrases, catmorfdict.values()))))
			uniq_phraseparts = guess_helper.uniq_list(phraseparts) # uniq for unhashable lists!
			all_matches = dict(itertools.starmap(guess_matching.lookup_oov, zip(uniq_phraseparts, itertools.repeat(matchers))))
			print("Matched phraseparts " + str(phraseparts))
			return do_guessing(oov_original_list, nes, all_matches, translations, catmorfdict, train_target, leidos_unigrams, args)
		
		# Read data and crunch
		if args.oovfile == 'pipe':
			import sys
			oov_original_list = sys.stdin.read().split()
			do_one_shot(oov_original_list)
		elif args.oovfile == 'server':
			import bottle
			import json
			app = bottle.Bottle()
			# https://gist.github.com/richard-flosi/3789163
			@app.hook('after_request')
			def enable_cors():
				bottle.response.headers['Access-Control-Allow-Origin'] = '*'
				bottle.response.headers['Access-Control-Allow-Methods'] = 'PUT, GET, POST, DELETE, OPTIONS'
				bottle.response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'
			@app.route('/lookupword')
			def crunch_word():
				params = bottle.request.query.decode()
				print(list(params.items()))
				oov = params['oov']
				bottle.response.content_type = 'application/json'
				oov_guesses, _ = do_one_shot([oov])
				return json.dumps(oov_guesses[oov])
			bottle.run(app, host='localhost', port=8080)

	else:
		# Load OOV list and its morfessor splits
		oov_original_list = guess_helper.load_file_lines(args.oovfile)
		catmorfdict = guess_helper.load_catmorfdict(oov_original_list, args.morffile)
		# Load previously calculated matches
		with open(args.matchfile) as f:
			all_matches = eval(f.read())
		# Do the guessing
		(oov_guesses, stats) = do_guessing(oov_original_list, nes, all_matches, translations, catmorfdict, train_target, leidos_unigrams, args)
		print_human_algo_statistics(args.reffile, stats)
		# Write our results in original order into result file
		with open(args.outfile, 'w') as translist:
			for oov in oov_original_list:
				print(oov_guesses[oov][0][0], file=translist)
