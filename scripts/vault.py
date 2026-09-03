#!/usr/bin/env python3
"""papers/ 원문 PDF 와 text/ 옮겨 적은 텍스트를 봉하고 여는 도구.

공개 저장소에는 .enc 만 올라가고 평문은 절대 커밋되지 않는다.

    python scripts/vault.py keygen     키를 새로 만든다 (최초 1회)
    python scripts/vault.py seal       papers/*.pdf, text/*/*.md  -> .enc
    python scripts/vault.py unseal     .enc -> 평문
    python scripts/vault.py status     무엇이 봉해졌고 무엇이 열려 있나

키는 환경변수 PAPER_STUDY_KEY(base64) 를 먼저 보고, 없으면 저장소 루트의
.key 파일을 읽는다. 둘 다 gitignore 대상이다. 키를 코드나 문서에 적지 않는다.

nonce 를 HMAC(키, 원문) 으로 만들기 때문에 같은 입력은 언제 봉해도 같은
암호문이 나온다. 다시 seal 해도 git diff 가 생기지 않는다.
"""

import base64
import hashlib
import hmac
import os
import sys
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = Path(__file__).resolve().parent.parent
PAPERS = ROOT / "papers"
TEXT = ROOT / "text"
KEYFILE = ROOT / ".key"
MAGIC = b"PSEAL1"
NONCE_LEN = 12


def die(msg):
    print(f"[!] {msg}", file=sys.stderr)
    raise SystemExit(1)


def load_key():
    raw = os.environ.get("PAPER_STUDY_KEY")
    source = "환경변수 PAPER_STUDY_KEY"
    if not raw:
        if not KEYFILE.exists():
            die(
                "키가 없다. 최초라면 `python scripts/vault.py keygen` 을 실행하고,\n"
                "    다른 PC 라면 비밀번호 관리자에 둔 키를 .key 에 붙여넣는다."
            )
        raw = KEYFILE.read_text(encoding="utf-8").strip()
        source = ".key 파일"
    try:
        key = base64.b64decode(raw, validate=True)
    except Exception:
        die(f"{source} 의 값이 base64 가 아니다.")
    if len(key) != 32:
        die(f"{source} 의 키가 {len(key)}바이트다. 32바이트여야 한다.")
    return key


def nonce_for(key, plaintext):
    """원문에서 결정론적으로 nonce 를 뽑는다 — 같은 입력이면 같은 암호문."""
    return hmac.new(key, plaintext, hashlib.sha256).digest()[:NONCE_LEN]


def plain_targets():
    """봉할 평문. text/<슬러그>/*.md 와 그림·표 쪽 이미지 text/<슬러그>/pages/*.png."""
    yield from sorted(PAPERS.glob("*.pdf"))
    yield from sorted(TEXT.glob("*/*.md"))
    yield from sorted(TEXT.glob("*/pages/*.png"))


def sealed_targets():
    yield from sorted(PAPERS.glob("*.pdf.enc"))
    yield from sorted(TEXT.glob("*/*.md.enc"))
    yield from sorted(TEXT.glob("*/pages/*.png.enc"))


def is_text(path):
    return TEXT in path.parents


def text_slug(path):
    return path.relative_to(TEXT).parts[0]


def cmd_keygen():
    if KEYFILE.exists():
        die(".key 가 이미 있다. 새로 만들면 기존 .enc 를 못 연다. 지우려면 직접 지운다.")
    key = base64.b64encode(os.urandom(32)).decode()
    KEYFILE.write_text(key + "\n", encoding="utf-8")
    print("[+] .key 를 만들었다.\n")
    print("[!] 키 값은 일부러 화면에 찍지 않는다 — 터미널 기록과 대화 기록에 남기지 않기 위해서다.")
    print("    지금 .key 파일을 열어 값을 비밀번호 관리자에 옮겨 둔다.")
    print("    잃으면 .enc 를 열 수 없다 (원문은 다시 받으면 되니 치명적이진 않다).")
    print("    .key 는 gitignore 대상이라 커밋되지 않는다.")


