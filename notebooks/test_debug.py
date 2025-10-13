# %% [markdown]
# # Natural-Selector Debug Pipeline
#
# Simplified test to check every step of the pipeline

# %%
import sys
import os
import json

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), '../src')))

from playwright.async_api import async_playwright

# %% [markdown]
# ## STEP 1: Capture CDP Snapshot

# %%
async def get_snapshot(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url, wait_until='networkidle')

        cdp = await page.context.new_cdp_session(page)
        snapshot = await cdp.send('DOMSnapshot.captureSnapshot', {
            'computedStyles': ['display', 'visibility', 'opacity'],
            'includePaintOrder': True,
            'includeDOMRects': True
        })

        await browser.close()
        return snapshot

cdp_snapshot = await get_snapshot('https://www.google.com')
print("✓ Step 1: Captured CDP snapshot")
print(f"  Documents: {len(cdp_snapshot.get('documents', []))}")
print(f"  Strings: {len(cdp_snapshot.get('strings', []))}")

# %% [markdown]
# ## STEP 2: Parse to Full IR

# %%
from natural_selector._internal.parsers.cdp_parser import parse_cdp_snapshot

full_ir = parse_cdp_snapshot(cdp_snapshot)
print(f"\n✓ Step 2: Parsed to Full IR")
print(f"  Total nodes: {len(full_ir.all_element_nodes())}")
print(f"  Root tag: {full_ir.root.tag}")

# %% [markdown]
# ## STEP 3: Apply Visibility Filter

# %%
from natural_selector._internal.transforms import visibility_pass

visible_ir = visibility_pass(full_ir)
print(f"\n✓ Step 3: Applied visibility filter")
print(f"  Visible nodes: {len(visible_ir.all_element_nodes())}")
print(f"  Filtered out: {len(full_ir.all_element_nodes()) - len(visible_ir.all_element_nodes())} nodes")

# %% [markdown]
# ## STEP 4: Apply Semantic Filter

# %%
from natural_selector._internal.transforms import semantic_pass

semantic_ir = semantic_pass(visible_ir)
print(f"\n✓ Step 4: Applied semantic filter")
print(f"  Semantic nodes: {len(semantic_ir.all_element_nodes())}")
print(f"  Filtered out: {len(visible_ir.all_element_nodes()) - len(semantic_ir.all_element_nodes())} nodes")

# Show top tags
from collections import Counter
tags = [node.tag for node in semantic_ir.all_element_nodes()]
print(f"\n  Top 5 tags:")
for tag, count in Counter(tags).most_common(5):
    print(f"    {tag}: {count}")

# %% [markdown]
# ## STEP 5: Add Identifiers

# %%
from natural_selector._internal.transforms import add_identifiers_pass

semantic_ir_with_ids = add_identifiers_pass(semantic_ir)
print(f"\n✓ Step 5: Added identifiers")

# Show example IDs
examples = []
for node in semantic_ir_with_ids.all_element_nodes()[:5]:
    if node.tag_id:
        readable_id = f"{node.tag}-{node.tag_id}"
        examples.append(f"{readable_id} (uuid: {node.id[:8]}...)")

print(f"  Example IDs:")
for ex in examples:
    print(f"    {ex}")

# %% [markdown]
# ## STEP 6: Create ID Mapping

# %%
from natural_selector._internal.rag.markdown_serializer import serialize_to_markdown

markdown_text, id_mapping = serialize_to_markdown(semantic_ir_with_ids)
print(f"\n✓ Step 6: Created ID mapping")
print(f"  Total mappings: {len(id_mapping)}")
print(f"\n  Sample mappings:")
for i, (readable_id, uuid) in enumerate(list(id_mapping.items())[:5]):
    print(f"    {readable_id} → {uuid[:8]}...")

# %% [markdown]
# ## STEP 7: Chunk Markdown

# %%
from natural_selector._internal.rag.chunker import chunk_ir

chunks = chunk_ir(semantic_ir_with_ids, max_tokens=500, overlap_tokens=50)
print(f"\n✓ Step 7: Chunked markdown")
print(f"  Total chunks: {len(chunks)}")
print(f"  Avg tokens/chunk: {sum(c['tokens'] for c in chunks) / len(chunks):.1f}")

print(f"\n  First chunk preview:")
print(chunks[0]['markdown'][:200] + "...")

# %% [markdown]
# ## STEP 8: Generate Embeddings

# %%
from natural_selector._internal.rag.embedder import SentenceTransformerEmbedder, embed_chunks

embedder = SentenceTransformerEmbedder()
embedded_chunks = embed_chunks(chunks, embedder)

print(f"\n✓ Step 8: Generated embeddings")
print(f"  Embedding dimension: {embedded_chunks[0]['embedding_dim']}")
print(f"  Total embedded chunks: {len(embedded_chunks)}")

# %% [markdown]
# ## STEP 9: Query with Natural Language

# %%
from natural_selector._internal.rag.retriever import ChunkRetriever
from natural_selector.integrations import OpenAILLM

retriever = ChunkRetriever(embedded_chunks, embedder)
llm = OpenAILLM(model="gpt-4o")

# Test query
query = "search button"
print(f"\n✓ Step 9: Query - '{query}'")

# Retrieve chunks
results = retriever.query(query, top_k=3)
print(f"  Retrieved {len(results)} chunks")
for i, (chunk, score) in enumerate(results, 1):
    print(f"    Chunk {i} similarity: {score:.3f}")

# Show what's in top chunk
print(f"\n  Top chunk content:")
print(results[0][0]['markdown'][:300] + "...")

# %% [markdown]
# ## STEP 10: LLM Generate Element ID

# %%
from natural_selector._internal.rag.llm import answer_query

result = answer_query(query, retriever, llm, top_k=3)
element_id = result['response'].strip()

print(f"\n✓ Step 10: LLM generated element ID")
print(f"  Query: '{query}'")
print(f"  LLM Response: '{element_id}'")

# Check if element ID exists in mapping
if element_id in id_mapping:
    uuid = id_mapping[element_id]
    print(f"  ✓ Found in mapping: {element_id} → {uuid[:8]}...")
else:
    print(f"  ✗ NOT in mapping! Available IDs:")
    # Show similar IDs
    similar = [k for k in id_mapping.keys() if 'button' in k or 'search' in k]
    for sim_id in similar[:5]:
        print(f"      {sim_id}")

# %% [markdown]
# ## STEP 11: Generate XPath

# %%
from natural_selector._internal.selector import generate_xpath

if element_id in id_mapping:
    xpath = generate_xpath(element_id, id_mapping, full_ir)

    print(f"\n✓ Step 11: Generated XPath")
    print(f"  Element ID: {element_id}")
    print(f"  XPath: {xpath}")

    # Show the full node details
    uuid = id_mapping[element_id]
    node = full_ir.get_node_by_id(uuid)
    print(f"\n  Full node details:")
    print(f"    Tag: {node.tag}")
    print(f"    Attributes: {node.attributes}")
else:
    print(f"\n✗ Step 11: Cannot generate XPath")
    print(f"  Element ID '{element_id}' not found in mapping")

# %%
