#!/usr/bin/env python3
"""인출 카드와 복습 일정.

기록은 저절로 쌓이지만 기억은 다시 꺼낼 때만 굳는다. 이 도구가 "언제 다시 물을지" 를 맡는다.

    python scripts/review.py due                        오늘 물어야 할 카드
    python scripts/review.py add <슬러그> "질문" "근거쪽"  카드 추가
    python scripts/review.py grade <id> o|t|x           채점 (맞음/반만/틀림)
    python scripts/review.py list [<슬러그>]             전체 보기
    python scripts/review.py stats                      현황

카드에 답을 적지 않는다. 질문과 근거 쪽만 적는다. 답이 카드에 있으면 눈으로 읽고
넘어가게 되고 그건 인출이 아니다. 채점은 조수가 원문의 그 쪽을 보고 한다.

저장소는 knowledge/cards.md 한 파일이다. 사람이 열어 읽을 수 있게 마크다운 표로 둔다.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CARDS = ROOT / "knowledge" / "cards.md"

# 단계별 다음 복습까지의 날 수. 맞을 때마다 한 칸씩 올라간다.
INTERVALS = [1, 3, 7, 21, 60]
COLS = ["id", "논문", "질문", "근거", "단계", "다음복습", "이력"]

HEADER = """# 인출 카드

논문을 읽으며 만든 질문이 여기 쌓이고, 정해진 날에 다시 돌아온다.
**답은 적지 않는다** — 질문과 근거 쪽만 둔다. 답이 보이면 인출 연습이 되지 않는다.

`단계` 는 맞힌 횟수다. 0→1일, 1→3일, 2→7일, 3→21일, 4→60일 뒤에 다시 묻는다.
틀리면 0 으로 돌아간다.

이 표는 `scripts/review.py` 가 읽고 쓴다. 손으로 고쳐도 되지만 열 개수는 지킨다.

"""


def today():
    return date.today().isoformat()


def esc(s):
    return str(s).replace("|", "/").replace("\n", " ").strip()


def load():
    if not CARDS.exists():
        return []
    rows = []
    for line in CARDS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != len(COLS):
            continue
        if cells[0] in ("id", "---") or set(cells[0]) <= {"-", ":"}:
            continue
        rows.append(dict(zip(COLS, cells)))
    return rows


def save(rows):
    rows.sort(key=lambda r: (r["다음복습"], r["id"]))
    out = [HEADER, "| " + " | ".join(COLS) + " |", "|" + "---|" * len(COLS)]
    for r in rows:
        out.append("| " + " | ".join(esc(r[c]) for c in COLS) + " |")
    out.append("")
    CARDS.parent.mkdir(exist_ok=True)
    CARDS.write_text("\n".join(out), encoding="utf-8")


def prefix(slug):
    parts = [p for p in slug.replace("_", "-").split("-") if p]
    return "".join(p[0] for p in parts)[:4].lower() or "c"


def cmd_add(slug, question, source):
    rows = load()
    pre = prefix(slug)
    n = 1 + max([int(r["id"].rsplit("-", 1)[1]) for r in rows if r["id"].startswith(pre + "-")] or [0])
    cid = f"{pre}-{n:02d}"
    rows.append({
        "id": cid, "논문": slug, "질문": question, "근거": source,
        "단계": "0", "다음복습": today(), "이력": "",
    })
    save(rows)
    print(f"[+] {cid}  {question}")
    print(f"    근거 {source} · 다음 복습 오늘")


def cmd_grade(cid, mark):
    if mark not in ("o", "t", "x"):
        print("판정은 o(맞음) / t(반만) / x(틀림) 중 하나다.", file=sys.stderr)
        raise SystemExit(2)
    rows = load()
    for r in rows:
        if r["id"] != cid:
            continue
        stage = int(r["단계"] or 0)
        if mark == "o":
            stage = min(stage + 1, len(INTERVALS) - 1)
            days = INTERVALS[stage]
        elif mark == "t":
            days = max(1, INTERVALS[stage] // 2)
        else:
            stage, days = 0, 1
        r["단계"] = str(stage)
        r["다음복습"] = (date.today() + timedelta(days=days)).isoformat()
        hist = [h for h in r["이력"].split() if h][-5:]
        hist.append(f"{date.today():%m%d}{mark}")
        r["이력"] = " ".join(hist)
        save(rows)
        print(f"[+] {cid} → 단계 {stage}, 다음 복습 {r['다음복습']} ({days}일 뒤)")
        return
    print(f"그런 카드가 없다: {cid}", file=sys.stderr)
    raise SystemExit(1)


def cmd_due():
    rows = [r for r in load() if r["다음복습"] <= today()]
    if not rows:
        print("오늘 복습할 카드가 없다. 바로 새 구간으로 간다.")
        return
    print(f"오늘 복습 {len(rows)}장\n")
    for r in rows:
        overdue = (date.fromisoformat(today()) - date.fromisoformat(r["다음복습"])).days
        late = f"  ({overdue}일 밀림)" if overdue > 0 else ""
        print(f"  [{r['id']}] {r['질문']}")
        print(f"        근거 {r['근거']} · 단계 {r['단계']}{late}")
    print("\n채점: python scripts/review.py grade <id> o|t|x")


def cmd_list(slug=None):
    rows = [r for r in load() if not slug or r["논문"] == slug]
    if not rows:
        print("카드가 없다.")
        return
    for r in rows:
        print(f"  [{r['id']}] 단계{r['단계']} {r['다음복습']}  {r['질문']}")
    print(f"\n총 {len(rows)}장")


def cmd_stats():
    rows = load()
    if not rows:
        print("카드가 없다.")
        return
    due = sum(1 for r in rows if r["다음복습"] <= today())
    by_paper = {}
    by_stage = {}
    for r in rows:
        by_paper[r["논문"]] = by_paper.get(r["논문"], 0) + 1
        by_stage[r["단계"]] = by_stage.get(r["단계"], 0) + 1
    print(f"카드 {len(rows)}장 · 오늘 복습 {due}장\n")
    print("논문별")
    for k, v in sorted(by_paper.items()):
        print(f"  {v:3}장  {k}")
    print("\n단계별 (높을수록 오래 기억에 남은 것)")
    for k in sorted(by_stage):
        print(f"  단계 {k}: {by_stage[k]}장")


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        raise SystemExit(2)
    cmd = a[0]
    if cmd == "due":
        cmd_due()
    elif cmd == "add" and len(a) == 4:
        cmd_add(a[1], a[2], a[3])
    elif cmd == "grade" and len(a) == 3:
        cmd_grade(a[1], a[2])
    elif cmd == "list":
        cmd_list(a[1] if len(a) > 1 else None)
    elif cmd == "stats":
        cmd_stats()
    else:
        print(__doc__)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
