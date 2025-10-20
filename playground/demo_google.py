"""
Demo: Natural Selector with Google.com using Playwright

Shows element-based embeddings and vector search on a real website.

Run: python demo_google.py
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), '../src')))

from playwright.async_api import async_playwright
from natural_selector import Session
from natural_selector.integrations import SentenceTransformerEmbedder
from natural_selector.utils import capture_snapshot
from natural_selector._internal.page_index import PageIndex
from natural_selector._internal.retriever import search_elements
from natural_selector.interfaces import LLM


# Dummy LLM (not used for vector search demo)
class DummyLLM(LLM):
    def generate(self, query: str, context: str, system_prompt: str = "") -> str:
        return "dummy"


async def main():
    print("=" * 80)
    print("NATURAL SELECTOR DEMO - Google.com")
    print("=" * 80)

    # =========================================================================
    # STEP 1: Capture Google.com with Playwright
    # =========================================================================
    print("\n[1] Launching browser and capturing Google.com...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("  Navigating to google.com...")
        await page.goto('https://www.google.com', wait_until='networkidle')

        print("  Waiting for page to stabilize...")
        await asyncio.sleep(3)

        print("  Capturing CDP snapshot...")
        snapshot = await capture_snapshot(page)

        await browser.close()
        print("  ✓ Snapshot captured")

    print(f"\n  Snapshot info:")
    print(f"    Documents: {len(snapshot.get('documents', []))}")
    print(f"    Strings: {len(snapshot.get('strings', []))}")

    # =========================================================================
    # STEP 2: Create Session and Page
    # =========================================================================
    print("\n[2] Creating session and page...")

    session = Session(
        llm=DummyLLM(),
        embedder=SentenceTransformerEmbedder(),
        top_k=5
    )

    page_obj = session.create_page_from_cdp(snapshot)
    print(f"  ✓ Page created: {page_obj}")
    print(f"    Total elements after filtering: {len(page_obj._id_mapping)}")

    # =========================================================================
    # STEP 3: Show Sample Element IDs
    # =========================================================================
    print("\n[3] Sample element IDs (first 20):")
    for i, element_id in enumerate(list(page_obj._id_mapping.keys())[:20], 1):
        print(f"  {i:2d}. {element_id}")

    # =========================================================================
    # STEP 4: Show Element Text Representations
    # =========================================================================
    print("\n[4] Sample element text representations:")
    print("    (This is what gets embedded)\n")

    # Find interesting elements
    interesting = []
    for element_id in page_obj._id_mapping.keys():
        if any(tag in element_id for tag in ['button-', 'input-', 'a-', 'textarea-']):
            interesting.append(element_id)
            if len(interesting) >= 3:
                break

    for element_id in interesting:
        node = page_obj._id_mapping[element_id]
        text_repr = PageIndex._generate_element_repr(node, element_id, page_obj._id_mapping)

        print(f"{'='*70}")
        print(f"Element: {element_id}")
        print(f"{'='*70}")
        print(text_repr)
        print()

    # =========================================================================
    # STEP 5: Build Index (Embed All Elements)
    # =========================================================================
    print("\n[5] Building index (embedding all elements)...")
    print("    Note: First run downloads sentence-transformers model (~90MB)")

    index = PageIndex.from_node_tree(
        root=page_obj._root,
        id_mapping=page_obj._id_mapping,
        embedder=session.embedder,
        llm=session.llm
    )

    print(f"  ✓ Indexed {len(index.elements)} elements")
    if index.elements:
        print(f"    Embedding dimension: {len(index.elements[0].embedding)}")

    # =========================================================================
    # STEP 6: Test Vector Search
    # =========================================================================
    print("\n[6] Testing vector search queries:")

    queries = [
        "search button",
        "search input",
        "gmail link",
        "images link",
    ]

    for query in queries:
        print(f"\n{'='*70}")
        print(f"Query: '{query}'")
        print(f"{'='*70}")

        results = search_elements(
            query_text=query,
            elements=index.elements,
            embedder=session.embedder,
            top_k=3
        )

        for i, (element, score) in enumerate(results, 1):
            print(f"\n  Result {i} (similarity: {score:.4f})")
            print(f"  Element ID: {element.element_id}")
            print(f"  Text representation (first 3 lines):")
            lines = element.text_repr.split('\n')[:3]
            for line in lines:
                print(f"    {line}")
            if len(element.text_repr.split('\n')) > 3:
                print(f"    ...")

    # =========================================================================
    # STEP 7: Show LLM Context
    # =========================================================================
    print("\n\n" + "="*80)
    print("BONUS: LLM Context for 'search button'")
    print("="*80)

    query = "search button"
    top_elements = search_elements(
        query_text=query,
        elements=index.elements,
        embedder=session.embedder,
        top_k=3
    )

    # Build context
    context_parts = []
    for i, (element, score) in enumerate(top_elements):
        context_parts.append(f"## Element {i+1} (relevance: {score:.2f})")
        context_parts.append(f"ID: {element.element_id}")
        context_parts.append(element.text_repr)
        context_parts.append("")

    context = "\n".join(context_parts)

    print("\nThis is what would be sent to the LLM:\n")
    print("-" * 70)
    print(context[:500])  # Show first 500 chars
    if len(context) > 500:
        print(f"\n... ({len(context) - 500} more characters)")
    print("-" * 70)

    print("\n✅ Demo complete!")
    print("\nTo use with real LLM:")
    print("  1. Install: pip install openai")
    print("  2. Set API key: export OPENAI_API_KEY='sk-...'")
    print("  3. Update session to use OpenAILLM")


if __name__ == "__main__":
    asyncio.run(main())
