def bold(s: str, i: int, k: int) -> str:
  return "\x1b[2m" + s[0:i] + "\x1b[1m" + s[i:i+k] + "\x1b[2m" + s[i+k:] + "\x1b[0m"

def load_file_lines(path: str) -> [str]:
  ls = []
  with open(path) as f:
    ls = f.read().splitlines()
  return ls
