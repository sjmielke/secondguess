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

# uses nefile, trainfile, leidosfile
def load_data(args):
	# Load training data
	train_target = Counter(" ".join(guess_helper.load_file_lines(args.trainfile)).split())
	
	# Load LEIDOS unigrams statistics
	leidos_unigrams = Counter(dict([(l.split()[1], int(l.split()[0])) for l in guess_helper.load_file_lines(args.leidosfile) if len(l.split()) != 1]))
	
	return (train_target, leidos_unigrams)

def prepare_guessing(oov_original_list, nes, catmorfdict, reffile):
	# Load cheat/reference
	if reffile == "nocheatref":
		reffile = None
	if reffile != None:
		cheat_list = guess_helper.load_file_lines(args.reffile)
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
	
	# mode server: Expose webservice for full pipeline
	
	mode_server = subparsers.add_parser('mode_server', help='Expose webservice for full pipeline')
	mode_server.add_argument('morfmodel' , help='<- binarized morfessor model')
	mode_server.add_argument('lexfile'   , help='<- normalized lexicon')
	mode_server.add_argument('nefile'    , help='<- NE list')
	mode_server.add_argument('trainfile' , help='<- tokenized training target (English)')
	mode_server.add_argument('leidosfile', help='<- counted leidos unigrams')
	mode_server.add_argument('--unmatchedpartweight', type=float)
	mode_server.add_argument('--perfectmatchweight', type=float)
	mode_server.add_argument('--oovcoverageweight', type=float)
	mode_server.add_argument('--sourcelexrestweight', type=float)
	mode_server.add_argument('--sourcepartcountweight', type=float)
	mode_server.add_argument('--trainingcountweight', type=float)
	mode_server.add_argument('--leidosfrequencyweight', type=float)
	mode_server.add_argument('--lengthratioweight', type=float)
	mode_server.add_argument('--resultwordcountweight', type=float)
	mode_server.add_argument('--deletionscore', type=float)
	mode_server.add_argument('--copyscore', type=float)
	mode_server.set_defaults(which='mode_server')
	
	# mode 1: Generate batches for scoring
	
	mode1 = subparsers.add_parser('mode1_genbatches', help='Generate batches for scoring')
	mode1.add_argument('batchsize', type=int)
	mode1.add_argument('oovfile'  , help='<- simple OOV list')
	mode1.add_argument('reffile'  , help='<- cheating reference translation')
	mode1.add_argument('morffile' , help='<- morf-segmented/-categorized OOV list')
	mode1.add_argument('nefile'   , help='<- NE list')
	mode1.add_argument('matchfile', help='<> all morphcombination matches')
	mode1.set_defaults(which='mode1_genbatches')
	
	# mode 2: Score individual batch
	
	mode2 = subparsers.add_parser('mode2_scorebatch', help='Score individual batch')
	
	mode2.add_argument('batchfile' , help='<- batch file')
	mode2.add_argument('reffile'   , help='<- cheating reference translation')
	
	mode2.add_argument('lexfile'   , help='<- normalized lexicon')
	mode2.add_argument('morffile'  , help='<- morf-segmented/-categorized OOV list')
	mode2.add_argument('nefile'    , help='<- NE list')
	mode2.add_argument('trainfile' , help='<- tokenized training target (English)')
	mode2.add_argument('leidosfile', help='<- counted leidos unigrams')
	
	mode2.add_argument('matchfile' , help='<> all morphcombination matches')
	
	mode2.add_argument('--unmatchedpartweight', type=float)
	mode2.add_argument('--perfectmatchweight', type=float)
	mode2.add_argument('--oovcoverageweight', type=float)
	mode2.add_argument('--sourcelexrestweight', type=float)
	mode2.add_argument('--sourcepartcountweight', type=float)
	mode2.add_argument('--trainingcountweight', type=float)
	mode2.add_argument('--leidosfrequencyweight', type=float)
	mode2.add_argument('--lengthratioweight', type=float)
	mode2.add_argument('--resultwordcountweight', type=float)
	mode2.add_argument('--deletionscore', type=float)
	mode2.add_argument('--copyscore', type=float)
	
	mode2.set_defaults(which='mode2_scorebatch')
	
	# mode 3: Combined scored batches into result
	
	mode3 = subparsers.add_parser('mode3_combineresults', help='Combined scored batches into result')
	
	mode3.add_argument('oovfile'    , help='<- original OOV list')
	mode3.add_argument('noofbatches', help='<- no. of batches', type=int)
	mode3.add_argument('outfile'    , help='-> output translation')
	
	mode3.set_defaults(which='mode3_combineresults')
	
	args = parser.parse_args()
	
	if args.which == 'mode_server':
		import morfessor
		import bottle
		import json
		
		# Load data
		(matchers, translations) = guess_helper.load_dictionary(args.lexfile)
		nes = list(guess_helper.load_file_lines(args.nefile)) # Load NE list -> apparently untokenized! sucks e.g. for Mosoni-Dunaig
		(train_target, leidos_unigrams) = load_data(args)
		
		morfmodel = morfessor.MorfessorIO().read_binary_model_file(args.morffile)
		print("Loaded morf")
		
		def do_one_shot(oov_original_list):
			catmorfdict = guess_helper.apply_list2dict(lambda w: list(zip(morfmodel.viterbi_segment(w)[0], itertools.repeat("STM"))), oov_original_list)
			print("Segmented words into " + str(catmorfdict))
			phraseparts = list(itertools.chain(*itertools.chain(*map(guess_phrases.gen_phrases, catmorfdict.values()))))
			uniq_phraseparts = guess_helper.uniq_list(phraseparts) # uniq for unhashable lists!
			all_matches = dict(itertools.starmap(guess_matching.lookup_oov, zip(uniq_phraseparts, itertools.repeat(matchers))))
			print("Matched phraseparts " + str(phraseparts))
			# Separate NEs and stuff
			(oov_guesses, (guessable_nes_counter, guessable_oovs_counter), cheat_guesses) \
				= prepare_guessing(oov_original_list, nes, catmorfdict, None)
			# Then do the actual OOV guessing, while counting, how often were we "better" than the human
			stats = guess_logic.guess_actual_oovs_into(oov_guesses, list(guessable_oovs_counter), guessable_oovs_counter, all_matches, translations, catmorfdict, cheat_guesses, train_target, leidos_unigrams, args)
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

	elif args.which == 'mode1_genbatches':
		# Load data
		oov_original_list = guess_helper.load_file_lines(args.oovfile)
		catmorfdict = guess_helper.load_catmorfdict(oov_original_list, args.morffile)
		nes = list(guess_helper.load_file_lines(args.nefile)) # Load NE list -> apparently untokenized! sucks e.g. for Mosoni-Dunaig
		
		# Load previously calculated matches
		with open(args.matchfile) as f:
			all_matches = eval(f.read())
		
		# Prepare guessing data
		(oov_guesses, (guessable_nes_counter, guessable_oovs_counter), cheat_guesses) \
			= prepare_guessing(oov_original_list, nes, catmorfdict, args.reffile)
		print("{} distinct NEs and {} distinct OOVs to guess.".format(len(guessable_nes_counter), len(guessable_oovs_counter)), file = sys.stderr)
		
		uniq_oov_list = list(guessable_oovs_counter)
		
		batches = [uniq_oov_list[i:i + args.batchsize] for i in range(0, len(uniq_oov_list), args.batchsize)]
		for (i, batch) in enumerate(batches):
			with open(args.oovfile + ".scores.batch." + str(i + 1), 'w') as f: # files from 1 to len
				print((oov_guesses, guessable_oovs_counter, catmorfdict, cheat_guesses, batch), file = f)
		
		# Now output the number of batches created for further handling
		print(len(batches))
	
	elif args.which == 'mode2_scorebatch':
		# Load data
		(_, translations) = guess_helper.load_dictionary(args.lexfile)
		(train_target, leidos_unigrams) = load_data(args)
		with open(args.matchfile) as f:
			all_matches = eval(f.read())
		
		# Load batch
		with open(args.batchfile) as f:
			(oov_guesses, guessable_oovs_counter, catmorfdict, cheat_guesses, batch) = eval(f.read())
		
		# Guess batch
		newstats = guess_logic.guess_actual_oovs_into(oov_guesses, batch, guessable_oovs_counter, all_matches, translations, catmorfdict, cheat_guesses, train_target, leidos_unigrams, args)
		# Write batch
		with open(args.batchfile + ".done", 'w') as f:
			print((oov_guesses, newstats), file = f)
		
	elif args.which == 'mode3_combineresults':
		oov_guesses = {}
		oov_original_list = guess_helper.load_file_lines(args.oovfile)
		stats = ((0, 0), (0, 0, 0, 0))
		
		print("Let's combine scores now...", end = '', flush = True)
		
		for i in range(args.noofbatches):
			print(i + 1, "...", end = '', flush = True)
			with open(args.oovfile + ".scores.batch." + str(i + 1) + ".done") as f:
				(batchguesses, batchstats) = eval(f.read())
				oov_guesses.update(batchguesses)
				stats = guess_helper.tupleadd(stats, batchstats)
		
		print("done!", flush = True)
		
		print_human_algo_statistics(stats)
		
		# Write our results in original order into result file
		with open(args.outfile, 'w') as translist:
			for oov in oov_original_list:
				print(oov_guesses[oov][0][0], file=translist)
	else:
		print("Unknown mode", args.which)
		exit(1)