def cmd_seal():
    key = load_key()
    aes = AESGCM(key)
    made = kept = 0
    text_stats = {}  # 슬러그 -> [새로 봉함, 그대로]. 25줄씩 찍지 않으려고 묶는다
    for src in plain_targets():
        enc = src.with_suffix(src.suffix + ".enc")
        data = src.read_bytes()
        nonce = nonce_for(key, data)
        blob = MAGIC + nonce + aes.encrypt(nonce, data, MAGIC)
        changed = not (enc.exists() and enc.read_bytes() == blob)
        if changed:
            enc.write_bytes(blob)
        if is_text(src):
            stat = text_stats.setdefault(text_slug(src), [0, 0])
            stat[0 if changed else 1] += 1
        elif changed:
            print(f"  + {enc.name} ({len(blob):,} bytes)")
        else:
            print(f"  = {enc.name} (그대로)")
        made += changed
        kept += not changed
    for slug, (m, k) in text_stats.items():
        print(f"  text/{slug}: 새로 봉함 {m}, 그대로 {k}")
    if made == kept == 0:
        print("  봉할 평문이 없다.")
    else:
        print(f"\n[+] 새로 봉함 {made}개, 변화 없음 {kept}개")


def cmd_unseal():
    key = load_key()
    aes = AESGCM(key)
    done = skipped = 0
    text_stats = {}
    for enc in sealed_targets():
        plain = enc.with_suffix("")
        exists = plain.exists()
        if not exists:
            blob = enc.read_bytes()
            if not blob.startswith(MAGIC):
                die(f"{enc.name} 이 이 도구가 만든 파일이 아니다.")
            nonce = blob[len(MAGIC):len(MAGIC) + NONCE_LEN]
            try:
                data = aes.decrypt(nonce, blob[len(MAGIC) + NONCE_LEN:], MAGIC)
            except Exception:
                die(f"{enc.name} 복호화 실패 — 키가 이 파일의 키가 아니다.")
            plain.write_bytes(data)
        if is_text(plain):
            stat = text_stats.setdefault(text_slug(plain), [0, 0])
            stat[1 if exists else 0] += 1
        elif exists:
            print(f"  = {plain.name} (이미 있음)")
        else:
            print(f"  + {plain.name} ({plain.stat().st_size:,} bytes)")
        done += not exists
        skipped += exists
    for slug, (d, s) in text_stats.items():
        print(f"  text/{slug}: 새로 연 것 {d}, 이미 있던 것 {s}")
    if done == skipped == 0:
        print("  열 .enc 가 없다.")
    else:
        print(f"\n[+] 새로 연 것 {done}개, 이미 있던 것 {skipped}개")


def cmd_status():
    pdfs = {p.name for p in PAPERS.glob("*.pdf")}
    encs = {e.name[:-4] for e in PAPERS.glob("*.pdf.enc")}
    key_where = (
        "환경변수" if os.environ.get("PAPER_STUDY_KEY")
        else ".key 파일" if KEYFILE.exists()
        else "없음 (keygen 필요)"
    )
    print(f"키: {key_where}\n")
    for name in sorted(pdfs | encs):
        mark = "봉함+평문" if name in pdfs and name in encs else "평문만 (seal 필요)" if name in pdfs else "봉함만 (unseal 필요)"
        print(f"  {mark:20} {name}")
    if not (pdfs or encs):
        print("  papers/ 가 비어 있다.")
    for slug_dir in sorted(p for p in TEXT.glob("*") if p.is_dir()):
        n_md = len(list(slug_dir.glob("*.md")))
        n_enc = len(list(slug_dir.glob("*.md.enc")))
        n_png = len(list(slug_dir.glob("pages/*.png")))
        n_png_enc = len(list(slug_dir.glob("pages/*.png.enc")))
        print(f"  text/{slug_dir.name:22} 쪽 평문 {n_md:2} · 봉함 {n_enc:2} │ 이미지 평문 {n_png:2} · 봉함 {n_png_enc:2}")


def main():
    cmds = {"keygen": cmd_keygen, "seal": cmd_seal, "unseal": cmd_unseal, "status": cmd_status}
    if len(sys.argv) != 2 or sys.argv[1] not in cmds:
        print(__doc__)
        raise SystemExit(2)
    PAPERS.mkdir(exist_ok=True)
    cmds[sys.argv[1]]()


if __name__ == "__main__":
    main()
