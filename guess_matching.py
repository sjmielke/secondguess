from difflib import SequenceMatcher
from contextlib import closing
import multiprocessing
import typing # NamedTuple
import itertools
import sys # stderr
import argparse

import guess_helper
import guess_phrases

CandidateWord = typing.NamedTuple('CandidateWord', [('oov', str), ('lexword', str), ('i_lex', int), ('i_oov', int), ('matchlength', int), ('islegal', bool)])

# mono2affix_min5_match3
def is_legal_match(w1: str, w2: str, i1: int, i2: int, l: int) -> bool:
	i2_ = len(w1) - (i1 + l)
	return l >= 3 and (l / len(w1) > 0.9 or (i1 == 0 or i2_ == 0) and i1 + i2_ <= 2 and l >= 5)

def get_best_match(oov: str, lexword: str, matcher: SequenceMatcher) -> (str, (int, int, int)):
	matcher.set_seq1(oov)
	i_o, i_w, matchlength = matcher.find_longest_match(0, len(oov), 0, len(lexword))
	return (lexword, (i_o, i_w, matchlength))

def lookup_oov(oov: str, matchers: "{str: SequenceMatcher}") -> "(str, [CandidateWord])":
	# Match search
	best_lexcandidates = []
	best_matchlength = 0
	found_legal = False
	
	# First find LCS = match with lexword in a mapreduce fashion
	all_pairs = map(lambda w: (oov, w, matchers[w]), sorted(matchers.keys()))
	
	individual_bestmatches = itertools.starmap(get_best_match, all_pairs)
	
	# Now compare all findings!
	#print(" ")
	#print("?")
	for (lexword, (i_o, i_w, matchlength)) in individual_bestmatches:
		if found_legal and (matchlength < 3 or matchlength < best_matchlength):
			continue
		legal = is_legal_match(lexword, oov, i_w, i_o, matchlength)
		if not found_legal or legal: # no legality regressions!
			if (legal and not found_legal # we find our first legal match...
					or matchlength > best_matchlength): # ...or a better one, regardless of legality status
				best_lexcandidates = [CandidateWord(oov, lexword, i_w, i_o, matchlength, legal)]
				best_matchlength = matchlength
			elif matchlength == best_matchlength: # no improvement? just add a candidate
				best_lexcandidates.append(CandidateWord(oov, lexword, i_w, i_o, matchlength, legal))
		if legal:
			found_legal = True
	#print("!")
	#print(" ")
	
	# If we didn't find anything legal, guess we just copy:
	if not found_legal:
		return (oov, [CandidateWord(oov, oov, -1, -1, len(oov), False)])
	else:
		return (oov, best_lexcandidates)

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Compute matches')
	
	subparsers = parser.add_subparsers(title='action')
	
	mode1 = subparsers.add_parser('mode1', help='Generate phrases and TODOs')
	mode1.add_argument('oovfile'   , help='<- simple OOV list')
	mode1.add_argument('morffile'  , help='<- morf-segmented/-categorized OOV list')
	mode1.add_argument('matchfile' , help='-> matchfile prefix')
	mode1.set_defaults(which='mode1')
	
	mode2 = subparsers.add_parser('mode2', help='Reduce one TODO file')
	mode2.add_argument('lexfile'   , help='<- normalized lexicon')
	mode2.add_argument('todofile'  , help='<> TODO file / batch')
	mode2.set_defaults(which='mode2')
	
	mode3 = subparsers.add_parser('mode3', help='Join all results into matchfile')
	mode3.add_argument('noofbatches', type=int, help='number of batches')
	mode3.add_argument('matchfile'  , help='<> matchfile (prefix)')
	mode3.set_defaults(which='mode3')
	
	args = parser.parse_args()
	
	if args.which == 'mode1':
		# First load data
		oov_original_list = guess_helper.load_file_lines(args.oovfile)
		catmorfdict = guess_helper.load_catmorfdict(oov_original_list, args.morffile)
		
		# Then generate all phrases
		all_phrases = []
		for _, segs in catmorfdict.items():
			all_phrases += itertools.chain(*guess_phrases.gen_phrases(segs))
		uniq_phrases = [k for k,v in itertools.groupby(sorted(all_phrases))] # uniq for unhashable lists!
		print("Matching {} ({} unique) phrases generated from {} unique words".format(len(all_phrases), len(uniq_phrases), len(catmorfdict.keys())), flush = True, file = sys.stderr)
		
		# Finally write TODOs in all files
		batchsize = 50
		batches = [uniq_phrases[i:i + batchsize] for i in range(0, len(uniq_phrases), batchsize)]
		for (i, batch) in enumerate(batches):
			with open(args.matchfile + ".batch." + str(i + 1), 'w') as f: # files from 1 to len
				print(batch, file = f)
		
		# Now output the number of batches created for further handling
		print(len(batches))
	
	elif args.which == 'mode2':
		# Load matchers
		(matchers, _) = guess_helper.load_dictionary(args.lexfile)
		
		with open(args.todofile) as f:
			batch = eval(f.read())
		with closing(multiprocessing.Pool(processes = 8)) as pool:
			data = list(zip(batch, itertools.repeat(matchers)))
			result = dict(pool.starmap(lookup_oov, data))
		with open(args.todofile + ".done", 'w') as f:
			print(result, file = f)
	
	elif args.which == 'mode3':
		d = {}
		for i in range(args.noofbatches):
			with open(args.matchfile + ".batch." + str(i + 1) + ".done") as f: # files from 1 to len
				d.update(eval(f.read()))
		with open(args.matchfile, 'w') as f:
			print(d, file = f)
