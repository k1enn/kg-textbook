"""data/md/<doc>/*.md -> LightRAG working dir, 1 bài = 1 doc. Chạy lại = resume, bài xong không gọi lại LLM."""
import argparse, asyncio, json, logging, pathlib, re, unicodedata
import yaml
from lightrag import LightRAG
from lightrag.base import DocStatus
from lightrag.constants import GRAPH_FIELD_SEP
from lightrag.llm.ollama import ollama_embed, ollama_model_complete
from lightrag.utils import normalize_entity_name
from lightrag.utils_graph import adelete_by_entity


def build(kg, llm):
    return LightRAG(
        working_dir=kg,
        llm_model_func=ollama_model_complete,
        llm_model_name=llm,
        llm_model_kwargs={"timeout": 600, "options": {
            "num_ctx": 12288, "num_predict": 6000, "temperature": 0.2, "top_p": 0.8, "top_k": 20}},
        llm_model_max_async=3,
        default_llm_timeout=600,  # worker cắt ở 2x giá trị này, mặc định 240 -> 480s
        max_parallel_insert=1,
        chunk_token_size=700, chunk_overlap_token_size=80,
        entity_extract_max_gleaning=1,
        entity_extraction_use_json=True,
        entity_extract_max_records=25, entity_extract_max_entities=12,
        force_llm_summary_on_merge=20,
        addon_params={"language": "Vietnamese", "entity_type_prompt_file": "hscc_vi.yml"},
        embedding_func=ollama_embed,  # bge-m3:latest, 1024 chiều
    )


GUIDE = yaml.safe_load(open("prompts/entity_type/hscc_vi.yml", encoding="utf-8"))["entity_types_guidance"]
TYPES = set(re.findall(r"^- `(\w+)`:", GUIDE, re.M)) | {"khac"}
UNIT = re.compile(r"^[\d\s,.<>≥≤\-–/%]+(giờ|phút|giây|ngày|ml|lít|l|mmhg|tuổi|điểm|%|kg|mg|g|cm|mm)?$", re.I)  # "1 giờ", "95%"
OBJ = re.compile(r"^\d+(\.\d+)+\.?\s|^\d+\.\s")  # "1. Trình bày", "3.6. Đụng dập"; không bắt "5 bước ABCDE"


def squash(s):
    return "".join(normalize_entity_name(unicodedata.normalize("NFC", s)).split()).casefold()  # bỏ hết khoảng trắng: "PaO2/FiO2< 100" = "PaO2/FiO2 < 100"


def ascii_(s):  # NFD không tách "đ"; LLM hay bỏ gạch dưới
    return "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c)).replace("đ", "d").replace("_", "")


def bad_name(name, ntype):
    return (len(squash(name)) < 2 or len(name) > 60 or len(name.split()) > 8
            or OBJ.match(name) or UNIT.match(name) or ntype.lower() == "unknown")


def fix_type(t):
    t = t.lower()
    if t in TYPES:
        return t
    return next((x for x in TYPES if ascii_(t) == ascii_(x)), "khac")


async def prune(rag, kg):
    """Hậu kỳ 4 bước, chỉ dùng API public, idempotent: xoá rác -> ép type -> gộp hoa thường -> xoá bậc 0.
    Thay kg_extraction_validator (mới có ở LightRAG 1.5.8); lên 1.5.8 thì chuyển sang hook đó."""
    g = rag.chunk_entity_relation_graph

    async def drop(name):  # bản public bỏ sót entity_chunks/relation_chunks, để lại chunk id cũ cho lần merge sau
        await adelete_by_entity(g, rag.entities_vdb, rag.relationships_vdb, name, rag.entity_chunks, rag.relation_chunks)

    nodes = await g.get_all_nodes()
    src = {n["id"]: [c for c in n.get("source_id", "").split(GRAPH_FIELD_SEP) if c] for n in nodes}
    ids = sorted({c for cs in src.values() for c in cs})
    text = {i: squash(c["content"]) for i, c in zip(ids, await rag.text_chunks.get_by_ids(ids)) if c}
    bad = [n["id"] for n in nodes if bad_name(n["id"], n.get("entity_type", ""))
           or not any(squash(n["id"]) in text.get(c, "") for c in src[n["id"]])]
    for name in bad:
        await drop(name)
    logging.info("prune 1 xoá rác: %d/%d, vd %s", len(bad), len(nodes), sorted(bad)[:20])

    keep = [n for n in nodes if n["id"] not in set(bad)]
    retyped = 0
    for n in keep:
        new = fix_type(n.get("entity_type", ""))
        if new != n.get("entity_type", ""):
            await rag.aedit_entity(n["id"], {"entity_type": new}, allow_rename=False)
            retyped += 1
    logging.info("prune 2 ép type: %d", retyped)

    groups = {}
    for n in keep:
        groups.setdefault(squash(n["id"]), []).append(n["id"])
    merged = []
    for grp in groups.values():
        if len(grp) < 2:
            continue
        target = min(grp, key=lambda x: (x != x.lower(), x))
        srcs = [x for x in grp if x != target]
        await rag.amerge_entities(srcs, target)
        merged += [f"{target} <- {x}" for x in srcs]
    logging.info("prune 3 gộp: %d, vd %s", len(merged), merged[:20])

    linked = {x for e in await g.get_all_edges() for x in (e["source"], e["target"])}
    alone = [n["id"] for n in await g.get_all_nodes() if n["id"] not in linked]
    for name in alone:
        await drop(name)
    logging.info("prune 4 bậc 0: %d, vd %s", len(alone), sorted(alone)[:20])

    log = pathlib.Path(kg, "pruned.json")
    old = json.loads(log.read_text(encoding="utf-8")) if log.exists() else []
    log.write_text(json.dumps(sorted({*old, *bad, *merged, *alone}), ensure_ascii=False, indent=0), encoding="utf-8")


async def main(a):
    files = sorted(p for p in pathlib.Path(a.md).glob("*.md") if not p.name.startswith("00-"))
    if a.only:
        files = [p for p in files if p.name[:2] in a.only.split(",")]
    rag = build(a.kg, a.llm)
    await rag.initialize_storages()
    try:
        for p in files:  # tuần tự; song song ở mức chunk (llm_model_max_async)
            st = await rag.doc_status.get_by_id(p.stem)
            if st and st.get("status") == DocStatus.FAILED:  # 1.5.7 không tự retry failed; chunk đã xong ăn LLM cache
                r = await rag.adelete_by_doc_id(p.stem)
                if r.status != "success":  # nạp tiếp sẽ ghi dòng dup-* mỗi lần chạy
                    logging.warning("bỏ qua %s: xoá doc failed lỗi %s %s", p.name, r.status, r.message)
                    continue
                st = None
            if not st:  # ainsert id đã có sẽ ghi thêm dòng dup-* FAILED
                await rag.ainsert(p.read_text(encoding="utf-8"), ids=p.stem,
                                  file_paths=f"{pathlib.Path(a.md).name}/{p.name}")
                logging.info("done %s", p.name)
        await rag.apipeline_process_enqueue_documents()  # resume bài dở (pending/processing)
        await prune(rag, a.kg)
    finally:
        await rag.finalize_storages()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", required=True)
    ap.add_argument("--kg", required=True)
    ap.add_argument("--only", help="vd 01,02,03")
    ap.add_argument("--llm", default="qwen3:4b-instruct-2507-q4_K_M")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    asyncio.run(main(ap.parse_args()))
