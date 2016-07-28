import sys
import typing

CandidateWord = typing.NamedTuple('CandidateWord', [('oov', str), ('lexword', str), ('i_lex', int), ('i_oov', int), ('matchlength', int), ('islegal', bool)])

new_dict = {}

for filename in sys.argv[1:]:
  with open(filename) as f:
    new_dict.update(eval(f.read()))

print(new_dict)
