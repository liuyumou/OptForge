"""Build maintained Markdown documentation and check local links and anchors."""

import argparse
import html
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

import markdown

ROOT = Path(__file__).resolve().parents[1]


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag in ("a", "img"):
            target = attrs.get("href" if tag == "a" else "src")
            if target:
                self.targets.append(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "book")
    args = parser.parse_args()
    # Original planning inputs contain unavailable external-session references.
    # Maintained documentation links to them as source artifacts, not book pages.
    sources = [path for path in ROOT.rglob("*.md") if not any(
        part in {"target", "book", ".git", ".venv", "artifacts"} for part in path.relative_to(ROOT).parts
    ) and path.name not in {"implementation-plan.md", "ai-native-optimizer-plan.md"}]
    rendered = {}
    parsed = {}
    for path in sources:
        rendered[path] = markdown.markdown(path.read_text(), extensions=["fenced_code", "tables", "toc"])
        parsed[path] = Links()
        parsed[path].feed(rendered[path])
    for path, links in parsed.items():
        for link in links.targets:
            url = urlsplit(link)
            if url.scheme or url.netloc:
                continue
            target = (path.parent / unquote(url.path)).resolve() if url.path else path
            if not target.is_relative_to(ROOT) or not target.exists():
                raise ValueError(f"{path.relative_to(ROOT)}: broken link {link}")
            if url.fragment and target in parsed and unquote(url.fragment) not in parsed[target].ids:
                raise ValueError(f"{path.relative_to(ROOT)}: missing anchor {link}")
    for path, body in rendered.items():
        for link in parsed[path].targets:
            url = urlsplit(link)
            if url.scheme or url.netloc or not url.path:
                continue
            target = (path.parent / unquote(url.path)).resolve()
            if target in rendered:
                replacement = url._replace(path=str(Path(url.path).with_suffix(".html"))).geturl()
                body = body.replace(f'href="{html.escape(link, quote=True)}"', f'href="{html.escape(replacement, quote=True)}"')
            elif target.is_file():
                copied = args.output / target.relative_to(ROOT)
                copied.parent.mkdir(parents=True, exist_ok=True)
                copied.write_bytes(target.read_bytes())
        output = args.output / path.relative_to(ROOT).with_suffix(".html")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>' + html.escape(path.stem) + '</title><body><main>' + body + '</main></body></html>\n')
    (args.output / "index.html").write_text('<!doctype html><html lang="en"><title>AI Optimizer</title><a href="README.html">AI Optimizer documentation</a></html>\n')
    print(f"documentation built: {len(sources)} pages; internal links and anchors passed")


if __name__ == "__main__":
    main()
