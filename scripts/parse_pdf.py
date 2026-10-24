"""PDF -> data/md/<doc>/NN-slug.md, mỗi bài 1 file. Deterministic."""
import argparse, collections, pathlib, re, shutil, unicodedata
import pymupdf

# Symbol font -> Unicode private use area (U+F0xx); bản đồ đối chiếu ngữ cảnh 2 tài liệu BYT
SYMBOL = {0xF020: " ", 0xF02B: "+", 0xF02D: "-", 0xF044: "Δ", 0xF062: "β", 0xF06D: "μ",
          0xF0A3: "≤", 0xF0AD: "↑", 0xF0AE: "→", 0xF0AF: "↓", 0xF0B1: "±", 0xF0B3: "≥",
          0xF0B7: "-", 0xF0E0: "→", ord("ƣ"): "ư", ord("Ƣ"): "Ư"}
REFS = re.compile(r"^\s*TÀI LIỆU THAM KHẢO\s*[:.]?\s*$", re.I)
CAPCUU = re.compile(r"^[#*\s]*Bài\s+(\d+)[*\s]*$")
HSTC = re.compile(r"^[#*\s]*1\.\s*(ĐẠI CƯƠNG|KHÁI NIỆM)")  # bài "Các rối loạn thăng bằng kiềm toan" mở bằng KHÁI NIỆM CƠ BẢN


def clean(s):
    s = unicodedata.normalize("NFC", s.translate(SYMBOL))
    s = re.sub(r"[-]", "", s)  # PUA còn sót: không rõ nghĩa, bỏ
    return re.sub(r"[ \t]+$", "", s, flags=re.M)


def read_lines(pdf):
    pages = [clean(p.get_text()).splitlines() for p in pymupdf.open(pdf)]
    # số trang in = chỉ số trang + offset phổ biến nhất; chỉ bỏ dòng số khớp đúng offset (giữ số trong bảng)
    off = collections.Counter(int(l) - i for i, ls in enumerate(pages) for l in ls if l.strip().isdigit())
    off = off.most_common(1)[0][0] if off else None
    n = len(pages)
    edge = collections.Counter(l.strip() for ls in pages for l in {*ls[:2], *ls[-2:]} if l.strip())
    header = {l for l, c in edge.items() if c >= n / 2}
    out = []
    for i, ls in enumerate(pages):
        out += [l for l in ls if not (l.strip().isdigit() and int(l) - i == off) and l.strip() not in header]
    return out


def is_upper(l):
    return any(c.isalpha() for c in l) and l == l.upper()


def split(lines, profile):
    """-> [(n, title_lines, body_lines)], front_lines"""
    if profile == "capcuu":
        cuts = [(i, int(m[1])) for i, l in enumerate(lines) if (m := CAPCUU.match(l))]
        starts = [i for i, _ in cuts]
    else:
        heads = [i for i, l in enumerate(lines) if HSTC.match(l)]
        starts = []
        for h in heads:
            j = h
            while j > 0 and (not lines[j - 1].strip() or is_upper(lines[j - 1].strip())) and h - j < 6:
                j -= 1
            while j < h and not lines[j].strip():
                j += 1
            starts.append(j)
        cuts = [(s, k + 1) for k, s in enumerate(starts)]
    docs = []
    for k, (s, n) in enumerate(cuts):
        block = lines[s: starts[k + 1] if k + 1 < len(starts) else len(lines)]
        if profile == "capcuu":
            block = block[1:]
            stop = next(i for i, l in enumerate(block) if l.strip() == "MỤC TIÊU")
        else:
            stop = next(i for i, l in enumerate(block) if HSTC.match(l))
        title = [l.strip() for l in block[:stop] if l.strip()][:3]
        body = block[stop:]
        ref = next((i for i, l in enumerate(body) if REFS.match(l)), len(body))
        docs.append((n, title, body[:ref]))
    return docs, lines[: starts[0]]


def slug(s):
    s = unicodedata.normalize("NFD", s.replace("đ", "d").replace("Đ", "D"))
    s = s.encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:60].rstrip("-")


def text(lines):
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("outdir", type=pathlib.Path)
    ap.add_argument("--profile", choices=["capcuu", "hstc"], required=True)
    ap.add_argument("--clean", action="store_true")
    a = ap.parse_args()
    docs, front = split(read_lines(a.pdf), a.profile)
    if a.clean:
        shutil.rmtree(a.outdir, ignore_errors=True)
    a.outdir.mkdir(parents=True, exist_ok=True)
    (a.outdir / "00-front.md").write_text(text(front), encoding="utf-8")
    total = 0
    for n, title, body in docs:
        t = " ".join(title)
        md = f"# {t}\n\n{text(body)}"
        (a.outdir / f"{n:02d}-{slug(t)}.md").write_text(md, encoding="utf-8")
        total += len(md)
        print(f"{n:02d} {len(md):>7} {t}" + ("  <-- NGẮN" if len(md) < 1500 else ""))
    print(f"{len(docs)} bài, {total} ký tự, ~{total / 3.45:.0f} token")


if __name__ == "__main__":
    main()
