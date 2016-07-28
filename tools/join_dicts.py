import sys

new_dict = {}

for filename in sys.argv[1:]:
  with open(filename) as f:
    new_dict.update(eval(f.read()))

print(new_dict)
