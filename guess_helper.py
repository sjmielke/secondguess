from difflib import SequenceMatcher
from collections import defaultdict

def bold(s: str, i: int, k: int) -> str:
	return "\x1b[2m" + s[0:i] + "\x1b[1m" + s[i:i+k] + "\x1b[2m" + s[i+k:] + "\x1b[0m"

def load_file_lines(path: str) -> [str]:
	ls = []
	with open(path) as f:
		ls = f.read().splitlines()
	return ls

def load_dictionary(path: str) -> ("Dict[str: SequenceMatcher]", "Dict[str: Set[str]]"):
	matchers = {}
	translations = defaultdict(set)
	for line in load_file_lines(path):
		(w, _, t) = line.split('\t')
		matchers[w] = SequenceMatcher(a=None, b=w, autojunk=False)
		translations[w].add(t)
	#print("{} distinct dictionary words to compare against loaded.".format(len(matchers.keys())))
	return (matchers, translations)

def load_catmorfdict(oov_original_list, morffile):
	morfoutput = load_file_lines(morffile)
	cleanmorfstring = lambda s: list(map(lambda seg: seg.split('|'), s.split()))
	return dict(zip(oov_original_list, map(cleanmorfstring, morfoutput)))

def mapfst(l):
	return map(lambda x: x[0], l)
