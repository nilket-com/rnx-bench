"""rnx 0160: the independent search reference for demos/notebooks/06_candle_search.

	probes/candle-search-0160/.venv/bin/python probes/candle-search-0160/reference.py OUT.json

sentence-transformers on PyTorch CPU (requirements.txt here, pinned) loads the pinned local
all-MiniLM-L6-v2 files that demos/candle/fetch-model.sh fetched, embeds every article's `text`
column and every question exactly as written, and ranks all articles for each question by
cosine similarity computed in float64 from the embeddings (normalize_embeddings=False, as
record 0131's reference). Ties order by article id ascending.

Every input is pinned: the CSV bytes and the six model files by SHA-256, recorded in the
output; the checker refuses a reference whose provenance doesn't match its own inputs. The
reference validates itself before writing: unique ids, complete rankings, finite scores, every
text within the model's 256-token limit (no silent truncation), and a stable shown boundary
(for every question, ranks 1/2, 2/3 and 3/4 differ by more than 1e-4). This is an authored
showcase corpus, not a held-out relevance benchmark."""
import csv, hashlib, json, math, pathlib, sys
import sentence_transformers, torch, transformers

RNX = pathlib.Path(__file__).resolve().parents[3] / "rnx"
DATA = RNX / "demos/data"
MODEL = RNX / "demos/models/all-MiniLM-L6-v2"
REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
MODEL_FILES = {
	"config.json": "953f9c0d463486b10a6871cc2fd59f223b2c70184f49815e7efbcab5d8908b41",
	"tokenizer.json": "be50c3628f2bf5bb5e3a7f17b1f74611b2561a3a27eeab05e5aa30f411572037",
	"model.safetensors": "53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db",
	"modules.json": "84e40c8e006c9b1d6c122e02cba9b02458120b5fb0c87b746c41e0207cf642cf",
	"1_Pooling/config.json": "4be450dde3b0273bb9787637cfbd28fe04a7ba6ab9d36ac48e92b11e350ffc23",
	"sentence_bert_config.json": "fc1993fde0a95c24ec6c022539d41cf6e2f7c9721e5415d6fb6897472a9cd4b7",
}
BATCH = 32
GAP = 1e-4
SHOWN = 3


def sha256(path):
	return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path, header):
	with open(path, newline="") as f:
		r = csv.reader(f)
		assert next(r) == header, path
		return list(r)


def main(out):
	for name, want in MODEL_FILES.items():
		got = sha256(MODEL / name)
		assert got == want, f"{name}: {got} != {want}; run sh demos/candle/fetch-model.sh"
	articles = rows(DATA / "articles.csv", ["id", "title", "text"])
	questions = rows(DATA / "questions.csv", ["id", "question"])
	article_ids = [int(a[0]) for a in articles]
	question_ids = [int(q[0]) for q in questions]
	assert article_ids == list(range(len(articles))) and question_ids == list(range(len(questions)))
	model = sentence_transformers.SentenceTransformer(str(MODEL), device="cpu")
	assert model.max_seq_length == 256, model.max_seq_length
	texts = [a[2] for a in articles] + [q[1] for q in questions]
	# no silent truncation: every text, with its special tokens, fits the limit
	lengths = [len(model.tokenizer(t)["input_ids"]) for t in texts]
	assert max(lengths) <= model.max_seq_length, max(lengths)
	emb = model.encode(texts, batch_size=BATCH, convert_to_numpy=True, normalize_embeddings=False).astype("float64")
	docs, qs = emb[:len(articles)], emb[len(articles):]

	def cosine(a, b):
		return float((a @ b) / math.sqrt((a @ a) * (b @ b)))
	rankings = []
	for qi, q in enumerate(qs):
		scored = [(cosine(d, q), ai) for ai, d in enumerate(docs)]
		assert all(math.isfinite(s) for s, _ in scored)
		# sort the numbers themselves, ties by article id (never by their text: the 0151 bug)
		scored.sort(key=lambda p: (-p[0], p[1]))
		ranked = [{"article": ai, "score": s} for s, ai in scored]
		assert sorted(r["article"] for r in ranked) == article_ids
		gaps = [ranked[k]["score"] - ranked[k + 1]["score"] for k in range(SHOWN)]
		assert min(gaps) > GAP, (qi, gaps)
		rankings.append({"question": qi, "ranking": ranked, "shown_gaps": gaps})
	result = {
		"record": "0160",
		"note": "an authored showcase corpus, not a held-out relevance benchmark",
		"inputs": {"articles.csv": sha256(DATA / "articles.csv"), "questions.csv": sha256(DATA / "questions.csv")},
		"model": {"name": "sentence-transformers/all-MiniLM-L6-v2", "revision": REVISION, "files": MODEL_FILES},
		"method": {"embedded_text": "articles: the text column; questions: the question column, exactly as written",
				   "pooling": "the model's own modules.json (mean pooling)", "normalize_embeddings": False,
				   "similarity": "cosine in float64 from the float32 embeddings", "max_seq_length": 256,
				   "max_tokens_seen": max(lengths), "batch_size": BATCH, "ties": "article id ascending",
				   "shown": SHOWN, "stability_gap": GAP},
		"versions": {"torch": torch.__version__, "sentence_transformers": sentence_transformers.__version__,
					 "transformers": transformers.__version__, "python": sys.version.split()[0],
					 "threads": torch.get_num_threads()},
		"rankings": rankings,
	}
	text = json.dumps(result, indent="\t") + "\n"
	pathlib.Path(out).write_text(text)
	for r in rankings:
		top = r["ranking"][:SHOWN]
		print(r["question"], [(t["article"], round(t["score"], 4)) for t in top], "min gap", round(min(r["shown_gaps"]), 4))


if __name__ == "__main__":
	main(sys.argv[1])
