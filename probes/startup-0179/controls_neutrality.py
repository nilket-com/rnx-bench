"""rnx 0179 untimed fail-closed controls for neutrality.py (review R1/R2, chatd seq 1345). No build, no subject run:
each control copies the retained neutrality binary and/or the retained 0178 reference, changes bytes, and requires
the comparison to refuse it for the stated reason. The unmodified pair must be accepted.

	python3 controls_neutrality.py NEW_BINARY OUT_JSON
"""
import json, pathlib, struct, sys, tempfile
import neutrality
from build import HISTORICAL_BASE, REFERENCE_BINARY
from common import SOURCES, sha


def main(new, out):
	new = pathlib.Path(new)
	a, b = new.read_bytes(), REFERENCE_BINARY.read_bytes()
	loads, sections = neutrality.elf(a)
	results = {}
	with tempfile.TemporaryDirectory() as d:
		d = pathlib.Path(d)

		def run(name, expect, new_bytes=None, ref_bytes=None):
			"""expect None = must be accepted; otherwise a substring that some reported problem must contain."""
			x, y = d / "new", d / "ref"
			x.write_bytes(a if new_bytes is None else new_bytes)
			y.write_bytes(b if ref_bytes is None else ref_bytes)
			ok, report = neutrality.compare(x, y, HISTORICAL_BASE, SOURCES["base"])
			passed = ok if expect is None else (not ok and any(expect in p for p in report["problems"]))
			results[name] = {"pass": passed, "accepted": ok, "expected_problem": expect, "problems": report["problems"]}
			print(name, "PASS" if passed else "FAIL", report["problems"][:2], flush=True)
			return report

		def flip(data, offset, mask=1):
			out = bytearray(data)
			out[offset] ^= mask
			return bytes(out)

		real = run("unmodified-pair-accepted", None)
		location = real["moved_locations"][0]
		loc, pointer = location["file_offset"], location["file_pointer"]
		ro = sections[".data.rel.ro"]
		shoff = struct.unpack_from("<Q", a, 40)[0]
		shnum = struct.unpack_from("<H", a, 60)[0]
		# R1: bytes outside every section, header fields, padding.
		run("reference-equals-itself-with-elf-header-pad-flipped", "outside the validated allowlist", new_bytes=flip(b, 9), ref_bytes=b)
		run("elf-header-pad-byte", "outside the validated allowlist", new_bytes=flip(a, 9))
		run("program-header-flags", "outside the validated allowlist", new_bytes=flip(a, struct.unpack_from("<Q", a, 32)[0] + 4))
		index = list(sections).index(".text")
		run("section-header-flags-of-text", "outside the validated allowlist", new_bytes=flip(a, shoff + index * 64 + 8))
		run("section-header-alignment", "outside the validated allowlist", new_bytes=flip(a, shoff + index * 64 + 48, 8))
		covered = bytearray(len(a))
		for s in sections.values():
			if s["type"] != 8:
				covered[s["offset"]:s["offset"] + s["size"]] = b"\1" * s["size"]
		covered[0:64] = b"\1" * 64
		ph = struct.unpack_from("<Q", a, 32)[0]
		phn = struct.unpack_from("<H", a, 56)[0]
		covered[ph:ph + phn * 56] = b"\1" * (phn * 56)
		covered[shoff:shoff + shnum * 64] = b"\1" * (shnum * 64)
		gap = covered.find(b"\0")
		assert gap >= 0, "no inter-section padding byte in this binary"
		run("inter-section-padding-byte", "outside the validated allowlist", new_bytes=flip(a, gap))
		results["inter-section-padding-byte"]["file_offset"] = gap
		run("truncated-file", "file sizes differ", new_bytes=a[:-1])
		# Section contents that must stay identical.
		for name in (".text", ".rodata", ".rela.dyn", ".symtab", ".eh_frame"):
			run(f"byte-in-{name}", "outside the validated allowlist", new_bytes=flip(a, sections[name]["offset"] + sections[name]["size"] // 2))
		# Build-id: descriptor only, framing validated.
		note = sections[".note.gnu.build-id"]["offset"]
		run("build-id-descriptor-byte-accepted", None, new_bytes=flip(a, note + 20))
		run("build-id-note-type", "build-id note framing", new_bytes=flip(a, note + 8))
		run("build-id-note-name", "build-id note framing", new_bytes=flip(a, note + 12))
		run("build-id-note-descsz", "build-id note framing", new_bytes=flip(a, note + 4))
		# .strtab: suffix digits only, same count and order.
		st = sections[".strtab"]
		table = a[st["offset"]:st["offset"] + st["size"]]
		suffix = table.find(b".llvm.")
		run("symbol-suffix-digit-accepted", None, new_bytes=flip(a, st["offset"] + suffix + 6, 1))
		run("symbol-name-outside-suffix", "beyond a .llvm.<digits> suffix", new_bytes=flip(a, st["offset"] + suffix - 3))
		run("symbol-without-suffix", "beyond a .llvm.<digits> suffix", new_bytes=flip(a, st["offset"] + table.find(b"main\0")))
		run("symbol-suffix-made-non-digit", "beyond a .llvm.<digits> suffix", new_bytes=flip(a, st["offset"] + suffix + 6, 0x40))
		terminator = st["offset"] + table.find(b"\0", suffix)
		run("symbol-count-changed", ".strtab symbol count differs", new_bytes=a[:terminator] + b"x" + a[terminator + 1:])
		# R2: the panic location.
		run("line-with-wrong-shift", "source diff gives", new_bytes=flip(a, loc + 16, 2))
		run("column-changed", "differs outside its line field", new_bytes=flip(a, loc + 20))
		# A changed length or pointer word is read as the line field of a (non-existent) location 8 or 16 bytes earlier and
		# refused there; whichever reason is reported first, the byte is outside the allowlist.
		run("length-word-changed", "outside the validated allowlist", new_bytes=flip(a, loc + 8))
		run("pointer-word-changed", "outside the validated allowlist", new_bytes=flip(a, loc))
		other = b"/home/me/work/rune-w-0173/crates/rune/src/compile/contexT.rs"
		assert len(other) == len(location["file"]) and other != location["file"].encode()
		path_at = neutrality.file_offset(loads, pointer, len(other))
		assert a[path_at:path_at + len(other)] == location["file"].encode() == b[path_at:path_at + len(other)]
		swap = lambda data: data[:path_at] + other + data[path_at + len(other):]
		run("same-length-other-path-in-both-files", "referenced file is", new_bytes=swap(a), ref_bytes=swap(b))
		run("other-path-in-reference-only", "outside the validated allowlist", ref_bytes=swap(b))
		huge = lambda data: data[:loc + 8] + struct.pack("<Q", 1 << 40) + data[loc + 16:]
		run("length-out-of-range-in-both-files", "is not the context.rs path length", new_bytes=huge(a), ref_bytes=huge(b))
		rela = sections[".rela.dyn"]
		entry = next(i for i in range(rela["size"] // 24) if struct.unpack_from("<Q", a, rela["offset"] + i * 24)[0] == location["address"])
		unmap = lambda data: data[:rela["offset"] + entry * 24 + 16] + struct.pack("<q", 1 << 50) + data[rela["offset"] + entry * 24 + 24:]
		run("pointer-relocated-out-of-range-in-both-files", "is not file-backed", new_bytes=unmap(a), ref_bytes=unmap(b))
		norel = lambda data: data[:rela["offset"] + entry * 24 + 8] + struct.pack("<Q", 6) + data[rela["offset"] + entry * 24 + 16:]
		run("pointer-not-a-relative-relocation-in-both-files", "RELATIVE relocation", new_bytes=norel(a), ref_bytes=norel(b))
		first = ro["offset"] + 16
		run("line-like-word-at-section-start", "truncated location", new_bytes=flip(a, ro["offset"]))
		run("unrelated-word-in-data-rel-ro", "outside the validated allowlist", new_bytes=flip(a, first + 4096))
	summary = {"new": {"path": str(new), "sha256": sha(new)}, "reference": {"path": str(REFERENCE_BINARY), "sha256": sha(REFERENCE_BINARY)},
		"controls": results}
	pathlib.Path(out).write_text(json.dumps(summary, indent=1) + "\n")
	failed = [k for k, v in results.items() if not v["pass"]]
	print("neutrality controls:", len(results) - len(failed), "/", len(results), "pass", flush=True)
	if failed:
		raise SystemExit(f"FAILED: {failed}")


if __name__ == "__main__":
	main(sys.argv[1], sys.argv[2])
