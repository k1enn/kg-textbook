"""So 2 LightRAG working dir cùng 1 sách: cấu trúc, chất lượng output LLM thô, độ phủ chunk, recall thuật ngữ vàng, truy hồi KG.
python scripts/bench.py kg/old/<doc> kg/new/<doc> [--md data/md/<doc>] [--only 01,02,03] [--retrieval]  (retrieval cần ollama bge-m3, không gọi LLM)"""
import argparse, asyncio, collections, json, pathlib, re, sys, unicodedata
import networkx as nx
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from index import build, squash

GOLD = ("triage|ABCD|primary survey|secondary survey|canuyn miệng hầu|mặt nạ thanh quản|nội khí quản|Heimlich|mở màng nhẫn giáp|bóp bóng|"
        "suy hô hấp cấp|khí máu động mạch|thở oxy|COPD|ARDS|PaO2|SpO2|sốc giảm thể tích|sốc tim|sốc nhiễm khuẩn|sốc phản vệ|sốc tắc nghẽn|lactat|"
        "noradrenalin|dopamin|dobutamin|adrenalin|CVP|ngừng tuần hoàn|ép tim|thổi ngạt|sốc điện|amiodaron|rung thất|vô tâm thu|hạ thân nhiệt|"
        "nhồi máu cơ tim|ST chênh|troponin|aspirin|clopidogrel|heparin|alteplase|tenecteplase|can thiệp mạch vành|chấn thương sọ não|Glasgow|"
        "tăng áp lực nội sọ|manitol|chấn thương cột sống|nẹp cổ|sốc tủy|methylprednisolon|tràn khí màng phổi|tràn máu màng phổi|mảng sườn di động|"
        "ép tim cấp|dẫn lưu màng phổi|đụng dập phổi|chấn thương bụng|FAST|chọc rửa ổ bụng|sốc chấn thương|mất máu|truyền máu|dịch tinh thể|gãy xương hở|"
        "hội chứng chèn ép khoang|garo|chi thể đứt rời|bất động|bỏng|ngộ độc cấp|rửa dạ dày|than hoạt|naloxon|atropin|PAM|thuốc giải độc|"
        "vận chuyển bệnh nhân|đặt nội khí quản|thông khí nhân tạo|hội chứng động mạch vành cấp|hạ đường máu|suy đa tạng|toan chuyển hóa|tụt huyết áp|thiểu niệu").split("|")
# (câu hỏi, từ khoá đưa thẳng vào QueryParam để khỏi gọi LLM, thuật ngữ đáp án phải xuất hiện trong entity/relation trả về)
QA = [("Thuốc trong cấp cứu ngừng tuần hoàn nâng cao?", ["ngừng tuần hoàn"], ["adrenalin", "amiodaron"]),
      ("Phân loại sốc?", ["sốc"], ["sốc giảm thể tích", "sốc tim", "sốc nhiễm khuẩn", "sốc phản vệ"]),
      ("Điều trị nhồi máu cơ tim ST chênh?", ["nhồi máu cơ tim"], ["aspirin", "heparin", "alteplase", "can thiệp mạch vành"]),
      ("Kỹ thuật kiểm soát đường thở?", ["đường thở"], ["canuyn miệng hầu", "mặt nạ thanh quản", "nội khí quản", "mở màng nhẫn giáp"]),
      ("Xử trí ngộ độc cấp?", ["ngộ độc"], ["rửa dạ dày", "than hoạt", "naloxon", "atropin"]),
      ("Tổn thương trong chấn thương ngực?", ["chấn thương ngực"], ["tràn khí màng phổi", "tràn máu màng phổi", "mảng sườn di động", "dẫn lưu màng phổi"]),
      ("Đánh giá chấn thương sọ não?", ["chấn thương sọ não"], ["glasgow", "tăng áp lực nội sọ", "manitol"]),
      ("Xét nghiệm suy hô hấp cấp?", ["suy hô hấp cấp"], ["khí máu động mạch", "pao2", "spo2"]),
      ("Xử trí chấn thương cột sống?", ["chấn thương cột sống"], ["nẹp cổ", "sốc tủy", "methylprednisolon"]),
      ("Chẩn đoán chấn thương bụng?", ["chấn thương bụng"], ["fast", "chọc rửa ổ bụng"])]
pct = lambda a, b: f"{100 * a / b:.0f}%" if b else "-"


