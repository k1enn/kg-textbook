"""data/md/<doc>/*.md -> LightRAG working dir, 1 bài = 1 doc. Chạy lại = resume, bài xong không gọi lại LLM."""
import argparse, asyncio, difflib, json, logging, pathlib, re, unicodedata
import yaml
from lightrag import LightRAG
from lightrag.base import DocStatus
from lightrag.llm.ollama import ollama_embed, ollama_model_complete
from lightrag.utils import normalize_entity_name


CFG = yaml.safe_load(pathlib.Path(__file__).with_suffix(".yml").read_text(encoding="utf-8"))
GUIDE = yaml.safe_load(open("prompts/entity_type/" + CFG["addon_params"]["entity_type_prompt_file"], encoding="utf-8"))["entity_types_guidance"]
TYPES = set(re.findall(r"^- `(\w+)`:", GUIDE, re.M)) | {"khac"}
UNIT = re.compile(r"^[\d\s,.<>≥≤\-–/%]+(giờ|phút|giây|ngày|ml|lít|l|mmhg|tuổi|điểm|%|kg|mg|g|cm|mm)?$", re.I)  # "1 giờ", "95%"
OBJ = re.compile(r"^\d+(\.\d+)+\.?\s|^\d+\.\s")  # "1. Trình bày", "3.6. Đụng dập"; không bắt "5 bước ABCDE"
EDGE = re.compile(r"^[^\w%]+|[^\w%]+$")  # bỏ dấu câu/gạch đầu dòng ở 2 đầu cửa sổ
FENCE = re.compile(r"---Input Text---\n```\n(.*)\n```\n\n---Output---", re.S)  # user prompt của LightRAG 1.5.7


def squash(s):
    return "".join(normalize_entity_name(unicodedata.normalize("NFC", s)).split()).casefold()  # bỏ hết khoảng trắng: "PaO2/FiO2< 100" = "PaO2/FiO2 < 100"


def ascii_(s):  # NFD không tách "đ"; LLM hay bỏ gạch dưới
    return "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c)).replace("đ", "d").replace("_", "")


def bad_name(name):
    return (len(squash(name)) < 2 or len(name) > 60 or len(name.split()) > 8
            or OBJ.match(name) or UNIT.match(name))


def repair(name, chunk):  # "khai_thong_duong_tho" / "cap_cu" -> "khai thông đường thở" / "cấp cứu": cửa sổ n, n+1 từ trong chunk, so bỏ dấu, mờ ≥ 0.9
    words = name.replace("_", " ").split()
    k = ascii_(squash(" ".join(words)))
    toks = chunk.split()
    best, score = None, 0.9
    for n in (len(words), len(words) + 1):
        for i in range(len(toks) - n + 1):
            w = EDGE.sub("", " ".join(toks[i:i + n]))
            r = difflib.SequenceMatcher(None, ascii_(squash(w)), k).ratio()
            if r > score:
                best, score = w, r
    return normalize_entity_name(best.lower()) if best else None


def fix_type(t):
    t = t.lower()
    if t in TYPES:
        return t
    return next((x for x in TYPES if ascii_(t) == ascii_(x)), "khac")


def ground(prompt, res):
    """Sửa output LLM theo nguyên văn chunk TRƯỚC khi LightRAG merge (thay prune hậu kỳ: xoá sau merge làm đứt cạnh, đầu kia bậc 0).
    Tên: viết thường, có trong chunk (khớp thẳng hoặc sửa snake_case/thiếu dấu), không thì bỏ. Type ép về mã. Endpoint quan hệ sửa cùng cách, có thì thêm entity.
    LightRAG 1.5.8 có kg_extraction_validator làm đúng việc này; lên 1.5.8 thì chuyển."""
    m = FENCE.search(prompt)
    try:
        j = json.loads(res[res.find("{"):res.rfind("}") + 1])
    except ValueError:
        return res
    if not m or not isinstance(j, dict):
        return res
    chunk = m.group(1)
    text = squash(chunk)

    def fix(name):
        name = normalize_entity_name(str(name)).lower()
        if bad_name(name):
            return None
        if squash(name) in text:
            return name
        new = repair(name, chunk)
        return None if new is None or bad_name(new) else new

    ents, dropped = {}, []
    for e in j.get("entities", []):
        if not isinstance(e, dict):
            continue
        n = fix(e.get("name", ""))
        if n is None:
            dropped.append(e.get("name"))
        elif n not in ents:
            ents[n] = {**e, "name": n, "type": fix_type(str(e.get("type", "")))}
    rels = []
    for r in j.get("relationships", []):
        if not isinstance(r, dict):
            continue
        s, t = fix(r.get("source", "")), fix(r.get("target", ""))
        if not s or not t or s == t:
            continue
        for n in (s, t):
            ents.setdefault(n, {"name": n, "type": "khac", "description": r.get("description", "")})
        rels.append({**r, "source": s, "target": t})
    logging.info("ground: giữ %d ent %d rel, bỏ %d vd %s", len(ents), len(rels), len(dropped), dropped[:5])
    return json.dumps({"entities": list(ents.values()), "relationships": rels}, ensure_ascii=False)


async def llm(prompt, system_prompt=None, history_messages=[], **kw):
    res = await ollama_model_complete(prompt, system_prompt=system_prompt, history_messages=history_messages, **kw)
    return ground(prompt, res) if "---Input Text---" in prompt else res  # cache LightRAG lưu bản đã sửa


def build(kg, llm_name):
    return LightRAG(
        working_dir=kg,
        llm_model_func=llm,
        llm_model_name=llm_name,
        embedding_func=ollama_embed,  # bge-m3:latest, 1024 chiều
        **CFG,
    )


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
