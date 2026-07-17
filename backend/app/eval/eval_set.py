"""The RAG evaluation set — questions with what a good retrieval should surface.

This is the yardstick for "did a change help?". Run it before and after a retrieval/chunking
tweak (`make eval`) and watch keyword-hit-rate, MRR, and routing accuracy move.

HOW TO TUNE (do this against YOUR ingested manual):
- `keywords`  : lowercase terms; a retrieved chunk counts as a hit if it contains ANY of them.
                Start broad (domain words), then tighten to the exact page's distinctive tokens.
- `pages`     : optional 1-based page numbers the answer lives on; if set, page-hit is also scored.
- `source`    : "internal" for questions the manual should cover, "web" for clearly out-of-scope
                ones (validates internal-first routing / the sufficiency gate), "none" for refuse.
- `lang`      : "en" | "el" — keep a Greek subset so cross-lingual retrieval stays honest.

The seeded items use domain-generic keywords so the harness runs meaningfully out of the box;
replace them with the distinctive tokens of your manual's pages for a sharper signal.
"""

from dataclasses import dataclass, field


@dataclass
class EvalItem:
    question: str
    source: str  # "internal" | "web" | "none"
    keywords: list[str] = field(default_factory=list)
    pages: list[int] = field(default_factory=list)
    lang: str = "en"


EVAL_SET: list[EvalItem] = [
    # --- Internal: should be answered from the manual (tune keywords/pages to your PDF) ---
    EvalItem(
        "What safety precautions apply before servicing the machine?",
        source="internal",
        keywords=["safety", "power", "isolate", "warning"],
    ),
    EvalItem(
        "How do I service the drum?",
        source="internal",
        keywords=["drum", "bearing", "belt", "motor"],
    ),
    EvalItem(
        "The machine won't heat up — what should I check?",
        source="internal",
        keywords=["heating", "temperature", "steam", "element", "thermostat"],
    ),
    EvalItem(
        "How is the water inlet / drain valve maintained?",
        source="internal",
        keywords=["valve", "water", "drain", "inlet"],
    ),
    EvalItem(
        "What routine maintenance is recommended?",
        source="internal",
        keywords=["maintenance", "clean", "inspect", "lubricat"],
    ),
    EvalItem(
        "What are the electrical connection requirements?",
        source="internal",
        keywords=["electrical", "voltage", "power", "supply", "connection"],
    ),
    EvalItem(
        "How do I handle an error or fault code?",
        source="internal",
        keywords=["error", "fault", "code", "alarm"],
    ),
    # --- Internal, Greek: cross-lingual retrieval over the (English) manual ---
    EvalItem(
        "Ποιες προφυλάξεις ασφαλείας ισχύουν πριν το σέρβις;",
        source="internal",
        keywords=["safety", "power", "isolate", "warning"],
        lang="el",
    ),
    EvalItem(
        "Το μηχάνημα δεν ζεσταίνεται, τι να ελέγξω;",
        source="internal",
        keywords=["heating", "temperature", "steam", "element"],
        lang="el",
    ),
    EvalItem(
        "Πώς συντηρώ τον κάδο;",
        source="internal",
        keywords=["drum", "bearing", "belt", "motor"],
        lang="el",
    ),
    # --- Out of scope: the library shouldn't cover these -> web fallback / not internal ---
    EvalItem("Who won the FIFA World Cup in 2018?", source="web", keywords=["france"]),
    EvalItem("What's the capital of Australia?", source="web", keywords=["canberra"]),
    EvalItem("How do I bake a chocolate cake?", source="web", keywords=["flour", "sugar", "oven"]),
]
