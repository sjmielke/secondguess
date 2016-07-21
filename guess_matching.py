from difflib import SequenceMatcher
from contextlib import closing
import multiprocessing
import typing # NamedTuple
import itertools
import sys
import argparse

import guess_helper
import guess_phrases

CandidateWord = typing.NamedTuple('CandidateWord', [('oov', str), ('lexword', str), ('i_lex', int), ('i_oov', int), ('matchlength', int), ('islegal', bool)])

# mono3affix_min6_match4 per word
def is_legal_match(s: str, i: int, l: int) -> bool:
	# First, find the two actually matching words of the string
	# Only one word? Then it's easy.
	if " " in s:
		for w in s.split():
			if len(w) <= i:
				i -= len(w) + 1
				continue
			# It can only be contained in this word!
			s = w
			break
	
	rest1 = i
	rest2 = len(s) - (i + l)
	
	return l >= 4 and (l / len(s) > 0.65 or (rest1 == 0 or rest2 == 0) and rest1 + rest2 <= 3 and l >= 6)

def get_best_match(oov: str, lexword: str, matcher: SequenceMatcher) -> (str, (int, int, int)):
	matcher.set_seq1(oov)
	i_o, i_w, matchlength = matcher.find_longest_match(0, len(oov), 0, len(lexword))
	return (lexword, (i_o, i_w, matchlength))

