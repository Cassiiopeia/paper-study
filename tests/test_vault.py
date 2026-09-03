"""vault.py 의 seal/unseal 왕복. papers/*.pdf 와 text/*/*.md 둘 다 봉하고 되돌리는지."""

import base64
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import vault  # noqa: E402


class VaultRoundTrip(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        # 모듈 상수를 임시 루트로 돌린다 — 실제 저장소를 건드리지 않기 위해
        self._orig = (vault.ROOT, vault.PAPERS, vault.TEXT, vault.KEYFILE)
        vault.ROOT = root
        vault.PAPERS = root / "papers"
        vault.TEXT = root / "text"
        vault.KEYFILE = root / ".key"
        vault.PAPERS.mkdir()
        (vault.TEXT / "slug").mkdir(parents=True)
        vault.KEYFILE.write_text(base64.b64encode(os.urandom(32)).decode() + "\n")
        os.environ.pop("PAPER_STUDY_KEY", None)

    def tearDown(self):
        vault.ROOT, vault.PAPERS, vault.TEXT, vault.KEYFILE = self._orig
        self.tmp.cleanup()

    def test_pdf_and_text_roundtrip(self):
        pdf = vault.PAPERS / "a.pdf"
        md = vault.TEXT / "slug" / "p01.md"
        pdf.write_bytes(b"%PDF-1.4 dummy")
        md.write_text("---\npage: 1\n---\n\n본문", encoding="utf-8")

        vault.cmd_seal()
        self.assertTrue((vault.PAPERS / "a.pdf.enc").exists())
        self.assertTrue((vault.TEXT / "slug" / "p01.md.enc").exists())

        pdf.unlink()
        md.unlink()
        vault.cmd_unseal()
        self.assertEqual(pdf.read_bytes(), b"%PDF-1.4 dummy")
        self.assertEqual(md.read_text(encoding="utf-8"), "---\npage: 1\n---\n\n본문")

    def test_reseal_is_deterministic(self):
        md = vault.TEXT / "slug" / "p01.md"
        md.write_text("같은 입력", encoding="utf-8")
        vault.cmd_seal()
        first = (vault.TEXT / "slug" / "p01.md.enc").read_bytes()
        vault.cmd_seal()
        self.assertEqual(first, (vault.TEXT / "slug" / "p01.md.enc").read_bytes())

    def test_targets_cover_pdf_md_and_page_png(self):
        (vault.PAPERS / "a.pdf").write_bytes(b"x")
        (vault.TEXT / "slug" / "p01.md").write_text("x")
        (vault.TEXT / "slug" / "pages").mkdir()
        (vault.TEXT / "slug" / "pages" / "p16.png").write_bytes(b"\x89PNG")
        names = [p.name for p in vault.plain_targets()]
        self.assertEqual(names, ["a.pdf", "p01.md", "p16.png"])

    def test_page_png_roundtrip(self):
        pages = vault.TEXT / "slug" / "pages"
        pages.mkdir()
        png = pages / "p16.png"
        png.write_bytes(b"\x89PNG fake")
        vault.cmd_seal()
        self.assertTrue((pages / "p16.png.enc").exists())
        png.unlink()
        vault.cmd_unseal()
        self.assertEqual(png.read_bytes(), b"\x89PNG fake")


if __name__ == "__main__":
    unittest.main()
