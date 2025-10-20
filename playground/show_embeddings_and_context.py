"""
Simple script to show:
1. Element text representations (what gets embedded)
2. LLM context (what gets sent to LLM for query resolution)

Run: python show_embeddings_and_context.py
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), '../src')))

from natural_selector import Session
from natural_selector.integrations import SentenceTransformerEmbedder
from natural_selector._internal.page_index import PageIndex
from natural_selector._internal.retriever import search_elements
from natural_selector.interfaces import LLM


# Dummy LLM (not used in this demo)
class DummyLLM(LLM):
    def generate(self, query: str, context: str, system_prompt: str = "") -> str:
        return "dummy"


# Simple HTML
HTML = """
<html>
<body>
    <nav role="navigation">
        <a href="/">Home</a>
        <a href="/about">About</a>
    </nav>
    <div class="search">
        <input type="text" placeholder="Search" aria-label="Search input" />
        <button type="submit">Search</button>
        <button type="button">Cancel</button>
    </div>
    <p>Welcome to our site</p>
</body>
</html>
"""


def main():
    print("=" * 80)
    print("ELEMENT EMBEDDINGS & LLM CONTEXT")
    print("=" * 80)

    # Create session (no API key needed for this demo)
    session = Session(
        llm=DummyLLM(),  # Not used in this demo
        embedder=SentenceTransformerEmbedder(),
        top_k=3
    )

    # Create page
    page = session.create_page_from_html(HTML)
    print(f"\nCreated page with {len(page._id_mapping)} elements")

    # =========================================================================
    # PART 1: Show element text representations (what gets embedded)
    # =========================================================================
    print("\n" + "=" * 80)
    print("PART 1: ELEMENT TEXT REPRESENTATIONS (What gets embedded)")
    print("=" * 80)

    # Show first 5 elements
    print("\nShowing first 5 elements...\n")
    for i, (element_id, node) in enumerate(list(page._id_mapping.items())[:5]):
        text_repr = PageIndex._generate_element_repr(node, element_id, page._id_mapping)

        print(f"{'=' * 60}")
        print(f"Element #{i+1}: {element_id}")
        print(f"{'=' * 60}")
        print(text_repr)
        print()

    # =========================================================================
    # PART 2: Show LLM context (what gets sent to LLM)
    # =========================================================================
    print("\n" + "=" * 80)
    print("PART 2: LLM CONTEXT (What gets sent to OpenAI)")
    print("=" * 80)

    # Build index (embeds all elements)
    print("\nBuilding index (embedding elements)...")
    index = PageIndex.from_node_tree(
        root=page._root,
        id_mapping=page._id_mapping,
        embedder=session.embedder,
        llm=session.llm
    )
    print(f"✓ Indexed {len(index.elements)} elements")

    # Simulate a query
    query = "search button"
    print(f"\nQuery: '{query}'")

    # Step 1: Vector search (get top 3 elements)
    print(f"\n[Step 1] Vector search - retrieving top 3 elements...")
    top_elements = search_elements(
        query_text=query,
        elements=index.elements,
        embedder=session.embedder,
        top_k=3
    )

    print(f"✓ Retrieved {len(top_elements)} elements")
    for i, (element, score) in enumerate(top_elements, 1):
        print(f"  {i}. {element.element_id} (similarity: {score:.4f})")

    # Step 2: Build LLM context (like PageIndex.query() does)
    print(f"\n[Step 2] Building LLM context from retrieved elements...")

    context_parts = []
    for i, (element, score) in enumerate(top_elements):
        context_parts.append(f"## Element {i+1} (relevance: {score:.2f})")
        context_parts.append(f"ID: {element.element_id}")
        context_parts.append(element.text_repr)
        context_parts.append("")

    context = "\n".join(context_parts)

    # System prompt
    system_prompt = """You are a browser automation assistant. Given webpage elements and a user query, identify the relevant element ID.

The context shows element details with IDs like:
- button-1, div-2, input-3, etc.

IMPORTANT: Only return the element ID(s), nothing else.
- For single element: just "button-1"
- For multiple elements: "button-1, input-2, div-3"
- If not found: "NOT_FOUND"

Do not include explanations, just the ID."""

    # Show complete LLM input
    print("\n" + "=" * 80)
    print("COMPLETE LLM INPUT")
    print("=" * 80)

    print("\n" + "-" * 80)
    print("SYSTEM PROMPT:")
    print("-" * 80)
    print(system_prompt)

    print("\n" + "-" * 80)
    print("USER MESSAGE:")
    print("-" * 80)
    user_message = f"Webpage Context:\n{context}\n\nQuery: {query}"
    print(user_message)

    print("\n" + "=" * 80)
    print("END OF LLM INPUT")
    print("=" * 80)

    # Show token count estimate
    print(f"\nEstimated input size:")
    print(f"  System prompt: ~{len(system_prompt.split())} words")
    print(f"  User message: ~{len(user_message.split())} words")
    print(f"  Total: ~{len(system_prompt.split()) + len(user_message.split())} words")

    print("\n✅ Done!")


if __name__ == "__main__":
    main()
