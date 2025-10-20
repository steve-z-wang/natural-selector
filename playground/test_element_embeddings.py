"""
Test script for element-based embeddings (new architecture).

Tests the migration from chunk-based to element-based embeddings:
1. Session creates Page from HTML
2. Page generates semantic IDs for all elements
3. PageIndex creates text representations for each element
4. Elements are embedded and indexed
5. Query retrieves relevant elements via vector search + LLM

Can be run directly: python test_element_embeddings.py
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), '../src')))

from natural_selector import Session
from natural_selector.integrations import OpenAILLM, SentenceTransformerEmbedder
from natural_selector._internal.page_index import PageIndex


# Sample HTML for testing
SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
</head>
<body>
    <nav role="navigation">
        <a href="/">Home</a>
        <a href="/about">About</a>
        <a href="/contact">Contact</a>
    </nav>

    <main>
        <h1>Welcome to our site</h1>

        <div class="search-section">
            <label for="search-input">Search</label>
            <input
                id="search-input"
                type="text"
                placeholder="Enter search query"
                aria-label="Search input"
            />
            <button type="submit" aria-label="Search">Search</button>
        </div>

        <div class="login-section">
            <h2>Login</h2>
            <form>
                <label for="email">Email</label>
                <input
                    id="email"
                    type="email"
                    placeholder="Enter your email"
                    name="email"
                />

                <label for="password">Password</label>
                <input
                    id="password"
                    type="password"
                    placeholder="Enter your password"
                    name="password"
                />

                <button type="submit">Sign In</button>
                <button type="button">Cancel</button>
            </form>
        </div>

        <div class="content">
            <p>This is a test page for natural-selector's element-based embeddings.</p>
            <ul role="list">
                <li>Feature 1: Natural language element selection</li>
                <li>Feature 2: Sibling context awareness</li>
                <li>Feature 3: Path-based disambiguation</li>
            </ul>
        </div>
    </main>

    <footer>
        <p>Copyright 2024</p>
        <a href="/privacy">Privacy Policy</a>
        <a href="/terms">Terms of Service</a>
    </footer>
</body>
</html>
"""


def test_session_and_page_creation():
    """Test Session -> Page creation with element-based approach."""
    print("=" * 80)
    print("TEST 1: Session and Page Creation")
    print("=" * 80)

    # Note: We're using SentenceTransformerEmbedder (no API key needed)
    session = Session(
        llm=OpenAILLM(api_key=os.getenv("OPENAI_API_KEY", "dummy")),  # LLM not used in this test
        embedder=SentenceTransformerEmbedder(),
        top_k=5
    )

    print("\n[1] Creating page from HTML...")
    page = session.create_page_from_html(SAMPLE_HTML)
    print(f"✓ Page created: {page}")

    print(f"\n[2] Analyzing page structure...")
    print(f"  Total elements: {len(page._id_mapping)}")
    print(f"  Sample element IDs:")
    for i, element_id in enumerate(list(page._id_mapping.keys())[:10]):
        print(f"    {i+1}. {element_id}")

    return session, page


def test_element_representation():
    """Test element text representation generation."""
    print("\n" + "=" * 80)
    print("TEST 2: Element Text Representation")
    print("=" * 80)

    session, page = test_session_and_page_creation()

    print("\n[1] Generating text representations for sample elements...")

    # Find some interesting elements to show
    sample_ids = []
    for element_id in page._id_mapping.keys():
        # Get buttons, inputs, links
        if any(tag in element_id for tag in ['button-', 'input-', 'a-', 'h1-']):
            sample_ids.append(element_id)
            if len(sample_ids) >= 5:
                break

    for element_id in sample_ids:
        node = page._id_mapping[element_id]
        text_repr = PageIndex._generate_element_repr(node, element_id, page._id_mapping)

        print(f"\n{'=' * 60}")
        print(f"Element: {element_id}")
        print(f"{'=' * 60}")
        print(text_repr)

    return session, page


def test_page_index_creation():
    """Test PageIndex creation with element embeddings."""
    print("\n" + "=" * 80)
    print("TEST 3: PageIndex Creation with Element Embeddings")
    print("=" * 80)

    session, page = test_session_and_page_creation()

    print("\n[1] Building PageIndex (this will embed all elements)...")
    print("  Note: First run downloads sentence-transformers model (~90MB)")

    # This triggers lazy index building
    index = PageIndex.from_node_tree(
        root=page._root,
        id_mapping=page._id_mapping,
        embedder=session.embedder,
        llm=session.llm
    )

    print(f"✓ PageIndex built: {index}")
    print(f"  Total elements embedded: {len(index.elements)}")

    # Check embeddings
    if index.elements:
        sample_element = index.elements[0]
        print(f"\n[2] Sample element data:")
        print(f"  Element ID: {sample_element.element_id}")
        print(f"  Text repr length: {len(sample_element.text_repr)} chars")
        print(f"  Embedding shape: {len(sample_element.embedding) if sample_element.embedding else 'None'}")
        print(f"\n  Text representation:")
        print(f"  {'-' * 60}")
        print(f"  {sample_element.text_repr}")

    return session, page, index


