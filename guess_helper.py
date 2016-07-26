import itertools
import json
import re
from difflib import SequenceMatcher
from collections import defaultdict
import unicodedata

def uninorm(s: str):
	return unicodedata.normalize('NFKC', s)

def bold(s: str, i: int, k: int) -> str:
	return "\x1b[2m" + s[0:i] + "\x1b[1m" + s[i:i+k] + "\x1b[2m" + s[i+k:] + "\x1b[0m"

def load_file_lines(path: str) -> [str]:
	ls = []
	with open(path) as f:
		ls = uninorm(f.read()).splitlines()
	return ls

def load_config(setname):
	# Load pure JSON dict
	with open("pyguess.config") as f:
		conf = json.loads(uninorm(f.read()))
	
	# Insert specific setname
	if setname != None:
		def replacesetname(d):
			if isinstance(d, str):
				return d.replace(conf['set-placeholder'], setname)
			elif isinstance(d, float):
				return d
			else:
				return {k: replacesetname(v) for k, v in d.items()}
		return replacesetname(conf)
	else:
		return conf

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

def load_grammar(grammarfilename, pertainymfilename) -> "([str], [(str, str)], [(str, str)], {str: str})":
	noun_adjective_dict = {}
	
	with open(pertainymfilename) as pertainymfile:
		for line in pertainymfile.read().splitlines():
			match = re.search(r'^::s-(adj|noun) (.*) ::t-(adj|noun) (.*)$', line)
			if match == None:
				continue
			cat1, w1, cat2, w2 = match.groups()
			if cat1 == "adj" and cat2 == "noun":
				tmp = w1
				w1 = w2
				w2 = tmp
			noun_adjective_dict[w1.strip()] = w2.strip()

	# grep '::synt noun suffix' grammar.uig-v02.txt | grep ::eng | sed 's/ ::synt noun suffix ::function /	/;s/	.*::eng /	/;s/::uig //;s/ ::.*$//'

	adjectivizers, prefixers, suffixers = [], [], []
	
	with open(grammarfilename) as grammarfile:
		for line in grammarfile.read().splitlines():
			if "::synt noun suffix" in line:
				uig = re.search(r'::uig ([^:]*) ::', line).group(1)
				if "adjectivizer" in line:
					adjectivizers.append(uig)
				elif "::eng" in line:
					all_eng = re.search(r'::eng ([^:]*)', line).group(1).strip()
					eng_alternatives = all_eng.split(';')
					for raweng in eng_alternatives:
						eng = re.sub(r'\([^\(\)]+\)', '', raweng).strip()
						eng_words = eng.split()
						newphrases = [""]
						for word in eng_words:
							if '/' in word:
								choices = word.split('/')
								newnewphrases = []
								for choice in choices:
									newnewphrases.append(list(map(lambda p: p + ' ' + choice, newphrases)))
								newphrases = itertools.chain(*newnewphrases)
							else:
								newphrases = list(map(lambda p: p + ' ' + word, newphrases))
						for eng in newphrases:
							eng = eng[1:]
							if eng[0] == "'":
								suffixers.append((uig, ' ' + eng))
							elif eng[0] == "-":
								suffixers.append((uig, eng[1:]))
							else:
								prefixers.append((uig, eng + ' '))

	return (adjectivizers, prefixers, suffixers, noun_adjective_dict)


def mapfst(l):
	return tuple(map(lambda x: tuple(x)[0], l))

def uniq_list(l):
	return [k for k,v in itertools.groupby(sorted(l))]
