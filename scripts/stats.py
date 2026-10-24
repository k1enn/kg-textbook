"""Chỉ số sức khoẻ của 1 LightRAG working dir. Đọc file, không gọi LLM."""
import collections, json, pathlib, re, sys
import networkx as nx
import yaml

kg = pathlib.Path(sys.argv[1])
guide = yaml.safe_load(open("prompts/entity_type/hscc_vi.yml", encoding="utf-8"))["entity_types_guidance"]
TYPES = set(re.findall(r"^- `(\w+)`:", guide, re.M)) | {"khac", "other"}  # prompt gốc LightRAG bảo dùng `Other`
RELS = tuple(re.findall(r"^  - `(\w+)`:", guide, re.M))
load = lambda f: json.loads((kg / f).read_text(encoding="utf-8")) if (kg / f).exists() else {}

docs = load("kv_store_doc_status.json")
status = collections.Counter(v.get("status") for v in docs.values())
trunc = [k for k, v in docs.items() if (v.get("metadata") or {}).get("llm_truncation")]
chunks = len(load("kv_store_text_chunks.json"))
out = sum(len(v.get("return") or "") for v in load("kv_store_llm_response_cache.json").values()
          if v.get("cache_type") == "extract")
g = nx.read_graphml(kg / "graph_chunk_entity_relation.graphml")
n, e = g.number_of_nodes(), g.number_of_edges()
types = collections.Counter(str(d.get("entity_type", "")).lower() for _, d in g.nodes(data=True))
off = sum(c for t, c in types.items() if t not in TYPES)
rel_ok = sum(any(k.strip() in RELS for k in str(d.get("keywords", "")).split(","))  # merge sort lại keywords
             for *_, d in g.edges(data=True))
pruned = len(load("pruned.json"))
pct = lambda a, b: f"{100 * a / b:.0f}%" if b else "-"

print(f"docs        {dict(status)}  truncation {len(trunc)} {trunc[:5]}")
print(f"chunks      {chunks}   token out/chunk ~{out / 3.45 / chunks:.0f} (>= 400)" if chunks else "chunks      0")
print(f"nodes/edges {n}/{e}   cô lập {pct(sum(1 for _ in nx.isolates(g)), n)} (< 30%)")
print(f"ngoài schema {pct(off, n)} (< 10%)   rel prefix hợp lệ {pct(rel_ok, e)} (>= 60%)   prune drop {pct(pruned, pruned + n)} (< 40%)")
print("types       " + ", ".join(f"{t}:{c}" for t, c in types.most_common()))
