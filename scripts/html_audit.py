#!/usr/bin/env python3
"""Static HTML accessibility check covering the axe-core WCAG A/AA rules
that are reliably visible in raw markup.

Used by the pre-commit gate. Reads one or more HTML files (or stdin), reports
findings as JSON, and exits non-zero on any finding.

This is intentionally narrow:
  - It catches obvious source-level failures (missing alt, missing label,
    aria-hidden-body, blink/marquee, meta-refresh, etc.)
  - It does NOT compute rendered-DOM contrast, landmark coverage, or focus
    state. Those go through the CI layer (@axe-core/cli on the built site).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from html.parser import HTMLParser


# -- Reference data ---------------------------------------------------------

# WAI-ARIA 1.2 roles (abridged but covers what real markup uses).
VALID_ARIA_ROLES = frozenset(
    """alert alertdialog application article banner blockquote button caption cell
    checkbox code columnheader combobox complementary contentinfo definition deletion
    dialog directory document emphasis feed figure form generic grid gridcell group
    heading img insertion link list listbox listitem log main mark marquee math meter
    menu menubar menuitem menuitemcheckbox menuitemradio navigation none note option
    paragraph presentation progressbar radio radiogroup region row rowgroup rowheader
    scrollbar search searchbox separator slider spinbutton status strong subscript
    superscript switch tab table tablist tabpanel term textbox time timer toolbar
    tooltip tree treegrid treeitem""".split()
)

# WAI-ARIA 1.2 attributes (also abridged to the reasonably current set).
VALID_ARIA_ATTRS = frozenset(
    """aria-activedescendant aria-atomic aria-autocomplete aria-braillelabel
    aria-brailleroledescription aria-busy aria-checked aria-colcount aria-colindex
    aria-colindextext aria-colspan aria-controls aria-current aria-describedby
    aria-description aria-details aria-disabled aria-dropeffect aria-errormessage
    aria-expanded aria-flowto aria-grabbed aria-haspopup aria-hidden aria-invalid
    aria-keyshortcuts aria-label aria-labelledby aria-level aria-live aria-modal
    aria-multiline aria-multiselectable aria-orientation aria-owns aria-placeholder
    aria-posinset aria-pressed aria-readonly aria-relevant aria-required
    aria-roledescription aria-rowcount aria-rowindex aria-rowindextext aria-rowspan
    aria-selected aria-setsize aria-sort aria-valuemax aria-valuemin aria-valuenow
    aria-valuetext""".split()
)

# axe-core impacts for the rules we check. Keep aligned with rule-descriptions.md.
IMPACT = {
    "image-alt": "critical",
    "input-image-alt": "critical",
    "input-button-name": "critical",
    "label": "critical",
    "select-name": "critical",
    "button-name": "critical",
    "video-caption": "critical",
    "meta-refresh": "critical",
    "aria-required-attr": "critical",
    "aria-valid-attr": "critical",
    "aria-roles": "critical",
    "aria-hidden-body": "critical",
    "duplicate-id-aria": "critical",
    "link-name": "serious",
    "html-has-lang": "serious",
    "html-lang-valid": "serious",
    "valid-lang": "serious",
    "document-title": "serious",
    "frame-title": "serious",
    "summary-name": "serious",
    "blink": "serious",
    "marquee": "serious",
    "server-side-image-map": "minor",
    "object-alt": "serious",
    "role-img-alt": "serious",
    "aria-allowed-attr": "serious",
    "nested-interactive": "serious",
    "meta-viewport": "moderate",
    "no-autoplay-audio": "moderate",
    "form-field-multiple-labels": "moderate",
}


_BCP47_RE = re.compile(r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*$")


@dataclass
class Finding:
    rule: str
    impact: str
    line: int
    col: int
    element: str
    message: str
    file: str = ""


@dataclass
class _ElementContext:
    tag: str
    attrs: dict
    line: int
    col: int
    text_buf: list[str] = field(default_factory=list)


class A11yHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.findings: list[Finding] = []
        self.stack: list[_ElementContext] = []
        # Page-scope state
        self.has_html_lang: tuple[bool, str | None] = (False, None)
        self.has_title: bool = False
        self.title_text: list[str] = []
        self.in_title: bool = False
        self.ids_seen: dict[str, int] = {}  # id -> count
        self.id_refs: list[tuple[str, int, int]] = []  # (id, line, col)
        self.html_seen = False
        self.body_attrs: dict | None = None
        self.body_pos: tuple[int, int] = (0, 0)
        # Form-field tracking for label coverage
        self.label_for_targets: set[str] = set()
        self.form_fields: list[_ElementContext] = []

    # ---- helpers ----------------------------------------------------------

    def _attr_dict(self, attrs: list[tuple[str, str | None]]) -> dict:
        return {k.lower(): (v if v is not None else "") for k, v in attrs}

    def _add(self, ctx: _ElementContext, rule: str, message: str) -> None:
        self.findings.append(
            Finding(
                rule=rule,
                impact=IMPACT.get(rule, "serious"),
                line=ctx.line,
                col=ctx.col,
                element=ctx.tag,
                message=message,
            )
        )

    def _has_accessible_name(self, ctx: _ElementContext) -> bool:
        a = ctx.attrs
        if a.get("aria-label", "").strip():
            return True
        if a.get("aria-labelledby", "").strip():
            return True
        text = "".join(ctx.text_buf).strip()
        return bool(text)

    # ---- HTMLParser hooks -------------------------------------------------

    def handle_starttag(self, tag: str, attrs):
        line, col = self.getpos()
        a = self._attr_dict(attrs)
        ctx = _ElementContext(tag=tag, attrs=a, line=line, col=col)
        self.stack.append(ctx)

        # Track ids and references
        if "id" in a and a["id"]:
            self.ids_seen[a["id"]] = self.ids_seen.get(a["id"], 0) + 1
        for ref_attr in ("aria-labelledby", "aria-describedby", "aria-controls"):
            if ref_attr in a and a[ref_attr]:
                for token in a[ref_attr].split():
                    self.id_refs.append((token, line, col))

        # ARIA validity
        for k in a:
            if k.startswith("aria-") and k not in VALID_ARIA_ATTRS:
                self._add(
                    ctx,
                    "aria-valid-attr",
                    f'Unknown ARIA attribute "{k}"',
                )
        if "role" in a and a["role"]:
            for r in a["role"].split():
                if r not in VALID_ARIA_ROLES:
                    self._add(
                        ctx,
                        "aria-roles",
                        f'Invalid ARIA role "{r}"',
                    )

        # Per-tag rules
        method = getattr(self, f"_check_{tag}", None)
        if method is not None:
            method(ctx)

        # Generic structural checks not tied to a single tag
        self._check_role_img(ctx)

        # Self-closing void elements get no end tag. Finalize them now.
        if tag in _VOID_ELEMENTS:
            self._finalize(ctx)
            self.stack.pop()

    def handle_endtag(self, tag: str):
        # Find matching ctx (forgive bad nesting by walking back)
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i].tag == tag:
                ctx = self.stack[i]
                self._finalize(ctx)
                del self.stack[i:]
                if tag == "title":
                    self.in_title = False
                return
        # Stray end tag. Ignore.

    def handle_data(self, data: str) -> None:
        for ctx in self.stack:
            ctx.text_buf.append(data)
        if self.in_title:
            self.title_text.append(data)

    def handle_startendtag(self, tag: str, attrs) -> None:  # <foo />
        self.handle_starttag(tag, attrs)
        if tag not in _VOID_ELEMENTS:
            # Treat self-closing of non-void as immediate close.
            if self.stack and self.stack[-1].tag == tag:
                self._finalize(self.stack[-1])
                self.stack.pop()

    # ---- per-tag checks ---------------------------------------------------

    def _check_html(self, ctx: _ElementContext) -> None:
        self.html_seen = True
        lang = ctx.attrs.get("lang", "")
        xml_lang = ctx.attrs.get("xml:lang", "")
        if not lang:
            self._add(ctx, "html-has-lang", "<html> missing lang attribute")
        elif not _BCP47_RE.match(lang):
            self._add(
                ctx,
                "html-lang-valid",
                f'<html lang="{lang}"> is not a valid BCP-47 language tag',
            )
        if lang and xml_lang and lang.split("-")[0].lower() != xml_lang.split("-")[0].lower():
            self._add(ctx, "valid-lang", "lang and xml:lang base languages differ")
        if lang:
            self.has_html_lang = (True, lang)

    def _check_body(self, ctx: _ElementContext) -> None:
        self.body_attrs = ctx.attrs
        self.body_pos = (ctx.line, ctx.col)
        if ctx.attrs.get("aria-hidden", "").lower() == "true":
            self._add(ctx, "aria-hidden-body", '<body> must not have aria-hidden="true"')

    def _check_title(self, ctx: _ElementContext) -> None:
        self.in_title = True

    def _check_img(self, ctx: _ElementContext) -> None:
        a = ctx.attrs
        # role="presentation"|"none" exempts from alt requirement
        role = a.get("role", "")
        is_presentational = role in ("presentation", "none")
        has_alt_attr = "alt" in a  # empty alt="" is fine, missing attr is not
        has_aria_name = bool(a.get("aria-label") or a.get("aria-labelledby"))
        if not is_presentational and not has_alt_attr and not has_aria_name:
            self._add(
                ctx,
                "image-alt",
                "<img> missing alt; use alt=\"\" for decorative images",
            )
        if "ismap" in a:
            self._add(
                ctx,
                "server-side-image-map",
                "<img ismap> uses a server-side image map (keyboard-inaccessible)",
            )

    def _check_input(self, ctx: _ElementContext) -> None:
        a = ctx.attrs
        type_ = a.get("type", "text").lower()
        if type_ == "image":
            if not (a.get("alt") or a.get("aria-label") or a.get("aria-labelledby")):
                self._add(
                    ctx,
                    "input-image-alt",
                    '<input type="image"> requires alt or aria-label[ledby]',
                )
        elif type_ == "button":
            if not (a.get("value") or a.get("aria-label") or a.get("aria-labelledby")):
                self._add(
                    ctx,
                    "input-button-name",
                    '<input type="button"> requires non-empty value or aria-label[ledby]',
                )
        elif type_ in ("hidden", "submit", "reset"):
            # submit/reset have user-agent default labels, hidden has no UI.
            return
        else:
            # Form-field. Needs a label of some kind. Defer until we've seen
            # all <label for> targets; queue and resolve in close().
            self.form_fields.append(ctx)

    def _check_select(self, ctx: _ElementContext) -> None:
        self.form_fields.append(ctx)

    def _check_textarea(self, ctx: _ElementContext) -> None:
        self.form_fields.append(ctx)

    def _check_label(self, ctx: _ElementContext) -> None:
        for_id = ctx.attrs.get("for", "")
        if for_id:
            self.label_for_targets.add(for_id)

    def _check_button(self, ctx: _ElementContext) -> None:
        # Resolved at close time once we have the text content.
        pass

    def _check_a(self, ctx: _ElementContext) -> None:
        # Resolved at close time.
        pass

    def _check_iframe(self, ctx: _ElementContext) -> None:
        a = ctx.attrs
        if not (a.get("title") or a.get("aria-label") or a.get("aria-labelledby")):
            self._add(ctx, "frame-title", "<iframe> requires title or aria-label[ledby]")

    def _check_frame(self, ctx: _ElementContext) -> None:
        self._check_iframe(ctx)

    def _check_meta(self, ctx: _ElementContext) -> None:
        a = ctx.attrs
        if a.get("http-equiv", "").lower() == "refresh":
            content = a.get("content", "")
            m = re.match(r"^\s*(\d+)", content)
            if m and int(m.group(1)) > 0:
                self._add(ctx, "meta-refresh", "<meta http-equiv=\"refresh\"> delay > 0")
        if a.get("name", "").lower() == "viewport":
            content = a.get("content", "").lower()
            if "user-scalable=no" in content or "user-scalable=0" in content:
                self._add(ctx, "meta-viewport", "viewport disables user scaling")
            m = re.search(r"maximum-scale\s*=\s*([\d.]+)", content)
            if m and float(m.group(1)) < 2:
                self._add(ctx, "meta-viewport", "viewport maximum-scale < 2")

    def _check_blink(self, ctx: _ElementContext) -> None:
        self._add(ctx, "blink", "<blink> is forbidden by 2.2.2")

    def _check_marquee(self, ctx: _ElementContext) -> None:
        self._add(ctx, "marquee", "<marquee> is forbidden by 2.2.2")

    def _check_video(self, ctx: _ElementContext) -> None:
        if "autoplay" in ctx.attrs and "muted" not in ctx.attrs and "controls" not in ctx.attrs:
            self._add(
                ctx,
                "no-autoplay-audio",
                "<video autoplay> without muted/controls may autoplay audio",
            )

    def _check_audio(self, ctx: _ElementContext) -> None:
        if "autoplay" in ctx.attrs and "muted" not in ctx.attrs and "controls" not in ctx.attrs:
            self._add(
                ctx,
                "no-autoplay-audio",
                "<audio autoplay> without muted/controls",
            )

    def _check_object(self, ctx: _ElementContext) -> None:
        # Validated at close. Needs inner text or aria-label[ledby].
        pass

    def _check_role_img(self, ctx: _ElementContext) -> None:
        # Generic role="img" check (not specific to <img>/<svg>)
        if ctx.tag in ("img", "svg"):
            return
        if ctx.attrs.get("role") == "img":
            if not (ctx.attrs.get("aria-label") or ctx.attrs.get("aria-labelledby")):
                self._add(
                    ctx,
                    "role-img-alt",
                    'role="img" needs aria-label or aria-labelledby',
                )

    def _check_svg(self, ctx: _ElementContext) -> None:
        # Resolved at close. If role="img", needs <title> child or aria-label.
        pass

    # ---- close-time finalization -----------------------------------------

    def _finalize(self, ctx: _ElementContext) -> None:
        tag = ctx.tag
        a = ctx.attrs
        text = "".join(ctx.text_buf).strip()
        if tag == "title":
            self.has_title = True

        if tag == "button":
            if not (text or a.get("aria-label") or a.get("aria-labelledby")):
                self._add(ctx, "button-name", "<button> has no accessible name")

        if tag == "a":
            if "href" in a:
                if not (text or a.get("aria-label") or a.get("aria-labelledby")):
                    self._add(ctx, "link-name", "<a href> has no accessible name")

        if tag == "summary":
            if not (text or a.get("aria-label") or a.get("aria-labelledby")):
                self._add(ctx, "summary-name", "<summary> has no accessible name")

        if tag == "object":
            if not (text or a.get("aria-label") or a.get("aria-labelledby")):
                self._add(ctx, "object-alt", "<object> has no accessible name")

        if tag == "svg" and a.get("role") == "img":
            # Did we see a <title> child? Inspect text_buf. Close events
            # for descendants flush their text into our buffer too.
            # Simpler check: text content includes a non-empty string OR aria-label.
            has_label = bool(a.get("aria-label") or a.get("aria-labelledby"))
            # We can't perfectly detect <title> from raw text alone, so we
            # require the explicit aria-label or a title-tag-shaped substring.
            has_title_child = "<title" in "".join(ctx.text_buf).lower() or bool(text)
            if not (has_label or has_title_child):
                self._add(
                    ctx,
                    "svg-img-alt",
                    'role="img" SVG needs <title> child or aria-label',
                )

    # ---- finalization across the document --------------------------------

    def finalize_document(self) -> None:
        for ctx in self.form_fields:
            a = ctx.attrs
            id_ = a.get("id", "")
            named = bool(
                a.get("aria-label")
                or a.get("aria-labelledby")
                or (id_ and id_ in self.label_for_targets)
            )
            if not named:
                self._add(ctx, "label", f"<{ctx.tag}> has no associated label")
        if self.html_seen and not self.has_html_lang[0]:
            pass  # already reported in _check_html
        if not self.has_title:
            # Use the body position if available, else (1,0).
            line, col = self.body_pos if self.body_pos != (0, 0) else (1, 0)
            self.findings.append(
                Finding(
                    rule="document-title",
                    impact=IMPACT["document-title"],
                    line=line,
                    col=col,
                    element="title",
                    message="document is missing a non-empty <title>",
                )
            )
        for token, line, col in self.id_refs:
            if token not in self.ids_seen:
                self.findings.append(
                    Finding(
                        rule="duplicate-id-aria",
                        impact=IMPACT["duplicate-id-aria"],
                        line=line,
                        col=col,
                        element="(id reference)",
                        message=f"aria reference points to non-existent id \"{token}\"",
                    )
                )
        for id_, count in self.ids_seen.items():
            if count > 1:
                self.findings.append(
                    Finding(
                        rule="duplicate-id-aria",
                        impact=IMPACT["duplicate-id-aria"],
                        line=0,
                        col=0,
                        element="(duplicate id)",
                        message=f"id \"{id_}\" appears {count} times",
                    )
                )


_VOID_ELEMENTS = frozenset(
    "area base br col embed hr img input link meta param source track wbr".split()
)


# -- Driver -----------------------------------------------------------------


def audit(html: str, file: str = "") -> list[Finding]:
    p = A11yHTMLParser()
    p.feed(html)
    p.close()
    p.finalize_document()
    for f in p.findings:
        f.file = file
    return p.findings


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("files", nargs="*", help="HTML files; if omitted, read stdin")
    p.add_argument("--human", action="store_true", help="Human-readable output")
    p.add_argument(
        "--fail-on",
        default="any",
        choices=["any", "minor", "moderate", "serious", "critical"],
        help='Exit non-zero if findings reach this impact (default: any).',
    )
    args = p.parse_args(argv)

    sources: list[tuple[str, str]] = []
    if args.files:
        for path in args.files:
            with open(path, encoding="utf-8") as fh:
                sources.append((path, fh.read()))
    else:
        sources.append(("(stdin)", sys.stdin.read()))

    all_findings: list[Finding] = []
    for path, html in sources:
        all_findings.extend(audit(html, file=path))

    if args.human:
        if not all_findings:
            print("ok: no static a11y findings")
        else:
            for f in all_findings:
                print(
                    f"{f.file}:{f.line}:{f.col} [{f.impact}] {f.rule}: {f.message}"
                )
            print(f"\n{len(all_findings)} finding(s)")
    else:
        print(json.dumps([asdict(f) for f in all_findings], indent=2))

    return _exit_code(all_findings, args.fail_on)


_IMPACT_ORDER = ["minor", "moderate", "serious", "critical"]


def _exit_code(findings: list[Finding], fail_on: str) -> int:
    if not findings:
        return 0
    if fail_on == "any":
        return 1
    threshold = _IMPACT_ORDER.index(fail_on)
    for f in findings:
        if f.impact in _IMPACT_ORDER and _IMPACT_ORDER.index(f.impact) >= threshold:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
