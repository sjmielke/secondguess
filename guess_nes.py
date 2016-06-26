from typing import Dict, Set, List, Tuple

from guess_helper import mapfst

def desuffixize_ne(ne: str, catmorfdict: Dict[str, List[Tuple[str, str]]], ne_roots: [str]) -> str:
  # We only want to cut away prefixes and suffixes, no infixes!
  stm_indices = [i for i, (morph, cat) in enumerate(catmorfdict[ne]) if cat == 'STM']
  return "".join(mapfst(catmorfdict[ne][stm_indices[0] : stm_indices[-1]+1]))

# Mutates the `guesses` dict and returns all NE roots
def guess_nes_into(guesses: Dict[str, str], catmorfdict: Dict[str, List[Tuple[str, str]]], nes: [str]) -> Set[str]:
  # First desuffixize/group -> guess all NEs
  all_ne_roots = set()
  for ne_suf in sorted(nes):
    ne = desuffixize_ne(ne_suf, catmorfdict, nes)
    print("{:<20} ~> NE: {:<12} {} -> {:<20}".format(ne_suf, " ".join(mapfst(catmorfdict[ne_suf])), '✔' if ne == ne_suf else '✗', ne))
    guesses[ne_suf] = ne
    all_ne_roots.add(ne)
  return all_ne_roots
