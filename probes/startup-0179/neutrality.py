"""rnx 0179 neutrality comparison: is a build of the tests-first base, under the UNCHANGED 0178 harness, the same program
as 0178's retained P0 base primary except for diagnostics that the base's test-only source lines must move?

	python3 neutrality.py NEW_BINARY REFERENCE_BINARY      # prints the report; exit 1 unless accepted

The claim it supports is narrow: machine code and all other data are identical; the enumerated panic line fields
differ (so panic DIAGNOSTICS differ). It is not whole-binary identity and not "all observable behaviour unchanged".

Method (fail closed; review R1/R2 of the first form, chatd seq 1345): the two files must have the same length. EVERY
differing file offset, wherever it lies (ELF header, program headers, section headers, padding, any section), must fall
inside an allowlist built only from validated structures:

1. .note.gnu.build-id: the note framing (namesz 4, type 3, name "GNU\\0", descriptor filling the section) must be
	equal in both files; only the descriptor bytes are allowed to differ.
2. .strtab: both tables must split into the same number of names in the same order; a differing pair must have equal
	length and be equal up to a trailing `.llvm.<digits>` ThinLTO suffix; only those suffix digits are allowed.
3. .data.rel.ro: a differing 4-byte word must be the `line` field of a 24-byte core::panic::Location (file pointer,
	file length, line, column) whose other 20 bytes are equal in both files, whose file pointer is filled by an
	R_X86_64_RELATIVE relocation that is the same in both files, and whose referenced bytes, resolved through the
	PT_LOAD mapping in BOTH files, are exactly the fork's context.rs path. The new line must equal the old line plus
	the number of lines the base adds above it, from `git diff -U0 OLD_REV..NEW_REV -- context.rs`.

Anything else is a problem and the comparison is not accepted. Every accepted difference is enumerated.
"""
import json, pathlib, re, struct, subprocess, sys
from common import FORK, EB

CONTEXT_RS = "crates/rune/src/compile/context.rs"
R_X86_64_RELATIVE = 8


class Malformed(Exception):
	pass


def elf(data):
	"""Minimal ELF64 little-endian reader: program headers, named section headers. Raises Malformed on anything odd."""
	if data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 1:
		raise Malformed("not ELF64 little-endian")
	(phoff, shoff), (phentsize, phnum, shentsize, shnum, shstrndx) = struct.unpack_from("<QQ", data, 32), struct.unpack_from("<HHHHH", data, 54)
	if phentsize != 56 or shentsize != 64 or shstrndx >= shnum:
		raise Malformed("unexpected header entry sizes")
	if phoff + phnum * 56 > len(data) or shoff + shnum * 64 > len(data):
		raise Malformed("header tables out of range")
	loads = []
	for i in range(phnum):
		p_type, _, p_offset, p_vaddr, _, p_filesz, _, _ = struct.unpack_from("<IIQQQQQQ", data, phoff + i * 56)
		if p_type == 1:
			loads.append((p_vaddr, p_offset, p_filesz))
	raw = [struct.unpack_from("<IIQQQQIIQQ", data, shoff + i * 64) for i in range(shnum)]
	names_off, names_size = raw[shstrndx][4], raw[shstrndx][5]
	if names_off + names_size > len(data):
		raise Malformed("section name table out of range")
	sections = {}
	for name_index, sh_type, _, addr, offset, size, *_ in raw:
		end = data.find(b"\0", names_off + name_index, names_off + names_size)
		if end < 0:
			raise Malformed("unterminated section name")
		name = data[names_off + name_index:end].decode()
		if sh_type != 8 and offset + size > len(data):  # SHT_NOBITS occupies no file bytes
			raise Malformed(f"section {name} out of range")
		if name in sections:
			raise Malformed(f"duplicate section {name}")
		sections[name] = {"type": sh_type, "addr": addr, "offset": offset, "size": size}
	return loads, sections