def test_vector_search():
    """Test vector search for elements."""
    print("\n" + "=" * 80)
    print("TEST 4: Vector Search (No LLM)")
    print("=" * 80)

    session, page, index = test_page_index_creation()

    # Test queries
    queries = [
        "search button",
        "email input field",
        "sign in button",
        "navigation links",
        "password input"
    ]

    print("\n[1] Testing vector search for various queries...")

    from natural_selector._internal.retriever import search_elements

    for query in queries:
        print(f"\n{'=' * 60}")
        print(f"Query: '{query}'")
        print(f"{'=' * 60}")

        # Get top 3 elements
        results = search_elements(
            query_text=query,
            elements=index.elements,
            embedder=session.embedder,
            top_k=3
        )

        for i, (element, score) in enumerate(results, 1):
            print(f"\n  Result {i} (similarity: {score:.4f})")
            print(f"  Element ID: {element.element_id}")
            print(f"  Text representation (preview):")
            preview = element.text_repr[:200].replace('\n', '\n    ')
            print(f"    {preview}...")


def test_full_query_with_llm():
    """Test full query pipeline with LLM (requires API key)."""
    print("\n" + "=" * 80)
    print("TEST 5: Full Query with LLM")
    print("=" * 80)

    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\n⚠️  Skipping LLM test - OPENAI_API_KEY not set")
        print("  Set environment variable to test full query pipeline:")
        print("  export OPENAI_API_KEY='sk-...'")
        return

    # Create session with real LLM
    session = Session(
        llm=OpenAILLM(api_key=api_key),
        embedder=SentenceTransformerEmbedder(),
        top_k=5
    )

    page = session.create_page_from_html(SAMPLE_HTML)
    print(f"✓ Page created: {page}")

    # Test queries
    queries = [
        "search button",
        "email input",
        "sign in button",
    ]

    print("\n[1] Testing full query pipeline (vector search + LLM)...")

    for query in queries:
        print(f"\n{'=' * 60}")
        print(f"Query: '{query}'")
        print(f"{'=' * 60}")

        # Use Page.select() which triggers the full pipeline
        results = page.select(query, top_k=5)

        if results:
            print(f"  Found {len(results)} element(s):")
            for element in results:
                print(f"\n  {element}")
                print(f"    Tag: {element.tag}")
                print(f"    Text: {element.text}")
                print(f"    Attributes: {element.attributes}")
                print(f"    XPath: {element.to_xpath()}")
        else:
            print("  No elements found")


def test_formatted_output():
    """Test formatted page output."""
    print("\n" + "=" * 80)
    print("TEST 6: Formatted Page Output")
    print("=" * 80)

    session, page = test_session_and_page_creation()

    print("\n[1] Markdown format:")
    print("=" * 60)
    markdown = page.get_formatted_page(format="markdown")
    # Show first 1000 chars
    print(markdown[:1000])
    if len(markdown) > 1000:
        print(f"\n... ({len(markdown) - 1000} more characters)")

    print("\n[2] JSON format (preview):")
    print("=" * 60)
    import json
    json_str = page.get_formatted_page(format="json")
    json_obj = json.loads(json_str)
    print(f"  Total elements: {json_obj['total_elements']}")
    print(f"  Root tag: {json_obj['root']['tag']}")
    print(f"  Root semantic_id: {json_obj['root']['semantic_id']}")


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("NATURAL-SELECTOR: ELEMENT-BASED EMBEDDINGS TEST SUITE")
    print("=" * 80)
    print("\nThis test suite validates the new element-based embedding architecture.")
    print("Tests run in order, building on previous test results.\n")

    try:
        # Test 1: Basic creation
        test_session_and_page_creation()

        # Test 2: Element representations
        test_element_representation()

        # Test 3: Index creation and embeddings
        test_page_index_creation()

        # Test 4: Vector search
        test_vector_search()

        # Test 5: Full query (requires API key)
        test_full_query_with_llm()

        # Test 6: Formatted output
        test_formatted_output()

        print("\n" + "=" * 80)
        print("ALL TESTS COMPLETED SUCCESSFULLY! ✅")
        print("=" * 80)

    except Exception as e:
        print("\n" + "=" * 80)
        print(f"TEST FAILED: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
