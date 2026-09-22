#!/usr/bin/env python3
"""Validate a generated static wireframe without third-party dependencies."""

from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


REQUIRED_FILES = ("index.html", "styles.css", "script.js", "netlify.toml")
PLACEHOLDER_PATTERN = re.compile(r"\{\{[^{}]+\}\}|\b(?:TODO|TBD|Lorem ipsum)\b", re.I)


class PrototypeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.anchor_targets: list[str] = []
        self.local_files: list[str] = []
        self.images_without_alt: list[str] = []
        self.inputs: list[tuple[str, str]] = []
        self.label_fors: set[str] = set()
        self.has_lang = False
        self.has_viewport = False
        self.has_description = False
        self.has_title = False
        self._inside_title = False
        self._title_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        node_id = values.get("id")
        if node_id:
            self.ids.append(node_id)

        if tag == "html" and values.get("lang").strip():
            self.has_lang = True
        elif tag == "title":
            self._inside_title = True
        elif tag == "meta":
            if values.get("name", "").lower() == "viewport":
                self.has_viewport = True
            if values.get("name", "").lower() == "description" and values.get("content", "").strip():
                self.has_description = True
        elif tag == "a":
            href = values.get("href", "")
            if href.startswith("#"):
                self.anchor_targets.append(href[1:])
            self._collect_local_file(href)
        elif tag == "link":
            self._collect_local_file(values.get("href", ""))
        elif tag == "script":
            self._collect_local_file(values.get("src", ""))
        elif tag == "img":
            if "alt" not in values:
                self.images_without_alt.append(values.get("src", "<inline>"))
            self._collect_local_file(values.get("src", ""))
        elif tag in {"input", "select", "textarea"}:
            input_type = values.get("type", "").lower()
            if input_type != "hidden":
                self.inputs.append((values.get("id", ""), values.get("aria-label", "")))
        elif tag == "label" and values.get("for"):
            self.label_fors.add(values["for"])

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._inside_title = False
            self.has_title = bool("".join(self._title_text).strip())

    def handle_data(self, data: str) -> None:
        if self._inside_title:
            self._title_text.append(data)

    def _collect_local_file(self, value: str) -> None:
        if not value or value.startswith(("#", "data:", "mailto:", "tel:", "sms:")):
            return
        parsed = urlparse(value)
        if not parsed.scheme and not parsed.netloc:
            self.local_files.append(parsed.path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a static wireframe project.")
    parser.add_argument("project", type=Path, help="Project folder")
    parser.add_argument(
        "--allow-placeholders",
        action="store_true",
        help="Allow starter {{TOKENS}} while testing the bundled template.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.project.expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []

    if not root.is_dir():
        print(f"ERROR: project folder not found: {root}", file=sys.stderr)
        return 2

    for filename in REQUIRED_FILES:
        if not (root / filename).is_file():
            errors.append(f"Missing required file: {filename}")

    index_path = root / "index.html"
    css_path = root / "styles.css"
    js_path = root / "script.js"
    netlify_path = root / "netlify.toml"

    if index_path.is_file():
        html = index_path.read_text(encoding="utf-8")
        parser = PrototypeParser()
        parser.feed(html)

        duplicate_ids = sorted({node_id for node_id in parser.ids if parser.ids.count(node_id) > 1})
        if duplicate_ids:
            errors.append("Duplicate HTML ids: " + ", ".join(duplicate_ids))

        id_set = set(parser.ids)
        missing_anchors = sorted({target for target in parser.anchor_targets if target and target not in id_set})
        if missing_anchors:
            errors.append("Anchors without targets: " + ", ".join(missing_anchors))
        if "" in parser.anchor_targets:
            errors.append('Found href="#" placeholder link')

        for local_file in sorted(set(parser.local_files)):
            if local_file and not (root / local_file).is_file():
                errors.append(f"Missing referenced local file: {local_file}")

        if parser.images_without_alt:
            errors.append("Images without alt attribute: " + ", ".join(parser.images_without_alt))
        if not parser.has_lang:
            errors.append("The html element needs a non-empty lang attribute")
        if not parser.has_viewport:
            errors.append("Missing viewport meta tag")
        if not parser.has_description:
            errors.append("Missing non-empty meta description")
        if not parser.has_title:
            errors.append("Missing non-empty title")

        for field_id, aria_label in parser.inputs:
            if not field_id and not aria_label:
                errors.append("Form control without id/label or aria-label")
            elif field_id and field_id not in parser.label_fors and not aria_label:
                errors.append(f"Form control has no associated label: {field_id}")

        if not args.allow_placeholders:
            placeholders = sorted(set(PLACEHOLDER_PATTERN.findall(html)))
            if placeholders:
                errors.append("Unresolved text placeholders: " + ", ".join(placeholders[:12]))

    if css_path.is_file():
        css = css_path.read_text(encoding="utf-8")
        required_css = {
            ":focus-visible": "Visible keyboard focus styles are missing",
            "prefers-reduced-motion": "Reduced-motion handling is missing",
            "max-width: 1024px": "1024px responsive state is missing",
            "max-width: 768px": "768px responsive state is missing",
            "max-width: 480px": "480px responsive state is missing",
        }
        for marker, message in required_css.items():
            if marker not in css:
                errors.append(message)

    if js_path.is_file():
        javascript = js_path.read_text(encoding="utf-8")
        network_calls = ("fetch(", "XMLHttpRequest", "sendBeacon(")
        for marker in network_calls:
            if marker in javascript:
                errors.append(f"Prototype contains an external submission primitive: {marker}")

    if netlify_path.is_file():
        netlify = netlify_path.read_text(encoding="utf-8")
        if 'publish = "."' not in netlify:
            errors.append('netlify.toml should publish the project root: publish = "."')
        if "X-Robots-Tag" not in netlify or "noindex" not in netlify:
            warnings.append("Netlify config does not explicitly block indexing")

    for warning in warnings:
        print(f"WARN: {warning}")
    for error in errors:
        print(f"ERROR: {error}")

    if errors:
        print(f"FAILED: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1

    print(f"PASS: {root}")
    print(f"Checked {len(REQUIRED_FILES)} required files; {len(warnings)} warning(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
