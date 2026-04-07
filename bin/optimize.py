#!/usr/bin/env pypy3

import shutil
import subprocess
import string
import zipfile
import tempfile
from concurrent.futures import ProcessPoolExecutor
import os
import re
import math
import random
import multiprocessing
from collections import Counter
from ast import literal_eval
import signal
from dataclasses import dataclass, field, fields
import statistics
import sys
from itertools import permutations

@dataclass(slots=True)
class Score:
	effort: float = 0
	sfb: float = 0
	rolling: float = 0
	scissors: float = 0

@dataclass(slots=True)
class Layout:
	letters: list[list[str]]
	score: Score = field(default_factory=lambda: Score())
	total: int = 0
	left_usage: int = 0
	right_usage: int = 0
	source: str = ""

	def clone(self):
		return Layout(
			[row[:] for row in self.letters],
			source=self.source,
		)

	def __post_init__(self):
		self.letters = [r[:] for r in self.letters]
		self.calc_scores()
		if SCORE_MEDIAN is not None:
			self.calc_total_score()

	def __eq__(self, other):
		if not isinstance(other, Layout):
			return False
		return self.letters == other.letters or self.flatten() == other.flatten_reverse()

	def __hash__(self):
		return hash(tuple(tuple(r) for r in self.letters))

	def calc_scores(self):
		_effort_grid = EFFORT_GRID
		_finger_grid = FINGER_GRID
		_bigrams = BIGRAMS
		_trigrams = TRIGRAMS
		pos = {}

		sfb = 0
		rolling = 0
		scissors = 0

		self.score = Score()
		self.left_usage = 0
		self.right_usage = 0

		for r in range(ROWS):
			for c in range(COLS):
				ch = self.letters[r][c]
				if ch:
					pos[ch] = (r*COLS) + c
					try:
						l = LETTERS[ch]
					except KeyError:
						print('======= ERROR')
						print_layout(self)
						sys.exit(1)
					self.score.effort += l * _effort_grid[r][c]
					if c < 5:
						self.left_usage += l
					else:
						self.right_usage += l
		total_usage = self.left_usage + self.right_usage
		balance = abs(self.left_usage - self.right_usage) / total_usage
		self.score.effort *= 1 + max(0, balance - 0.1) * 10

		stats = {ch: (r, c, _finger_grid[r][c], _effort_grid[r][c], c<5, 4<=c<=5) for r in range(ROWS) for c in range(COLS) if (ch := self.letters[r][c])}

		max_sum = MAX_E * 2
		K = max_sum ** 2
		for pair, count in _bigrams.items():
			a, b = pair[0], pair[1]
			if a not in pos or b not in pos:
				continue
			r1, c1, f1, e1, h1, is_center1 = stats[a]
			r2, _, f2, e2, h2, is_center2 = stats[b]
			if h1 != h2: continue
			row_delta = abs(r1 - r2)
			is_center = is_center1 or is_center2
			i = (a in VOWELS) + (b in VOWELS)

			# sfb
			if f1 == f2:
				weight = 1.0
				weight *= CENTER_WEIGHT if is_center else 1.0
				weight *= (ROW_WEIGHT ** -row_delta)
				sfb += count * weight * (e1+e2)
			else:
				has_gap = abs(f1-f2) > 1
				# scissors
				if is_center or (not has_gap and row_delta == 2) :
					scissors += count * (e1+e2)
				else: # rolling
					weight = 1.0
					if f1 > f2: # inroll
						weight = [0.7, 1.0, 0.5][i]
					elif f1 < f2: # outroll
						weight = [0.4, 0.6, 0.3][i]
					weight *= (GAP_WEIGHT ** has_gap)
					weight *= (ROW_WEIGHT ** row_delta)
					rolling += count * weight * (K / (e1+e2))

		max_sum = MAX_E * 3
		min_sum = MIN_E * 3
		K = max_sum ** 2
		for pair, count in _trigrams.items():
			a, b, c = pair[0], pair[1], pair[2]
			if a not in pos or b not in pos or c not in pos:
				continue
			r1, c1, f1, e1, h1, is_center1 = stats[a]
			r2, _, f2, e2, h2, is_center2 = stats[b]
			r3, c3, f3, e3, h3, is_center3 = stats[c]
			is_center = is_center1 or is_center2 or is_center3
			row_delta1 = abs(r1 - r2)
			row_delta2 = abs(r2 - r3)
			row_delta_sum = row_delta1 + row_delta2
			has_gap1 = abs(f1 - f2) > 1
			has_gap2 = abs(f2 - f3) > 1
			has_gap_sum = has_gap1 + has_gap2

			# sfs
			if f1 == f3 and f1 != f2:
				weight = CENTER_WEIGHT if (4<=c1<=5 or 4<=c3<=5) else 1.0
				weight *= (ROW_WEIGHT ** abs(r1-r3))
				sfb += count * weight * (e1+e3)

			# rolling
			if (h1 == h2 == h3) and f1 != f2 and f2 != f3 and f1 != f3 and \
					not is_center and row_delta1 != 2 and row_delta2 != 2:
				i = (a in VOWELS) + (b in VOWELS) + (c in VOWELS)
				if (f1 > f2 > f3): # inroll
					weight = [0.6, 1.0, 0.7, 0.3][i]
				elif (f1 < f2 < f3): # outroll
					weight = [0.4, 0.6, 0.5, 0.2][i]
				else: # redirect
					weight = [-0.6, -1.0, -0.7, -0.3][i]

				if weight > 0:
					s = 1
					e = K / (e1+e2+e3)
				else:
					s = -1
					e = K / ((max_sum + min_sum) - (e1+e2+e3))
				weight *= GAP_WEIGHT ** (s * has_gap_sum)
				weight *= ROW_WEIGHT ** (s * row_delta_sum)
				rolling += count * weight * e

		self.score.sfb = sfb
		self.score.rolling = rolling
		self.score.scissors = scissors

	def calc_total_score(self):
		def norm(v, m, d):
			if d == 0: return 0
			return (v - m) / d

		r = Score(
			effort=norm(self.score.effort, SCORE_MEDIAN.effort, SCORE_SCALE.effort),
			sfb=norm(self.score.sfb, SCORE_MEDIAN.sfb, SCORE_SCALE.sfb),
			rolling=norm(self.score.rolling, SCORE_MEDIAN.rolling, SCORE_SCALE.rolling),
			scissors=norm(self.score.scissors, SCORE_MEDIAN.scissors, SCORE_SCALE.scissors),
		)

		self.total = int((
			(-r.effort) * SCORE_RATES.effort +
			(-r.sfb) * SCORE_RATES.sfb +
			(r.rolling) * SCORE_RATES.rolling +
			(-r.scissors) * SCORE_RATES.scissors
		) * 1e9)

	def flatten(self):
		return [item for row in self.letters for item in row]

	def flatten_reverse(self):
		return [item for row in self.letters for item in row[::-1]]

