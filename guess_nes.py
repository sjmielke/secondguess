from guess_helper import mapfst

def desuffixize_ne(ne: str, catmorfdict: "{str: [(str, str)]}") -> str:
	# We only want to cut away prefixes and suffixes, no infixes!
	stm_indices = [i for i, (morph, cat) in enumerate(catmorfdict[ne]) if cat == 'STM']
	return "".join(mapfst(catmorfdict[ne][stm_indices[0] : stm_indices[-1]+1]))

# Mutates the `guesses` dict and returns all NE roots
def guess_nes_into(oov_guesses: "{str: str}", catmorfdict: "{str: [(str, str)]}", nes: "[str]") -> "Set[str]":
	# First desuffixize/group -> guess all NEs
	all_ne_roots = set()
	for ne_suf in sorted(nes):
		ne = desuffixize_ne(ne_suf, catmorfdict)
		#print("{:<20} ~> NE: {:<20} {} -> {:<20}".format(ne_suf, " ".join(mapfst(catmorfdict[ne_suf])), '✔' if ne == ne_suf else '✗', ne))
		oov_guesses[ne_suf] = [(ne, 1.0)]
		all_ne_roots.add(ne)
	return all_ne_roots
