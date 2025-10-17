# %% [markdown]
# # Component Output Generation
# Generate intermediate outputs for testing individual components:
# 1. full-ir.json - Complete DomIR from CDP
# 2. semantic-ir.json - SemanticIR after filters
# 3. chunks.json - Chunked markdown with tokens
# 4. llm-context.txt - LLM context with token counts

# %%
import sys
import os
import asyncio
import json
import tiktoken

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), '../src')))

from playwright.async_api import async_playwright
from natural_selector._internal.parsers.cdp_parser import parse_cdp_snapshot
from natural_selector._internal.filters import visibility_pass, semantic_pass
from natural_selector._internal.index.chunker import create_chunks
from natural_selector._internal.index.embedder import embed_chunks
from natural_selector.integrations import SentenceTransformerEmbedder

# %% [markdown]
# ## Step 1: Launch Browser

# %%
print("="*80)
print("GENERATING COMPONENT OUTPUTS")
print("="*80)

print("\n[1] Launching browser...")
playwright = await async_playwright().start()
browser = await playwright.chromium.launch(headless=False)
page = await browser.new_page()
print(f"✓ Browser launched")

# %% [markdown]
# ## Step 2: Capture CDP Snapshot

# %%
print("\n[2] Capturing CDP snapshot from Google...")
url = 'https://www.google.com'
await page.goto(url, wait_until='networkidle')

# Wait 5 seconds for page to stabilize
print("  Waiting 5 seconds for page to stabilize...")
await asyncio.sleep(5)

cdp = await page.context.new_cdp_session(page)
cdp_snapshot = await cdp.send('DOMSnapshot.captureSnapshot', {
    'computedStyles': ['display', 'visibility', 'opacity'],
    'includePaintOrder': True,
    'includeDOMRects': True
})

print(f"✓ Captured snapshot")
print(f"  URL: {url}")
print(f"  Documents: {len(cdp_snapshot.get('documents', []))}")
print(f"  Strings: {len(cdp_snapshot.get('strings', []))}")

# %% [markdown]
# ## Step 3: Build DomIR (full-ir)

# %%
print("\n[3] Building DomIR (full-ir)...")
dom_ir = parse_cdp_snapshot(cdp_snapshot)
print(f"✓ DomIR created")
print(f"  Total nodes: {len(dom_ir.all_element_nodes())}")

# Serialize DomIR to JSON
full_ir_dict = dom_ir.to_dict()
with open('full-ir.json', 'w') as f:
    json.dump(full_ir_dict, f, indent=2)
print(f"✓ Saved to: full-ir.json")

# %% [markdown]
# ## Step 3.5: Debug - Check specific elements

# %%
# Debug: Find Gmail link in full IR
print("\n[3.5] Debugging: Looking for Gmail/Images links...")
from natural_selector._internal.ir.dom_ir import DomElement, DomText

def find_link_elements(dom_ir, search_text):
    """Find <a> tags with specific text as direct children."""
    results = []
    for node in dom_ir.all_element_nodes():
        elem = node.data
        if isinstance(elem, DomElement) and elem.tag == 'a':
            # Get direct text children only
            direct_text = []
            for child in node.children:
                if isinstance(child.data, DomText):
                    direct_text.append(child.data.text)

            combined_text = ''.join(direct_text).strip()

            # Check if this link contains our search text
            if search_text.lower() in combined_text.lower():
                results.append({
                    'tag': elem.tag,
                    'text': combined_text,
                    'bounds': f"w={elem.bounds.width}, h={elem.bounds.height}" if elem.bounds else "no bounds",
                    'styles': elem.styles,
                    'aria-label': elem.attributes.get('aria-label', 'N/A'),
                    'href': elem.attributes.get('href', 'N/A'),
                    'class': elem.attributes.get('class', 'N/A')
                })
    return results

gmail_links = find_link_elements(dom_ir, "Gmail")
images_links = find_link_elements(dom_ir, "Images")

print(f"  Gmail <a> links found in full-ir: {len(gmail_links)}")
for elem in gmail_links[:3]:  # Show first 3
    print(f"    - {elem['tag']}: '{elem['text']}', bounds={elem['bounds']}")
    print(f"      aria-label={elem['aria-label']}, class={elem['class']}")

print(f"  Images <a> links found in full-ir: {len(images_links)}")
for elem in images_links[:3]:  # Show first 3
    print(f"    - {elem['tag']}: '{elem['text']}', bounds={elem['bounds']}")
    print(f"      aria-label={elem['aria-label']}, class={elem['class']}")

# %% [markdown]
# ## Step 3.6: Debug - Check "Sign in" popup elements

# %%
print("\n[3.6] Debugging: Looking for 'Sign in' popup elements...")