TMP_PATH = None
ANALYZE_RESULT_FILENAME = 'analyze_result.tsv'
RESULT_FILENAME = 'result.txt'

LETTERS = Counter()
BIGRAMS = Counter()
TRIGRAMS = Counter()

VOWELS = 'aeiouy'
ROWS = 3
COLS = 10
EFFORT_GRID = [
	[3.3, 1.8, 1.5, 2.0, 5.0],
	[1.5, 1.2, 1.0, 1.0, 4.0],
	[2.8, 2.3, 2.0, 1.5, 4.5],
]
EFFORT_GRID = [r + r[::-1] for r in EFFORT_GRID]
MAX_E = max(val for row in EFFORT_GRID for val in row)
MIN_E = min(val for row in EFFORT_GRID for val in row)

FINGER_GRID = [
	[4, 3, 2, 1, 1],
	[4, 3, 2, 1, 1],
	[4, 3, 2, 1, 1],
]
FINGER_GRID = [r + [v + 4 for v in r[::-1]] for r in FINGER_GRID]

SCORE_RATES = Score(
	sfb = 0.30,
	scissors = 0.30,
	rolling = 0.30,
	effort = 0.10,
)
SCORE_MEDIAN = Score()
SCORE_SCALE = Score()


GAP_WEIGHT = 0.8
ROW_WEIGHT = 0.9
HAND_WEIGHT = 0.7
CENTER_WEIGHT = 2.0

EXT_TEXT = {
	'.md', '.markdown',
	'.txt', '.text',
	'.rst',
	'.adoc', '.asciidoc', '.asc',
	'.org',
	'.tex',
	'.LICENSE', 'LICENSE',
	'readme', 'README',
	'.html', '.htm',
	'.json',
	'.fxml', '.xml', '.svg', '.vue',
}