def lookup_oov(oov: str, matchers: "{str: SequenceMatcher}") -> "(str, [CandidateWord])":
	print("Looking up", oov, "...", end = '', flush = True)
	
	# Match search
	nextbest_lexcandidates = []
	nextbest_matchlength = 0
	best_lexcandidates = []
	best_matchlength = 0
	found_legal = False
	
	# First find LCS = match with lexword in a mapreduce fashion
	all_pairs = map(lambda w: (oov, w, matchers[w]), sorted(matchers.keys()))
	
	individual_bestmatches = itertools.starmap(get_best_match, all_pairs)
	
	print("...", end = '', flush = True)
	
	# Now compare all findings!
	for (lexword, (i_o, i_w, matchlength)) in individual_bestmatches:
		if found_legal and (matchlength < 3 or matchlength < best_matchlength):
			continue
		legal = is_legal_match(lexword, i_w, matchlength)
		if not found_legal or legal: # no legality regressions!
			if (legal and not found_legal # we find our first legal match...
					or matchlength > best_matchlength): # ...or a better one, regardless of legality status
				# Also get some more
				nextbest_lexcandidates = best_lexcandidates
				nextbest_matchlength = best_matchlength
				# Then update best
				best_lexcandidates = [CandidateWord(oov, lexword, i_w, i_o, matchlength, legal)]
				best_matchlength = matchlength
			elif matchlength == best_matchlength: # no improvement? just add a candidate
				best_lexcandidates.append(CandidateWord(oov, lexword, i_w, i_o, matchlength, legal))
		if legal:
			found_legal = True
	
	print("done!", flush = True)
	
	# If we didn't find anything legal, guess we just copy:
	if not found_legal or len(best_lexcandidates) > 75: # matching too much can't be right
		return (oov, [CandidateWord(oov, oov, -1, -1, len(oov), False)])
	elif nextbest_matchlength > 3 and nextbest_matchlength + 1 == best_matchlength and len(nextbest_lexcandidates) < 30:
		return (oov, best_lexcandidates + nextbest_lexcandidates)
	else:
		return (oov, best_lexcandidates)

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Compute matches')
	
	subparsers = parser.add_subparsers(title='action')
	
	mode1 = subparsers.add_parser('mode1_genphrases', help='Generate phrases for one set')
	mode1.add_argument('oovfile'   , help='<- simple OOV list')
	mode1.add_argument('morffile'  , help='<- morf-segmented/-categorized OOV list')
	mode1.set_defaults(which='mode1_genphrases')
	
	mode1 = subparsers.add_parser('mode1_joinphrases_genbatches', help='Join phrases of all sets and generate TODOs')
	mode1.add_argument('batchsize' , type=int, help='batch size')
	mode1.add_argument('matchfile' , help='<> matchfile prefix')
	mode1.set_defaults(which='mode1_joinphrases_genbatches')
	
	mode2 = subparsers.add_parser('mode2', help='Reduce one TODO file')
	mode2.add_argument('lexfile'   , help='<- normalized lexicon')
	mode2.add_argument('todofile'  , help='<> TODO file / batch')
	mode2.set_defaults(which='mode2')
	
	mode3 = subparsers.add_parser('mode3', help='Join all results into matchfile')
	mode3.add_argument('noofbatches', type=int, help='number of batches')
	mode3.add_argument('matchfile'  , help='<> matchfile (prefix)')
	mode3.set_defaults(which='mode3')
	
	args = parser.parse_args()
	
	if args.which == 'mode1_genphrases':
		# First load data
		oov_original_list = guess_helper.load_file_lines(args.oovfile)
		catmorfdict = guess_helper.load_catmorfdict(oov_original_list, args.morffile)
		
		# Then generate all phrases
		all_phraseparts = []
		for _, segs in catmorfdict.items():
			all_phraseparts += itertools.chain(*guess_phrases.gen_phrases(segs))
		uniq_phraseparts = guess_helper.uniq_list(all_phraseparts) # uniq for unhashable lists!
		print("Matching {} ({} unique) phrases generated from {} unique words".format(len(all_phraseparts), len(uniq_phraseparts), len(catmorfdict.keys())), flush = True, file = sys.stderr)
		
		# ... to stdout!
		print("\n".join(uniq_phraseparts))
	elif args.which == 'mode1_joinphrases_genbatches':
		# ... and back in from stdin!
		all_uniq_phraseparts = sys.stdin.read().splitlines()
		
		print("Found", len(all_uniq_phraseparts), "phraseparts...", file = sys.stderr)
		
		# Filter those out that are already present in the matchfile
		try:
			with open(args.matchfile) as f:
				prev_matches = eval(f.read())
		except:
			prev_matches = {}
		new_uniq_phraseparts = list(filter(lambda p: p not in prev_matches, all_uniq_phraseparts))
		
		print("...", len(new_uniq_phraseparts), "new ones.", file = sys.stderr)
		
		# Finally write new TODOs in all files
		batches = [new_uniq_phraseparts[i:i + args.batchsize] for i in range(0, len(new_uniq_phraseparts), args.batchsize)]
		for (i, batch) in enumerate(batches):
			with open(args.matchfile + ".batch." + str(i + 1), 'w') as f: # files from 1 to len
				print(batch, file = f)
		
		# Now output the number of batches created for further handling
		print(len(batches))
	
	elif args.which == 'mode2':
		# Load matchers
		(matchers, _) = guess_helper.load_dictionary(args.lexfile)
		print("Matchers loaded!")
		
		with open(args.todofile) as f:
			batch = eval(f.read())
		
		print("Loaded batch {}".format(args.todofile))
		
		with closing(multiprocessing.Pool(processes = 8)) as pool:
			print("Opened the pool...", flush = True)
			data = list(zip(batch, itertools.repeat(matchers)))
			print("Let's start the starmap!", flush = True)
			result = dict(pool.starmap(lookup_oov, data))
		
		print("Writing results to {}".format(args.todofile + ".done"))
		
		with open(args.todofile + ".done", 'w') as f:
			print(result, file = f)
	
	elif args.which == 'mode3':
		# Load all previous matches
		try:
			with open(args.matchfile) as f:
				prev_matches = eval(f.read())
		except:
			prev_matches = {}
		
		# Add new matches!
		for i in range(args.noofbatches):
			with open(args.matchfile + ".batch." + str(i + 1) + ".done") as f: # files from 1 to len
				prev_matches.update(eval(f.read()))
		with open(args.matchfile, 'w') as f:
			print(prev_matches, file = f)