def find_text_elements(dom_ir, search_text):
    """Find any elements containing specific text."""
    results = []
    for node in dom_ir.all_element_nodes():
        elem = node.data
        if isinstance(elem, DomElement):
            # Get all text descendants
            all_text = []
            def collect_text(n):
                for child in n.children:
                    if isinstance(child.data, DomText):
                        all_text.append(child.data.text)
                    elif isinstance(child.data, DomElement):
                        collect_text(child)
            collect_text(node)

            combined_text = ''.join(all_text).strip()

            # Check if this element contains our search text
            if search_text.lower() in combined_text.lower():
                results.append({
                    'tag': elem.tag,
                    'text': combined_text[:100] + ('...' if len(combined_text) > 100 else ''),  # Truncate long text
                    'bounds': f"w={elem.bounds.width:.1f}, h={elem.bounds.height:.1f}" if elem.bounds else "no bounds",
                    'styles': elem.styles,
                    'class': elem.attributes.get('class', 'N/A'),
                    'jsname': elem.attributes.get('jsname', 'N/A')
                })
    return results

signin_elements = find_text_elements(dom_ir, "Sign in")
print(f"  Elements containing 'Sign in' found in full-ir: {len(signin_elements)}")
for i, elem in enumerate(signin_elements[:5]):  # Show first 5
    print(f"    [{i}] {elem['tag']}: text='{elem['text']}'")
    print(f"        bounds={elem['bounds']}, jsname={elem['jsname']}")
    print(f"        styles={elem['styles']}")

# Search for popup-specific text
print(f"\n  Looking for popup dialog with 'Sign in to Google'...")
popup_elements = find_text_elements(dom_ir, "Sign in to Google")
print(f"  Elements containing 'Sign in to Google' found in full-ir: {len(popup_elements)}")
for i, elem in enumerate(popup_elements[:5]):
    print(f"    [{i}] {elem['tag']}: text='{elem['text']}'")
    print(f"        bounds={elem['bounds']}, jsname={elem['jsname']}")
    print(f"        styles={elem['styles']}")

print(f"\n  Looking for 'Stay signed out' button...")
stay_out_elements = find_text_elements(dom_ir, "Stay signed out")
print(f"  Elements containing 'Stay signed out' found in full-ir: {len(stay_out_elements)}")
for i, elem in enumerate(stay_out_elements[:3]):
    print(f"    [{i}] {elem['tag']}: text='{elem['text']}'")
    print(f"        bounds={elem['bounds']}, jsname={elem['jsname']}")
    print(f"        styles={elem['styles']}")

# %% [markdown]
# ## Step 4: Apply Filters to Create SemanticIR

# %%
print("\n[4] Applying filters to create SemanticIR...")

# Visibility filter
print("  Applying visibility filter...")
visible_dom_ir = visibility_pass(dom_ir)
print(f"  ✓ Nodes after visibility: {len(visible_dom_ir.all_element_nodes())}")

# Debug: Check if Gmail/Images survived visibility filter
gmail_after_vis = find_link_elements(visible_dom_ir, "Gmail")
images_after_vis = find_link_elements(visible_dom_ir, "Images")
print(f"  Gmail links after visibility: {len(gmail_after_vis)}")
print(f"  Images links after visibility: {len(images_after_vis)}")

# Debug: Check if Sign in elements survived visibility filter
signin_after_vis = find_text_elements(visible_dom_ir, "Sign in")
print(f"  'Sign in' elements after visibility: {len(signin_after_vis)}")
if signin_after_vis:
    for i, elem in enumerate(signin_after_vis[:3]):
        print(f"    [{i}] {elem['tag']}: text='{elem['text']}'")
        print(f"        bounds={elem['bounds']}, jsname={elem['jsname']}")

# Check specifically for the popup dialog
popup_after_vis = find_text_elements(visible_dom_ir, "Sign in to Google")
print(f"  'Sign in to Google' popup after visibility: {len(popup_after_vis)}")
if popup_after_vis:
    for i, elem in enumerate(popup_after_vis[:5]):
        print(f"    [{i}] {elem['tag']}: bounds={elem['bounds']}, jsname={elem['jsname']}")
        print(f"        text='{elem['text']}'")

# Semantic filter - step by step to debug
print("  Applying semantic filter...")

# Import semantic passes
from natural_selector._internal.filters.semantic.convert import convert_to_semantic_pass
from natural_selector._internal.filters.semantic.filter_attributes import filter_by_attributes_pass
from natural_selector._internal.filters.semantic.filter_empty import filter_empty_nodes_pass
from natural_selector._internal.filters.semantic.collapse_wrappers import collapse_wrappers_pass
from natural_selector._internal.filters.semantic.generate_ids import generate_ids_pass
from natural_selector._internal.ir.semantic_ir import SemanticElement, SemanticIR