EXT_C_STYLE = {
	'.c', '.h',
	'.cpp', '.hpp', '.cc', '.hh',
	'.cxx', '.hxx',
	'.dts', '.dtsi',
	'.ino',
	'.cs',
	'.java',
	'.kt', '.kts',
	'.scala',
	'.go',
	'.rs',
	'.zig',
	'.js', '.jsx', '.mjs',
	'.ts', '.tsx',
	'.swift',
	'.m', '.mm',
	'.php',
	'.groovy',
	'.gradle',
	'.css', '.scss', '.less',
	'.v', '.sv',
	'.dart', '.sol', '.proto',
}

EXT_SCRIPT_STYLE = {
	'.py',
	'.rb',
	'.sh', '.bash', '.zsh', '.fish',
	'.conf', '.cfg',
	'.gitconfig', '.gitignore',
	'.pl', '.pm',
	'.R', '.r',
	'.jl',
	'.ex', '.exs',
	'.yaml', '.yml', '.toml',
	'.dockerfile', 'Dockerfile',
	'Makefile', '.mk', '.make',
	'.cmake',
}

EXT_DASH_STYLE = {
	'.sql',
	'.lua',
	'.hs', '.lhs',
	'.vhd', '.vhdl',
	'.elm',
	'.ada', '.adb', '.ads',
}

EXT_PERCENT_STYLE = {
	'.erl', '.hrl',
}

EXT_SEMI_STYLE = {
	'.asm', '.s', '.S',
	'.clj', '.cljs', '.cljc', '.edn',
	'.lisp', '.lsp', '.scm',
	'.ini',
}

EXT_PAREN_STAR_STYLE = {
	'.ml', '.mli',
	'.fs', '.fsi', '.fsx',
	'.pas', '.pp',
}

EXTENSIONS = EXT_TEXT | EXT_C_STYLE | EXT_SCRIPT_STYLE | EXT_DASH_STYLE | EXT_PERCENT_STYLE | EXT_SEMI_STYLE | EXT_PAREN_STAR_STYLE

def unflatten(flat, rows=ROWS, cols=COLS):
	return [flat[i*cols:(i+1)*cols] for i in range(rows)]

def layout_key(l):
	return (
		l.total,
		l.left_usage,
		-l.score.sfb,
		-l.score.scissors,
		-l.score.effort,
		l.score.rolling,
	)

def best_layout(layouts: list[Layout]):
	return max(layouts, key=layout_key).clone()

def sort_layouts(layouts: list[Layout]):
	layouts.sort(key=layout_key, reverse=True)
	return layouts

def sort_unique_layouts(layouts: list[Layout], size):
	layouts = sort_layouts(list(set(layouts)))
	result = []

	for layout in layouts:
		if len(result) == size:
			break
		is_unique = True
		a = layout.flatten()
		for l in result:
			if layout == l or \
					9 >= sum(1 for c1, c2 in zip(a, l.flatten()) if c1 != c2) or \
					9 >= sum(1 for c1, c2 in zip(a, l.flatten_reverse()) if c1 != c2):
				is_unique = False
				break

		if is_unique:
			result.append(layout)

	return result

def init_score_state():
	global SCORE_MEDIAN, SCORE_SCALE
	def iqr(v):
		q = statistics.quantiles(v, n=4, method="inclusive")
		return q[2] - q[0]

	base_layout = make_initial_layout()
	unique_layouts = {base_layout.clone()}
	while len(unique_layouts) < 10000:
		unique_layouts.add(make_random())
	layouts = list(unique_layouts)

	vals = {f.name: [getattr(l.score, f.name) for l in layouts] for f in fields(Score)}

	med_map = {}
	iqr_map = {}
	for k, v in vals.items():
		d = iqr(v)
		med = statistics.median(v)
		if d == 0:
			d = max(abs(med), 1) * 1e-9

		iqr_map[k] = d
		med_map[k] = med

	SCORE_SCALE = Score(**iqr_map)
	SCORE_MEDIAN = Score(**med_map)

