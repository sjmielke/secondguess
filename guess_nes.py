from typing import Dict, Set

def desuffixize_ne(ne: str, ne_roots: [str]) -> str:
  return ne

# Mutates the `guesses` dict and returns all NE roots
def guess_nes_into(guesses: Dict[str, str], nes: [str]) -> Set[str]:
  # First desuffixize/group -> guess all NEs
  all_ne_roots = set()
  for ne_suf in sorted(nes):
    ne = desuffixize_ne(ne_suf, nes)
    #print("{:<20} ~~> is NE           {} -> {:<20}".format(ne, '✔' if ne == ne_suf else '✗', ne))
    guesses[ne_suf] = ne
    all_ne_roots.add(ne)
  return all_ne_roots