def count_links_in_semantic(root, search_text):
    """Count links in semantic tree."""
    count = 0
    def traverse(node):
        nonlocal count
        if isinstance(node.data, SemanticElement):
            if node.data.tag == 'a':
                # Check if any child has the text
                for child in node.children:
                    if hasattr(child.data, 'text') and search_text.lower() in child.data.text.lower():
                        count += 1
                        break
            for child in node.children:
                traverse(child)
    traverse(root)
    return count

def count_text_in_semantic(root, search_text):
    """Count any elements containing text in semantic tree."""
    count = 0
    def traverse(node):
        nonlocal count
        if isinstance(node.data, SemanticElement):
            # Collect all text from this node's descendants
            all_text = []
            def collect_text(n):
                for child in n.children:
                    if hasattr(child.data, 'text'):
                        all_text.append(child.data.text)
                    if isinstance(child.data, SemanticElement):
                        collect_text(child)
            collect_text(node)
            combined_text = ''.join(all_text).strip()
            if search_text.lower() in combined_text.lower():
                count += 1
            for child in node.children:
                traverse(child)
    traverse(root)
    return count

# Pass 0: Convert
root = convert_to_semantic_pass(visible_dom_ir.root)
gmail_count = count_links_in_semantic(root, "Gmail")
images_count = count_links_in_semantic(root, "Images")
signin_count = count_text_in_semantic(root, "Sign in")
popup_count = count_text_in_semantic(root, "Sign in to Google")
print(f"    After convert: Gmail={gmail_count}, Images={images_count}, Sign in={signin_count}, Popup={popup_count}")

# Pass 1: Filter attributes
# First, let's check what attributes the Gmail link has
def find_link_in_semantic(root, search_text):
    """Find a link and its parent in semantic tree."""
    result = []
    def traverse(node, parent=None):
        if isinstance(node.data, SemanticElement):
            if node.data.tag == 'a':
                # Check if any child has the text
                for child in node.children:
                    if hasattr(child.data, 'text') and search_text.lower() in child.data.text.lower():
                        parent_info = None
                        if parent:
                            parent_info = {
                                'tag': parent.data.tag,
                                'attrs': parent.data.semantic_attributes
                            }
                        result.append({
                            'tag': node.data.tag,
                            'attrs': node.data.semantic_attributes,
                            'parent': parent_info
                        })
                        break
            for child in node.children:
                traverse(child, node)
    traverse(root)
    return result

gmail_info = find_link_in_semantic(root, "Gmail")
if gmail_info:
    print(f"    Gmail link before filter_attributes:")
    print(f"      Link attrs: {gmail_info[0]['attrs']}")
    if gmail_info[0]['parent']:
        print(f"      Parent <{gmail_info[0]['parent']['tag']}> attrs: {gmail_info[0]['parent']['attrs']}")

root = filter_by_attributes_pass(root)
gmail_count = count_links_in_semantic(root, "Gmail")
images_count = count_links_in_semantic(root, "Images")
signin_count = count_text_in_semantic(root, "Sign in")
print(f"    After filter_attributes: Gmail={gmail_count}, Images={images_count}, Sign in={signin_count}")

# Pass 2: Filter empty
root = filter_empty_nodes_pass(root)
gmail_count = count_links_in_semantic(root, "Gmail")
images_count = count_links_in_semantic(root, "Images")
signin_count = count_text_in_semantic(root, "Sign in")
print(f"    After filter_empty: Gmail={gmail_count}, Images={images_count}, Sign in={signin_count}")

# Pass 3: Collapse wrappers
root = collapse_wrappers_pass(root)
gmail_count = count_links_in_semantic(root, "Gmail")
images_count = count_links_in_semantic(root, "Images")
signin_count = count_text_in_semantic(root, "Sign in")
print(f"    After collapse_wrappers: Gmail={gmail_count}, Images={images_count}, Sign in={signin_count}")

# Pass 4: Generate IDs
root, id_mapping = generate_ids_pass(root)

# Create SemanticIR
semantic_ir = SemanticIR(root, id_index=id_mapping)
print(f"  ✓ Nodes after semantic: {len(semantic_ir.all_element_nodes())}")

# Serialize SemanticIR to JSON
semantic_ir_dict = semantic_ir.to_dict()
with open('semantic-ir.json', 'w') as f:
    json.dump(semantic_ir_dict, f, indent=2)
print(f"✓ Saved to: semantic-ir.json")

# %% [markdown]
# ## Step 5: Create Chunks from SemanticIR

# %%
print("\n[5] Creating chunks from SemanticIR...")
chunks = create_chunks(
    semantic_ir,
    max_tokens=500,
    overlap_tokens=50
)
print(f"✓ Created {len(chunks)} chunks")