def download_target(url, dest):
	repo_name = url.rstrip('/').split('/')[-1]
	base_url = url.rstrip('/') + '/zipball/HEAD'
	suffix = ''.join(random.choices(string.ascii_lowercase, k=4))
	target_dir = os.path.join(dest, f"{repo_name}_{suffix}")
	os.makedirs(target_dir, exist_ok=True)

	z = os.path.join(target_dir, f'{repo_name}.zip')
	try:
		subprocess.run(
			[
				'curl', '-L', '-f', '-s',
				'--connect-timeout', '30',
				'--retry', '3',
				'--retry-delay', '2',
				'-o', z, base_url
			],
			check=True, capture_output=True
		)

		if zipfile.is_zipfile(z):
			with zipfile.ZipFile(z, 'r') as zz:
				zz.extractall(target_dir)
	except Exception as e:
		print(e)
		if os.path.exists(z):
			os.remove(z)
		return False

	os.remove(z)
	return True

def cleanup(_sig, _frame):
	global TMP_PATH
	try:
		if TMP_PATH and os.path.exists(TMP_PATH):
			shutil.rmtree(TMP_PATH)
	except Exception:
		pass
	sys.exit(1)

def save_analyze_result(result_path):
	file_path = os.path.join(result_path, ANALYZE_RESULT_FILENAME)

	with open(file_path, 'w', encoding='utf-8') as f:
		f.write('letter\tfrequency\n')
		for ch, count in LETTERS.most_common():
			f.write(f'{ch}\t{count}\n')

		f.write('\nbigram\tfrequency\n')
		for bg, count in BIGRAMS.most_common():
			f.write(f'{bg}\t{count}\n')

		f.write('\ntrigram\tfrequency\n')
		for tg, count in TRIGRAMS.most_common():
			f.write(f'{tg}\t{count}\n')

def load_analysis_result(result_path):
	global LETTERS, BIGRAMS, TRIGRAMS

	file_path = os.path.join(result_path, ANALYZE_RESULT_FILENAME)

	with open(file_path, 'r', encoding='utf-8') as f:
		section = None
		for line in f:
			line = line.rstrip('\n')
			if not line:
				continue
			if line.startswith('letter\t'):
				section = 'letters'
				continue
			elif line.startswith('bigram\t'):
				section = 'bigrams'
				continue
			elif line.startswith('trigram\t'):
				section = 'trigrams'
				continue

			if section == 'letters':
				ch, count = line.split('\t')
				LETTERS[ch] = int(count)
			elif section == 'bigrams':
				bg, count = line.split('\t')
				BIGRAMS[bg] = int(count)
			elif section == 'trigrams':
				tg, count = line.split('\t')
				TRIGRAMS[tg] = int(count)

def analyze_target_single(full_path):
	letters = Counter()
	bigrams = Counter()
	trigrams = Counter()
	pattern = re.compile('[a-z]+', re.IGNORECASE)
	try:
		with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
			for line in f:
				groups = pattern.findall(line)
				for g in groups:
					word = g.lower()
					word = [ch for ch in word if 'a' <= ch <= 'z']
					n = len(word)

					for i in range(n):
						c1 = word[i]
						letters[c1] += 1
						if i < n - 1:
							c2 = word[i+1]
							if c1 != c2:
								bigrams[c1+c2] += 1
								if i < n - 2:
									c3 = word[i+2]
									trigrams[c1+c2+c3] += 1
	except (FileNotFoundError, PermissionError, IsADirectoryError) as e:
		print(f'Failed: {full_path} — {e}')

	return letters, bigrams, trigrams

