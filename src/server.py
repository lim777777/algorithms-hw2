"""Serve the URL shortener and a view of its hash table."""

import argparse
from dataclasses import dataclass
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import sys
from urllib.parse import parse_qsl

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.base62 import ALPHABET
from src.hash_table import horner_hash
from src.linear_probing import LinearProbingHashTable
from src.shortener import MAX_URL_LENGTH, Shortener


MAX_FORM_BYTES = 3 * MAX_URL_LENGTH + len("url=")
STYLE = """
  * { box-sizing: border-box; }
  body {
    margin: 0;
    min-height: 100vh;
    background: linear-gradient(135deg, #287f85, #163953 46%, #091221);
    color: #131313;
    font: 1rem/1.5 system-ui, sans-serif;
  }
  .page {
    --gutter: clamp(12px, 2.6vw, 30px);
    --page-inset: clamp(16px, 8vw, 92px);
    margin: var(--gutter);
    padding: 22px var(--page-inset) 42px;
    min-height: calc(100vh - 2 * var(--gutter));
    background: #fafafa;
    border-radius: 12px;
    box-shadow: 0 6px 18px #09122166;
  }
  a { color: #0000bb; }
  a:visited { color: #551a8b; }
  nav a { display: inline-block; }
  nav { margin-bottom: 28px; }
  h1 { margin: 0 0 24px; font-size: 2rem; line-height: 1.25; }
  label { display: block; }
  .form-row { display: flex; max-width: 650px; }
  input, button { font: inherit; }
  input {
    min-width: 0;
    flex: 1;
    border: 1px solid #565656;
    border-radius: 2px;
    padding: 5px 8px;
  }
  button { padding: 5px 5px; font-size: 0.875rem; cursor: pointer; flex-shrink: 0; }
  p { margin: 0 0 16px; }
  .original { overflow-wrap: anywhere; }
  .table-wrap { overflow-x: auto; }
  table { border-collapse: collapse; width: 100%; text-align: left; }
  th, td { border: 1px solid #b3b3b3; padding: 8px; vertical-align: top; }
  th:first-child { width: 5rem; }
  @media (min-width: 48rem) {
    .table-wrap { margin-inline-end: calc(-1 * var(--page-inset)); }
    .linear-table th:first-child { width: 15%; }
  }
  .chain-length { margin-bottom: 6px; }
  .chain { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
  .node { min-width: 0; border: 1px solid #777; border-radius: 5px; padding: 7px 8px; }
  summary { cursor: pointer; margin-top: 8px; }
  details p { margin-top: 12px; }
  details ol { margin: 0 0 8px; padding-inline-start: 1.7rem; }
  details { overflow-wrap: anywhere; }
"""


@dataclass(frozen=True)
class ShortenerView:
    prefix: str
    shortener: Shortener
    linear: bool = False


def page(title: str, content: str, basic_prefix: str) -> str:
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>{STYLE}</style>
</head>
<body>
  <div class="page">
    <nav aria-label="페이지 이동">
      <a href="{basic_prefix}/">기본 홈</a> | <a href="{basic_prefix}/table">기본 해시 테이블</a> |
      <a href="/linear/">선형 탐지 홈</a> | <a href="/linear/table">선형 탐지 테이블</a>
    </nav>
    <main>
      <h1>{escape(title)}</h1>
      {content}
    </main>
  </div>
