from typing import Dict

def get_guessables_into(guesses: Dict[str, str], fulluniqlist: [str], ne_list: [str]) -> ([str], [str]):
  guessable_nes = []
  guessable_oovs = []
  for w in list(set(fulluniqlist)):
    # Filter out non-alphabetic tokens
    if not any(c.isalpha() for c in w):
      #print("{:<20} ~~> non-alpha token".format(w))
      guesses[w] = w
    elif w in ne_list:
      guessable_nes.append(w)
    else:
      guessable_oovs.append(w)
  return (guessable_nes, guessable_oovs)