def analyze_target(result_path):
	global LETTERS, BIGRAMS, TRIGRAMS, TMP_PATH

	targets = [
		'https://github.com/torvalds/linux',            # C
		'https://github.com/opencv/opencv',             # C++
		'https://github.com/gcc-mirror/gcc',            # C++
		'https://github.com/llvm/llvm-project',         # C++/C
		'https://github.com/python/cpython',            # C/Python
		'https://github.com/numpy/numpy',               # Python/C
		'https://github.com/django/django',             # Python
		'https://github.com/psf/requests',              # Python
		'https://github.com/facebook/react',            # JavaScript/TypeScript
		'https://github.com/reactjs/react.dev',
		'https://github.com/microsoft/vscode',          # TypeScript
		'https://github.com/sveltejs/svelte',           # JavaScript/TypeScript
		'https://github.com/nodejs/node',               # JavaScript/C++
		'https://github.com/denoland/deno',             # TypeScript/Rust
		'https://github.com/kubernetes/kubernetes',     # Go
		'https://github.com/golang/go',                 # Go
		'https://github.com/rust-lang/rust',            # Rust
		'https://github.com/rust-lang/book',            # Rust
		'https://github.com/rust-lang/cargo',            # Rust
		'https://github.com/rust-lang/rfcs',            # Rust
		'https://github.com/theseus-os/Theseus',        # Rust
		'https://github.com/bytecodealliance/wasmtime', # Rust
		'https://github.com/sharkdp/fd',                # Rust
		'https://github.com/ziglang/zig',               # Zig
		'https://github.com/vlang/v',                   # V
		'https://github.com/nim-lang/Nim',              # Nim
		'https://github.com/carbon-language/carbon-lang', # Carbon
		'https://github.com/ValeLang/Vale',             # Vale
		'https://github.com/rails/rails',               # Ruby
		'https://github.com/elixir-lang/elixir',        # Elixir
		'https://github.com/apple/swift',               # Swift
		'https://github.com/JetBrains/kotlin',          # Kotlin
		'https://github.com/php/php-src',               # PHP
		'https://github.com/lua/lua',                   # Lua
		'https://github.com/ghc/ghc',                   # Haskell
		'https://github.com/scala/scala',               # Scala
		'https://github.com/wch/r-source',              # R
		'https://github.com/dotnet/runtime',            # C#
		'https://github.com/openjdk/jdk',               # Java
		'https://github.com/ohmyzsh/ohmyzsh',           # Shell
		'https://github.com/copy/v86',                  # Assembly/JavaScript
		'https://github.com/cirosantilli/x86-bare-metal-examples', # Assembly/C
		'https://github.com/mit-pdos/xv6-public',       # C/Assembly
		'https://github.com/redox-os/redox',            # Rust/Assembly
		'https://github.com/SerenityOS/serenity',       # C++/Assembly
		'https://github.com/u-boot/u-boot',             # C/Assembly
		'https://github.com/coreboot/coreboot',         # C/Assembly
		'https://github.com/Maratyszcza/PeachPy',       # Python/Assembly
		'https://github.com/netwide-assembler/nasm',    # Assembly
		'https://github.com/BeaEngine/BeaEngine',       # Assembly/C
		'https://github.com/ApolloTeam-dev/AROS',       # C/Assembly
		'https://github.com/mdn/content',
		'https://github.com/progit/progit2',
		'https://github.com/tldr-pages/tldr',
		'https://github.com/docker/docs',
		'https://github.com/pytorch/examples',
		'https://github.com/GITenberg/Moby-Dick--Or-The-Whale_2701',
		'https://github.com/GITenberg/The-Adventures-of-Sherlock-Holmes_1661',
		'https://github.com/GITenberg/The-Great-Gatsby_64317',
		'https://github.com/GITenberg/Alice-s-Adventures-in-Wonderland_11',
	]

	# Download
	len_targets = len(targets)
	TMP_PATH = tempfile.mkdtemp(dir=os.path.expanduser('~'), prefix='keeb')
	print('[Download Target]')
	downloaded = 0
	for url in targets:
		if download_target(url, TMP_PATH):
			downloaded += 1
			print(f'\r\033[K{downloaded}/{len_targets} ({downloaded/len_targets*100:.1f}%)', end='')
		else:
			print(f'Failed {url}')
	print(f'\r\033[K...Done')

	# file list
	files = []
	for root, _, fs in os.walk(TMP_PATH):
		for file in fs:
			name, ext = os.path.splitext(file)
			if ext.lower() in EXTENSIONS or name.lower() == 'readme':
				files.append(os.path.join(root, file))

	# Calc LETTERS, BIGRAMS
	print('[Analyze Target]')
	letters = Counter()
	bigrams = Counter()
	trigrams = Counter()
	len_files = len(files)
	with ProcessPoolExecutor() as executor:
		for i, (l, b, t) in enumerate(executor.map(analyze_target_single, files), 1):
			letters += l
			bigrams += b
			trigrams += t
			print(f'\r\033[K{i}/{len_files} ({i/len_files*100:.1f}%)', end='')

	LETTERS = letters

	total_count = sum(bigrams.values())
	threshold = total_count * 0.99
	cumulative = 0
	for bigram, count in bigrams.most_common():
		cumulative += count
		BIGRAMS[bigram] = count
		if cumulative >= threshold:
			break

	total_count = sum(trigrams.values())
	threshold = total_count * 0.9
	cumulative = 0
	for trigram, count in trigrams.most_common():
		cumulative += count
		TRIGRAMS[trigram] = count
		if cumulative >= threshold:
			break

	shutil.rmtree(TMP_PATH)
	print(f'\r\033[K...Done')

	# Store result
	save_analyze_result(result_path)