</body>
</html>"""


def home(prefix: str) -> str:
    return f"""
      <form action="{prefix}/shorten" method="post">
        <label for="url">원래 URL</label>
        <div class="form-row">
          <input id="url" type="url" name="url" required maxlength="{MAX_URL_LENGTH}">
          <button type="submit">줄이기</button>
        </div>
      </form>"""


def short_link(code: str, linear: bool) -> str:
    if linear:
        path = f"/linear/s/{code}"
    else:
        # Preserve the normal /code path while keeping /table available.
        path = f"/s/{code}" if code == "table" else f"/{code}"
    return f'<a href="{path}">{path}</a>'


def result(url: str, code: str, view: ShortenerView) -> str:
    return f"""
      <p class="original">원래 URL: {escape(url)}</p>
      <p>짧은 링크: {short_link(code, view.linear)}</p>
      <p><a href="{view.prefix}/">다른 URL 줄이기</a></p>"""


def hash_details(url: str, capacity: int, slot: int | None) -> str:
    steps: list[tuple[str, int, int]] = []
    index = horner_hash(url, capacity, steps=steps)
    calculations = []
    for char, previous, current in steps:
        equation = f"{char!r}: ({previous} * 31 + {ord(char)}) % {capacity} = {current}"
        calculations.append(f"<li>{escape(equation)}</li>")
    probe_details = ""
    if slot is not None:
        probes = (slot - index) % capacity + 1
        path = " → ".join(str((index + offset) % capacity) for offset in range(probes))
        probe_details = (f"<p>시작 칸 {index}, 저장 칸 {slot}, 탐지 {probes}회<br>"
                         f"탐지 순서: {path}</p>")
    return f"""
      <details>
        <summary>호너 해시 계산 과정</summary>
        <p>초기값 0, 버킷 수 {capacity}, 결과 {index}</p>
        {probe_details}
        <ol>{''.join(calculations)}</ol>
      </details>"""


def table_content(buckets: list[list[tuple[str, str]]], linear: bool) -> str:
    capacity = len(buckets)
    rows = []
    arrow = '<span aria-hidden="true">→</span>'
    for index, bucket in enumerate(buckets):
        cell = "비어 있음"
        if bucket:
            slot = index if linear else None
            nodes = []
            for url, code in bucket:
                nodes.append(f"""
                  <div class="node">
                    <div class="original">URL: {escape(url)}</div>
                    <div>코드: {escape(code)}</div>
                    <div>짧은 링크: {short_link(code, linear)}</div>
                    {hash_details(url, capacity, slot)}
                  </div>""")
            chain_length = ""
            if not linear:
                nodes.append("<span>NULL</span>")
                chain_length = f'<div class="chain-length">체인 길이: {len(bucket)}</div>'
            cell = f'{chain_length}<div class="chain">{arrow.join(nodes)}</div>'
        rows.append(f'<tr><th scope="row">{index}</th><td>{cell}</td></tr>')
    column = "선형 탐지" if linear else "연결 리스트"
    table_class = ' class="linear-table"' if linear else ""
    return f"""
      <p>버킷 수: {capacity}</p>
      <div class="table-wrap">
        <table{table_class}>
          <thead><tr><th scope="col">칸</th><th scope="col">{column}</th></tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
      </div>"""


class ShortenerHandler(BaseHTTPRequestHandler):
    def _send_page(self, title: str, content: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = page(title, content, self.server.basic.prefix).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_problem(self, status: HTTPStatus, title: str, message: str) -> None:
        self._send_page(title, f"<p>{escape(message)}</p>", status)

    def _not_found(self) -> None:
        self._send_problem(HTTPStatus.NOT_FOUND, "찾을 수 없음", "등록되지 않은 링크입니다.")

    def do_GET(self) -> None:
        path = self.path.partition("?")[0]
        if self.server.linear_default and path in ("/", "/table"):
            path = f"/linear{path}"
        for view in (self.server.basic, self.server.linear):
            if path == f"{view.prefix}/":
                title = "선형 탐지 URL 단축기" if view.linear else "URL 단축기"
                self._send_page(title, home(view.prefix))
                return
            if path == f"{view.prefix}/table":
                title = "선형 탐지 해시 테이블" if view.linear else "해시 테이블"
                self._send_page(title, table_content(view.shortener.url_buckets(), view.linear))
                return

        if path.startswith("/linear/s/"):
            shortener = self.server.linear.shortener
            code = path.removeprefix("/linear/s/")
        else:
            shortener = self.server.basic.shortener
            code = "table" if path == "/s/table" else path.removeprefix("/")
        if not path.startswith("/") or not code or any(char not in ALPHABET for char in code):
            self._not_found()
            return
        url = shortener.expand(code)
        if url is None:
            self._not_found()
            return

        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", url)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self) -> None:
        path = self.path.partition("?")[0]
        if path == "/linear/shorten" or (self.server.linear_default and path == "/shorten"):
            view = self.server.linear
        elif path == f"{self.server.basic.prefix}/shorten":
            view = self.server.basic
        else:
            self._not_found()
            return

        try:
            url = self._read_url()
            code = view.shortener.shorten(url)
        except ValueError:
            self._send_problem(HTTPStatus.BAD_REQUEST, "잘못된 URL",
                               f"호스트가 있는 {MAX_URL_LENGTH}자 이하의 HTTP 또는 HTTPS URL을 입력하세요.")
            return
        self._send_page("단축 결과", result(url, code, view))

    def _read_url(self) -> str:
        size = self.headers.get("Content-Length", "")
        if (self.headers.get_content_type() != "application/x-www-form-urlencoded"
                or not size.isascii() or not size.isdecimal() or len(size) > len(str(MAX_FORM_BYTES))):
            raise ValueError("invalid form headers")
        length = int(size)
        if not 0 < length <= MAX_FORM_BYTES:
            raise ValueError("invalid form length")
        data = self.rfile.read(length)
        if len(data) != length:
            raise ValueError("incomplete form body")
        fields = parse_qsl(data.decode("ascii"), keep_blank_values=True,
                           strict_parsing=True, errors="strict", max_num_fields=1)
        if len(fields) != 1 or fields[0][0] != "url":
            raise ValueError("missing URL field")
        return fields[0][1]


class ShortenerServer(HTTPServer):
    def __init__(self, address: tuple[str, int], mode: str = "chaining"):
        super().__init__(address, ShortenerHandler)
        self.linear_default = mode == "linear"
        basic_prefix = "/basic" if self.linear_default else ""
        self.basic = ShortenerView(basic_prefix, Shortener())
        self.linear = ShortenerView("/linear", Shortener(table_factory=LinearProbingHashTable), linear=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the URL shortener.")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--mode", choices=("chaining", "linear"), default="chaining")
    args = parser.parse_args()
    with ShortenerServer(("0.0.0.0", args.port), args.mode) as server:
        print(f"URL 단축기 http://localhost:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