# Display chunk statistics
total_tokens = sum(c.tokens for c in chunks)
avg_tokens = total_tokens / len(chunks) if chunks else 0
print(f"  Total tokens: {total_tokens}")
print(f"  Avg tokens per chunk: {avg_tokens:.1f}")
print(f"  Min tokens: {min(c.tokens for c in chunks) if chunks else 0}")
print(f"  Max tokens: {max(c.tokens for c in chunks) if chunks else 0}")

# Serialize chunks to JSON
chunks_list = []
for i, chunk in enumerate(chunks):
    chunks_list.append({
        'chunk_id': i,
        'markdown': chunk.markdown,
        'tokens': chunk.tokens
    })

with open('chunks.json', 'w') as f:
    json.dump(chunks_list, f, indent=2)
print(f"✓ Saved to: chunks.json")

# %% [markdown]
# ## Step 6: Generate LLM Context (Simulated Retrieval)

# %%
print("\n[6] Generating LLM context (simulated retrieval)...")

# For demonstration, embed chunks and simulate a query
print("  Embedding chunks...")
embedder = SentenceTransformerEmbedder()
chunks = embed_chunks(chunks, embedder)
print(f"  ✓ Embedded {len(chunks)} chunks")

# Simulate retrieval: just take top 3 chunks for demonstration
print("  Simulating retrieval (top 3 chunks)...")
top_chunks = chunks[:3]

# Build LLM context exactly like PageIndex.query() and OpenAILLM.generate() does
query = "search button"

# Step 1: Build context from chunks (what PageIndex does)
chunk_context_parts = []
for i, chunk in enumerate(top_chunks):
    chunk_context_parts.append(f"## Context {i+1} (relevance: 0.95)")  # Mock relevance score
    chunk_context_parts.append(chunk.markdown)
    chunk_context_parts.append("")

chunk_context = "\n".join(chunk_context_parts)

# Step 2: Build system prompt (from PageIndex.query())
system_prompt = """You are a browser automation assistant. Given a webpage's semantic structure and a user query, identify the relevant element ID.

The context shows the webpage structure in markdown format with element IDs like:
- button-1, div-2, input-3, etc.

IMPORTANT: Only return the element ID(s), nothing else.
- For single element: just "button-1"
- For multiple elements: "button-1, input-2, div-3"
- If not found: "NOT_FOUND"

Do not include explanations, just the ID."""

# Step 3: Build user message (from OpenAILLM.generate())
user_message = f"Webpage Context:\n{chunk_context}\n\nQuery: {query}"

# Step 4: Format complete LLM input
context_parts = []
context_parts.append("=" * 80)
context_parts.append("COMPLETE LLM INPUT (Exactly what is sent to OpenAI)")
context_parts.append("=" * 80)
context_parts.append("")
context_parts.append("=" * 80)
context_parts.append("SYSTEM PROMPT:")
context_parts.append("=" * 80)
context_parts.append(system_prompt)
context_parts.append("")
context_parts.append("=" * 80)
context_parts.append("USER MESSAGE:")
context_parts.append("=" * 80)
context_parts.append(user_message)
context_parts.append("")

# Add token statistics
encoding = tiktoken.get_encoding("cl100k_base")
system_tokens = len(encoding.encode(system_prompt))
user_tokens = len(encoding.encode(user_message))
total_tokens = system_tokens + user_tokens

context_parts.append("=" * 80)
context_parts.append("TOKEN STATISTICS")
context_parts.append("=" * 80)
context_parts.append(f"System prompt tokens: {system_tokens}")
context_parts.append(f"User message tokens: {user_tokens}")
context_parts.append(f"Total input tokens: {total_tokens}")
context_parts.append(f"Chunks included: {len(top_chunks)}")
context_parts.append(f"Avg tokens per chunk: {sum(c.tokens for c in top_chunks) / len(top_chunks):.1f}")

context_output = "\n".join(context_parts)

with open('llm-context.txt', 'w') as f:
    f.write(context_output)
print(f"✓ Saved to: llm-context.txt")
print(f"  System prompt tokens: {system_tokens}")
print(f"  User message tokens: {user_tokens}")
print(f"  Total input tokens: {total_tokens}")
print(f"  Chunks included: {len(top_chunks)}")

# %% [markdown]
# ## Summary

# %%
print("\n" + "="*80)
print("GENERATION COMPLETE!")
print("="*80)
print("\nGenerated files:")
print("  1. full-ir.json       - Complete DomIR from CDP")
print("  2. semantic-ir.json   - SemanticIR after filters")
print("  3. chunks.json        - Chunked markdown with tokens")
print("  4. llm-context.txt    - LLM context with token counts")

# %% [markdown]
# ## Cleanup: Close Browser

# %%
print("\nClosing browser...")
await browser.close()
await playwright.stop()
print("✓ Browser closed")

# %%