def make_initial_layout() -> Layout:
	coords = []
	for r in range(ROWS):
		for c in range(COLS):
			coords.append((EFFORT_GRID[r][c], r, c))
	coords.sort()

	letters_sorted = [ch for ch, _ in LETTERS.most_common()]
	letters = [['' for _ in range(COLS)] for _ in range(ROWS)]
	for i, (_, r, c) in enumerate(coords):
		if i < len(letters_sorted):
			letters[r][c] = letters_sorted[i]

	return Layout(letters, source='init')

def make_random() -> Layout:
	letters = list(LETTERS.keys())
	letters.extend([''] * ((COLS*ROWS) - len(letters)))
	random.shuffle(letters)
	return Layout(unflatten(letters), source="random")

def crossover(parents: list[Layout], blank=''):
	parent1 = parents[0].flatten()
	parent2 = parents[1].flatten()
	length = len(parent1)

	a, b = sorted(random.sample(range(length), 2))
	child = [blank] * length
	for i in range(length):
		if parent1[i] == blank:
			child[i] = blank
	child[a:b] = parent1[a:b]

	for i in range(length):
		target = parent2[i]
		if target == blank: continue
		if target in child: continue
		for j in range(length):
			if child[j] == blank:
				child[j] = target
				break

	return Layout(unflatten(child), source=parents[0].source+"->crossover")

def fine_tune_effort(base_layout: Layout):
	letters = [row[:] for row in base_layout.letters]
	positions = [(r,c) for r in range(ROWS) for c in range(COLS)]
	positions.sort(key=lambda pos: LETTERS.get(letters[pos[0]][pos[1]], 0), reverse=True)
	candidates = [base_layout.clone()]

	for (r,c) in positions:
		l = [row[:] for row in base_layout.letters]
		best = (r,c)
		for dr in (-1,0,1):
			for dc in (-1,0,1):
				nr, nc = r + dr, c + dc
				if 0 <= nr < ROWS and 0 <= nc < COLS:
					if EFFORT_GRID[nr][nc] < EFFORT_GRID[best[0]][best[1]]:
						best = (nr , nc)
		l[r][c], l[best[0]][best[1]] = l[best[0]][best[1]], l[r][c]
		candidates.append(Layout(l))

	best = best_layout(candidates)
	best.source = base_layout.source+"->fine_tune" if best != base_layout else base_layout.source
	return best

def optimize_effort(base_layout: Layout, result_len):
	orders = ['effort_asc', 'effort_desc', 'count_asc', 'count_desc']
	letters = [row[:] for row in base_layout.letters]
	layouts = {base_layout.clone()}

	for order in orders:
		effort_levels = list({val for row in EFFORT_GRID for val in row})

		if order == 'effort_asc':
			effort_levels.sort()
		elif order == 'effort_desc':
			effort_levels.sort(reverse=True)
		else:
			effort_counts = {val: sum(1 for r in range(ROWS) for c in range(COLS) if EFFORT_GRID[r][c] == val) for val in effort_levels}
			if order == 'count_asc':
				effort_levels.sort(key=lambda x: effort_counts[x])
			elif order == 'count_desc':
				effort_levels.sort(key=lambda x: -effort_counts[x])

		for effort_level in effort_levels:
			group_coords = [(r, c) for r in range(ROWS) for c in range(COLS) if abs(EFFORT_GRID[r][c] - effort_level) <= (effort_level * 0.5)]
			random.shuffle(group_coords)

			for i in range(len(group_coords)):
				r1, c1 = group_coords[i]
				for j in range(i+1, len(group_coords)):
					r2, c2 = group_coords[j]
					if letters[r1][c1] == letters[r2][c2]: continue
					l = [row[:] for row in letters]
					l[r1][c1], l[r2][c2] = l[r2][c2], l[r1][c1]
					layouts.add(Layout(l, source=base_layout.source+"->effort"))

	return sort_unique_layouts(list(layouts), result_len)