def file_offset(loads, vaddr, length):
	"""File offset of [vaddr, vaddr+length) if it lies wholly inside one PT_LOAD's file-backed part, else Malformed."""
	for p_vaddr, p_offset, p_filesz in loads:
		if p_vaddr <= vaddr and vaddr + length <= p_vaddr + p_filesz:
			return p_offset + (vaddr - p_vaddr)
	raise Malformed(f"address {vaddr:#x}+{length} is not file-backed")


def relative_relocations(data, sections):
	"""{r_offset: addend} for every R_X86_64_RELATIVE entry of .rela.dyn."""
	s = sections.get(".rela.dyn")
	if s is None or s["size"] % 24:
		raise Malformed(".rela.dyn missing or misaligned")
	got = {}
	for i in range(s["size"] // 24):
		r_offset, r_info, r_addend = struct.unpack_from("<QQq", data, s["offset"] + i * 24)
		if r_info == R_X86_64_RELATIVE:
			if r_offset in got:
				raise Malformed(f"duplicate relocation at {r_offset:#x}")
			got[r_offset] = r_addend
	return got


def line_shifts(old_rev, new_rev):
	"""[(first old line after the hunk, running lines added minus removed)] for context.rs between the two revisions."""
	diff = subprocess.run(["git", "-C", str(FORK), "diff", "--no-color", "-U0", old_rev, new_rev, "--", CONTEXT_RS], capture_output=True,
		text=True, check=True, env=EB).stdout
	shifts, total = [], 0
	for m in re.finditer(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", diff, re.M):
		old_start, old_n, new_n = int(m.group(1)), int(m.group(2) if m.group(2) is not None else 1), int(m.group(4) if m.group(4) is not None else 1)
		total += new_n - old_n
		shifts.append((old_start + old_n, total))
	if not shifts:
		raise Malformed("no context.rs hunks between the revisions")
	return shifts


def shift_at(shifts, old_line):
	got = 0
	for boundary, total in shifts:
		if old_line >= boundary:
			got = total
	return got


def allow_build_id(a, b, sa, sb, allowed, report):
	s = sa[".note.gnu.build-id"]
	off, size = s["offset"], s["size"]
	for data in (a, b):
		namesz, descsz, kind = struct.unpack_from("<III", data, off)
		if (namesz, kind) != (4, 3) or data[off + 12:off + 16] != b"GNU\0" or 16 + descsz != size or descsz == 0:
			raise Malformed("unexpected GNU build-id note framing")
	allowed.update(range(off + 16, off + size))
	report["build_id"] = {"new": a[off + 16:off + size].hex(), "reference": b[off + 16:off + size].hex()}


def allow_strtab(a, b, sa, sb, allowed, report):
	s = sa[".strtab"]
	off, size = s["offset"], s["size"]
	na, nb = a[off:off + size].split(b"\0"), b[off:off + size].split(b"\0")
	if len(na) != len(nb):
		raise Malformed(".strtab symbol count differs")
	pairs, position = [], off
	for x, y in zip(na, nb):
		if x != y:
			mx, my = re.fullmatch(rb"(.*\.llvm\.)(\d+)", x, re.S), re.fullmatch(rb"(.*\.llvm\.)(\d+)", y, re.S)
			if len(x) != len(y) or not mx or not my or mx.group(1) != my.group(1):
				raise Malformed(f".strtab names differ beyond a .llvm.<digits> suffix: {x[:120]!r} / {y[:120]!r}")
			allowed.update(range(position + len(mx.group(1)), position + len(x)))
			pairs.append([x.decode(), y.decode()])
		position += len(x) + 1
	report["strtab"] = {"symbols": len(na), "suffix_only_differences": len(pairs), "pairs": pairs}


def allow_locations(a, b, la, lb, sa, sb, differing, allowed, report, shifts, path):
	s = sa[".data.rel.ro"]
	off, size = s["offset"], s["size"]
	ra, rb = relative_relocations(a, sa), relative_relocations(b, sb)
	moved = []
	for start in sorted({p - (p - off) % 4 for p in differing if off <= p < off + size}):
		loc = start - 16
		if loc < off or loc + 24 > off + size:
			raise Malformed(f"truncated location at file offset {start}")
		if a[loc:loc + 16] != b[loc:loc + 16] or a[loc + 20:loc + 24] != b[loc + 20:loc + 24]:
			raise Malformed(f"location at {loc} differs outside its line field")
		length, new_line, column = struct.unpack_from("<QII", a, loc + 8)
		old_line = struct.unpack_from("<I", b, loc + 16)[0]
		vaddr = s["addr"] + (loc - off)
		if vaddr not in ra or ra[vaddr] != rb.get(vaddr):
			raise Malformed(f"location at {loc}: file pointer is not the same RELATIVE relocation in both files")
		pointer = ra[vaddr]
		if length != len(path):
			raise Malformed(f"location at {loc}: file length {length} is not the context.rs path length {len(path)}")
		text_a = a[file_offset(la, pointer, length):][:length]
		text_b = b[file_offset(lb, pointer, length):][:length]
		if text_a != path or text_b != path:
			raise Malformed(f"location at {loc}: referenced file is {text_a!r} / {text_b!r}, not {path!r}")
		expected = old_line + shift_at(shifts, old_line)
		if new_line != expected:
			raise Malformed(f"location at {loc}: line {old_line} -> {new_line}, source diff gives {expected}")
		allowed.update(range(start, start + 4))
		moved.append({"file_offset": loc, "address": vaddr, "file_pointer": pointer, "file": text_a.decode(), "old_line": old_line,
			"new_line": new_line, "column": column, "source_shift": expected - old_line})
	report["moved_locations"] = moved


def compare(new, reference, old_rev, new_rev):
	"""(accepted, report). Never raises for a malformed or unexplained input: that is a problem in the report."""
	a, b = pathlib.Path(new).read_bytes(), pathlib.Path(reference).read_bytes()
	report = {"size": [len(a), len(b)], "problems": []}
	if len(a) != len(b):
		report["problems"].append("file sizes differ")
		return False, report
	differing = [i for i in range(len(a)) if a[i] != b[i]]
	report["differing_bytes"] = len(differing)
	allowed, sa = set(), None
	try:
		(la, sa), (lb, sb) = elf(a), elf(b)
		by_section = {}
		for p in differing:
			name = next((n for n, s in sa.items() if s["type"] != 8 and s["offset"] <= p < s["offset"] + s["size"]), "(outside every section)")
			by_section[name] = by_section.get(name, 0) + 1
		report["differing_bytes_by_section"] = by_section
		path = (str(FORK) + "/" + CONTEXT_RS).encode()
		for step in (lambda: allow_build_id(a, b, sa, sb, allowed, report), lambda: allow_strtab(a, b, sa, sb, allowed, report),
				lambda: allow_locations(a, b, la, lb, sa, sb, differing, allowed, report, line_shifts(old_rev, new_rev), path)):
			try:
				step()
			except Malformed as error:
				report["problems"].append(str(error))
	except Malformed as error:
		report["problems"].append(str(error))
	outside = [p for p in differing if p not in allowed]
	if outside:
		report["problems"].append(f"{len(outside)} differing byte(s) outside the validated allowlist, first at file offset {outside[0]}")
	text = sa.get(".text") if sa else None
	report["text_identical"] = bool(text) and a[text["offset"]:text["offset"] + text["size"]] == b[text["offset"]:text["offset"] + text["size"]]
	if not report["text_identical"]:
		report["problems"].append(".text is not identical")
	report["claim"] = ("machine code and all other bytes identical except the enumerated panic line fields, ThinLTO local-symbol suffixes and the "
		"derived build-id; panic diagnostics for the moved locations differ")
	return not report["problems"], report


if __name__ == "__main__":
	from build import HISTORICAL_BASE
	from common import SOURCES
	ok, rep = compare(sys.argv[1], sys.argv[2], HISTORICAL_BASE, SOURCES["base"])
	print(json.dumps(rep, indent=1))
	sys.exit(0 if ok else 1)