def load(kg, f):
    p = pathlib.Path(kg, f)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def report(kg, gold):
    g = nx.read_graphml(pathlib.Path(kg, "graph_chunk_entity_relation.graphml"))
    n = g.number_of_nodes()
    cc = max((len(c) for c in nx.connected_components(g)), default=0)
    r = {"nodes": n, "edges": g.number_of_edges(), "avg deg": f"{2 * g.number_of_edges() / n:.2f}" if n else "-",
         "largest comp": pct(cc, n), "isolated": pct(sum(1 for _ in nx.isolates(g)), n)}
    ents, rels, undeclared, snake = 0, 0, 0, 0
    for v in load(kg, "kv_store_llm_response_cache.json").values():
        if v.get("cache_type") != "extract":
            continue
        s = v.get("return") or ""
        try:
            j = json.loads(s[s.find("{"):s.rfind("}") + 1])
        except ValueError:
            continue
        E = [e for e in j.get("entities", []) if isinstance(e, dict)]
        R = [x for x in j.get("relationships", []) if isinstance(x, dict)]
        names = {squash(e.get("name", "")) for e in E}
        ents += len(E); rels += len(R)
        snake += sum("_" in e.get("name", "") for e in E)
        undeclared += sum(squash(x.get(k, "")) not in names for x in R for k in ("source", "target"))
    r |= {"raw ents": ents, "raw rels": rels, "raw snake_case": pct(snake, ents), "raw rel endpoint undeclared": pct(undeclared, 2 * rels),
          "node survival": pct(n, ents)}
    cov = collections.Counter(c for _, d in g.nodes(data=True) for c in str(d.get("source_id", "")).split("<SEP>") if c)
    chunks = list(load(kg, "kv_store_text_chunks.json"))
    r["chunks w/ 0 nodes"] = f"{sum(cov[c] == 0 for c in chunks)}/{len(chunks)}"
    r["median nodes/chunk"] = sorted(cov[c] for c in chunks)[len(chunks) // 2] if chunks else 0
    keys = {squash(x): x for x in g.nodes}
    hit = {t for t in gold if squash(t) in keys}
    sub = {t for t in gold if t not in hit and any(squash(t) in k for k in keys)}
    r["gold exact"] = f"{len(hit)}/{len(gold)}"; r["gold substring"] = len(sub)
    r["gold deg"] = sum(g.degree(keys[squash(t)]) for t in hit)
    return r, hit | sub


async def retrieval(kg):
    from lightrag import QueryParam
    rag = build(kg, "unused")
    await rag.initialize_storages()
    out = []
    try:
        for q, kw, ans in QA:
            res = await rag.aquery(q, QueryParam(mode="hybrid", only_need_context=True, hl_keywords=kw, ll_keywords=kw, enable_rerank=False))
            ctx = res if isinstance(res, str) else getattr(res, "content", "") or ""
            kgpart = re.split(r"Document Chunks", ctx, flags=re.I)[0]  # bỏ phần chunk (vector, giống nhau 2 bên)
            ents, rels = kgpart.count('{"entity"'), kgpart.count('{"entity1"') or kgpart.count('{"relationship"') or kgpart.count('{"source"')
            blob = squash(kgpart)
            got = [a for a in ans if squash(a) in blob]
            out.append((q, ents, rels, got, ans))
    finally:
        await rag.finalize_storages()
    return out


def main(a):
    files = sorted(p for p in pathlib.Path(a.md).glob("*.md") if not p.name.startswith("00-"))
    if a.only:
        files = [p for p in files if p.name[:2] in a.only.split(",")]
    md = squash("".join(p.read_text(encoding="utf-8") for p in files))
    gold = [t for t in GOLD if squash(t) in md]
    (ra, ha), (rb, hb) = report(a.a, gold), report(a.b, gold)
    print(f"{'metric':30} {'A: ' + a.a:36} {'B: ' + a.b}")
    for k in ra:
        print(f"{k:30} {str(ra[k]):36} {rb[k]}")
    print(f"\ngold lost A->B ({len(ha - hb)}): {sorted(ha - hb)}\ngold gained A->B ({len(hb - ha)}): {sorted(hb - ha)}")
    if a.retrieval:
        A, B = asyncio.run(retrieval(a.a)), asyncio.run(retrieval(a.b))
        ta = tb = tot = 0
        print(f"\n{'câu hỏi':42} {'A ent/rel hit':18} B ent/rel hit")
        for (q, ea, la, ga, ans), (_, eb, lb, gb, _) in zip(A, B):
            ta += len(ga); tb += len(gb); tot += len(ans)
            print(f"{q:42} {f'{ea}/{la} {len(ga)}/{len(ans)}':18} {eb}/{lb} {len(gb)}/{len(ans)}  thiếu B: {[x for x in ans if x not in gb]}")
        print(f"{'TỔNG đáp án trong KG context':42} {pct(ta, tot):18} {pct(tb, tot)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("a"); ap.add_argument("b")
    ap.add_argument("--md", default="data/md/byt_capcuu_coban_2014")
    ap.add_argument("--only", help="vd 01,02,03: gold chỉ lấy từ bài pilot")
    ap.add_argument("--retrieval", action="store_true")
    main(ap.parse_args())