def optimize_swap(base_layout: Layout, temperature, max_temp, fix=0):
	n = None
	t = temperature / max_temp
	if fix == 0:
		if t > 0.6:
			n = random.choices([6, 7, 8], weights=[0.4, 0.4, 0.2], k=1)[0]
		elif t > 0.2:
			n = random.choices([4, 5, 6], weights=[0.5, 0.3, 0.2], k=1)[0]
		else:
			n = random.choices([2, 3, 4], weights=[0.7, 0.2, 0.1], k=1)[0]
	else:
		n = fix

	all_coords = [(r, c) for r in range(ROWS) for c in range(COLS)]
	coords = random.sample(all_coords, n)
	letters = [row[:] for row in base_layout.letters]

	shuffled = coords[:]
	random.shuffle(shuffled)

	for i in range(n):
		r1, c1 = coords[i]
		r2, c2 = shuffled[i]
		letters[r1][c1], letters[r2][c2] = letters[r2][c2], letters[r1][c1]

	return Layout(letters, source=base_layout.source)

def optimize_shuffle(base_layout: Layout, result_len, length=6, custom=""):
	base_letters = base_layout.letters

	if custom:
		target_positions = [
			(r, c) for r in range(ROWS) for c in range(COLS)
			if base_letters[r][c] in custom
		]
	else:
		all_positions = [(r, c) for r in range(ROWS) for c in range(COLS)]
		target_positions = random.sample(all_positions, length)

	letters = [base_letters[r][c] for r, c in target_positions]
	layouts = [base_layout.clone()]
	perms = permutations(target_positions, len(target_positions))

	l = [r[:] for r in base_layout.letters]
	for perm in perms:
		for i, (r, c) in enumerate(perm):
			l[r][c] = letters[i]
		layouts.append(Layout(l, source=base_layout.source+"->shuffle"))

	if custom:
		return sort_layouts(list(set(layouts)))[:result_len]
	else:
		return sort_unique_layouts(layouts, result_len)

def optimize_sa(base_layout: Layout, result_len, max_iter=10000, cooling_rate=0.9985):
	best = base_layout.clone()
	cur = base_layout.clone()
	initial_temp = max(abs(base_layout.total) * 0.005, 50)
	stop_temp = initial_temp * 1e-5
	temperature = initial_temp
	result = [best.clone()]

	for i in range(max_iter):
		new_layout = optimize_swap(cur, temperature, initial_temp)
		diff = new_layout.total - cur.total

		if diff >= 0:
			accept = True
		else:
			T = max(temperature, 1e-9)
			prob = math.exp(diff / T)
			accept = prob > random.random()

		if accept:
			cur = new_layout
			if cur.total > best.total:
				best = cur.clone()
				best.source += f"->sa_{i}"
				result.append(best.clone())
				temperature *= 1.05
		temperature *= cooling_rate

		if temperature < stop_temp:
			break

	return sort_unique_layouts(result, result_len)

def optimize(base_layouts: list[Layout], result_path, elites_len=5):
	gen_by_target = 20
	max_generation = elites_len*gen_by_target
	max_population = elites_len*gen_by_target
	elites = [l.clone() for l in base_layouts[:elites_len]]

	# Init population
	unique_population = {l.clone() for l in base_layouts}
	while len(unique_population) < max_population:
		unique_population.add(make_random())
	population = sort_layouts(list(unique_population))

	with ProcessPoolExecutor() as executor:
		prev = elites[0].total
		gen = 1
		while gen <= max_generation:
			target = gen // gen_by_target + 1
			print(f'\r\033[K...{gen}/{max_generation}', end='')
			random_len = int(max_population* max(0.05, 0.3 * (1 - gen/ max_generation)))

			parents_pool = population + elites
			parents = [best_layout(random.sample(parents_pool, 3)) for _ in range(max_population)]
			children = [crossover(random.sample(parents, 2)) for _ in range(max_population - target - random_len)]

			# Make next
			population = []
			progress = min(gen/max_generation, 1.0)
			result = list(executor.map(
				optimize_worker,
				children + elites[:target],
				[progress] * (len(children)+target),
				[elites_len] * (len(children)+target)
			))
			for r in result:
				population.extend(r)
			population = sort_unique_layouts(population, max_population-random_len)
			while len(population) < max_population:
				population.append(make_random())
			population = sort_layouts(population)

			# Elites
			elites.extend([fine_tune_effort(l) for l in population])
			elites = sort_unique_layouts(elites, elites_len)
			target_total = elites[target-1].total if len(elites) >= target else elites[-1].total
			if prev != target_total:
				print(f'\t improved ({prev:,} -> {target_total:,})')
				prev = target_total
				save_result(elites, result_path)
			else:
				gen += 1

	return elites

def optimize_worker(layout: Layout, progress, result_len):
	sa_weight = 0.2 + 0.2 * progress   # 0.2 - 0.4
	effort_weight = 0.2 + 0.1 * progress  # 0.2 - 0.3
	swap_weight = 0.3 - 0.05 * progress  # 0.3 - 0.25
	pass_weight = 1.0 - (sa_weight + effort_weight + swap_weight)

	weights = [max(0.0, sa_weight), max(0.0, effort_weight), max(0.0, swap_weight), max(0.0, pass_weight)]

	total = sum(weights)
	if total <= 0:
		weights = [0.25] * 4
		total = 1.0
	thresholds = []
	acc = 0.0
	for w in weights:
		acc += w / total
		thresholds.append(acc)

	r = random.random()
	if r < thresholds[0]:
		return optimize_sa(layout, result_len)
	elif r < thresholds[1]:
		return optimize_effort(layout, result_len)
	elif r < thresholds[2]:
		return optimize_shuffle(layout, result_len)
	else:
		return [layout]

def print_layout(layout: Layout):
	print(f'{layout.score.effort:,.0f}\t', end='')
	print(f'{layout.score.sfb:,.0f}\t', end='')
	print(f'{layout.score.rolling:,.0f}\t', end='')
	print(f'{layout.score.scissors:,.0f}')
	if layout.left_usage > 0:
		total = layout.left_usage + layout.right_usage
		left_percent = (layout.left_usage / total) * 100
		right_percent = (layout.right_usage / total) * 100
		print(f'{left_percent:.2f} : {right_percent:.2f} \t {layout.total:,}')
		print(f'{layout.source}')
	for row in layout.letters:
		print(row)

def save_result(layouts, result_path):
	file_path = os.path.join(result_path, RESULT_FILENAME)
	with open(file_path, 'w', encoding='utf-8') as f:
		for l in layouts:
			print(l.source, file=f)
			for row in l.letters:
				print(row, file=f)

def load_result(result_path):
	layouts = []
	file_path = os.path.join(result_path, RESULT_FILENAME)
	with open(file_path, 'r', encoding='utf-8') as f:
		lines = [line.rstrip('\n') for line in f if line.rstrip('\n')]
	for i in range(0, len(lines), 4):
		layouts.append(Layout([literal_eval(l) for l in lines[i+1:i+4]], source=lines[i]))
	return layouts

if __name__ == '__main__':
	multiprocessing.set_start_method("fork")
	signal.signal(signal.SIGINT, cleanup)
	try:
		if len(sys.argv) < 2:
			print(f"Usage: {sys.argv[0]} <result_path> [custom_index] [custom_letters]")
			sys.exit(1)

		result_path = sys.argv[1]
		result_path = os.path.expanduser(result_path)
		result_path = os.path.abspath(result_path)
		os.makedirs(result_path, exist_ok=True)

		# Analyze
		file_path = os.path.join(result_path, ANALYZE_RESULT_FILENAME)
		if os.path.exists(file_path):
			load_analysis_result(result_path)
		else:
			analyze_target(result_path)

		init_score_state()
		file_path = os.path.join(result_path, RESULT_FILENAME)
		if os.path.exists(file_path):
			result = load_result(result_path)
		else:
			result = [make_initial_layout()]

		if len(sys.argv) >= 3:
			if len(sys.argv) == 3:
				index = 0
				letters = sys.argv[2]
			else:
				index = int(sys.argv[2])
				letters = sys.argv[3]
			if letters != '':
				result = optimize_shuffle(result[index], len(letters), len(letters), letters)
		else:
			# Optimize
			print(f'[Optimize]')
			result = optimize(result, result_path)
			print(f'\r\033[K...Done')

		for i, l in enumerate(result, 1):
			print(f'[{i}]')
			print_layout(l)

	except KeyboardInterrupt:
		cleanup(None, None)

	cleanup(None,None)
