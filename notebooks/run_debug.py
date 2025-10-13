#!/usr/bin/env python
"""Runnable version of test_debug.py"""

import sys
import os
import asyncio
from collections import Counter
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), '../src')))

from playwright.async_api import async_playwright
from natural_selector._internal.parsers.cdp_parser import parse_cdp_snapshot
from natural_selector._internal.transforms import visibility_pass, semantic_pass, add_identifiers_pass
from natural_selector._internal.rag.markdown_serializer import serialize_to_markdown
from natural_selector._internal.rag.chunker import chunk_ir
from natural_selector._internal.rag.embedder import SentenceTransformerEmbedder, embed_chunks
from natural_selector._internal.rag.retriever import ChunkRetriever
from natural_selector._internal.rag.llm import answer_query
from natural_selector._internal.selector import generate_xpath
from natural_selector.integrations import OpenAILLM


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


async def main():
    # STEP 1: Capture CDP Snapshot
    print("="*60)
    print("STEP 1: Capture CDP Snapshot")
    print("="*60)
    cdp_snapshot = await get_snapshot('https://www.google.com')
    print("✓ Captured CDP snapshot")
    print(f"  Documents: {len(cdp_snapshot.get('documents', []))}")
    print(f"  Strings: {len(cdp_snapshot.get('strings', []))}")

    # STEP 2: Parse to Full IR
    print("\n" + "="*60)
    print("STEP 2: Parse to Full IR")
    print("="*60)
    full_ir = parse_cdp_snapshot(cdp_snapshot)
    print(f"✓ Parsed to Full IR")
    print(f"  Total nodes: {len(full_ir.all_element_nodes())}")
    print(f"  Root tag: {full_ir.root.tag}")

    # STEP 3: Apply Visibility Filter
    print("\n" + "="*60)
    print("STEP 3: Apply Visibility Filter")
    print("="*60)
    visible_ir = visibility_pass(full_ir)
    print(f"✓ Applied visibility filter")
    print(f"  Visible nodes: {len(visible_ir.all_element_nodes())}")
    print(f"  Filtered out: {len(full_ir.all_element_nodes()) - len(visible_ir.all_element_nodes())} nodes")

    # STEP 4: Apply Semantic Filter
    print("\n" + "="*60)
    print("STEP 4: Apply Semantic Filter")
    print("="*60)
    semantic_ir = semantic_pass(visible_ir)
    print(f"✓ Applied semantic filter")
    print(f"  Semantic nodes: {len(semantic_ir.all_element_nodes())}")
    print(f"  Filtered out: {len(visible_ir.all_element_nodes()) - len(semantic_ir.all_element_nodes())} nodes")

    # Show top tags
    tags = [node.tag for node in semantic_ir.all_element_nodes()]
    print(f"\n  Top 5 tags:")
    for tag, count in Counter(tags).most_common(5):
        print(f"    {tag}: {count}")

    # STEP 5: Add Identifiers
    print("\n" + "="*60)
    print("STEP 5: Add Identifiers")
    print("="*60)
    semantic_ir_with_ids = add_identifiers_pass(semantic_ir)
    print(f"✓ Added identifiers")

    # Show example IDs
    examples = []
    for node in semantic_ir_with_ids.all_element_nodes()[:5]:
        if node.tag_id:
            readable_id = f"{node.tag}-{node.tag_id}"
            examples.append(f"{readable_id} (uuid: {node.id[:8]}...)")

    print(f"  Example IDs:")
    for ex in examples:
        print(f"    {ex}")

    # STEP 6: Create ID Mapping
    print("\n" + "="*60)
    print("STEP 6: Create ID Mapping")
    print("="*60)
    markdown_text, id_mapping = serialize_to_markdown(semantic_ir_with_ids)
    print(f"✓ Created ID mapping")
    print(f"  Total mappings: {len(id_mapping)}")
    print(f"\n  Sample mappings:")
    for i, (readable_id, uuid) in enumerate(list(id_mapping.items())[:5]):
        print(f"    {readable_id} → {uuid[:8]}...")

    # STEP 7: Chunk Markdown
    print("\n" + "="*60)
    print("STEP 7: Chunk Markdown")
    print("="*60)
    chunks = chunk_ir(semantic_ir_with_ids, max_tokens=500, overlap_tokens=50)
    print(f"✓ Chunked markdown")
    print(f"  Total chunks: {len(chunks)}")
    print(f"  Avg tokens/chunk: {sum(c['tokens'] for c in chunks) / len(chunks):.1f}")

    print(f"\n  First chunk preview:")
    print(chunks[0]['markdown'][:200] + "...")

    # STEP 8: Generate Embeddings
    print("\n" + "="*60)
    print("STEP 8: Generate Embeddings")
    print("="*60)
    embedder = SentenceTransformerEmbedder()
    embedded_chunks = embed_chunks(chunks, embedder)

    print(f"✓ Generated embeddings")
    print(f"  Embedding dimension: {embedded_chunks[0]['embedding_dim']}")
    print(f"  Total embedded chunks: {len(embedded_chunks)}")

    # STEP 9: Query with Natural Language
    print("\n" + "="*60)
    print("STEP 9: Query with Natural Language")
    print("="*60)
    retriever = ChunkRetriever(embedded_chunks, embedder)
    llm = OpenAILLM(model="gpt-4o")

    # Test query
    query = "search button"
    print(f"✓ Query - '{query}'")

    # Retrieve chunks
    results = retriever.query(query, top_k=3)
    print(f"  Retrieved {len(results)} chunks")
    for i, (chunk, score) in enumerate(results, 1):
        print(f"    Chunk {i} similarity: {score:.3f}")

    # Show ALL chunks
    for i, (chunk, score) in enumerate(results, 1):
        print(f"\n  Chunk {i} FULL content (score: {score:.3f}):")
        print("---")
        print(chunk['markdown'])
        print("---")

    # STEP 10: LLM Generate Element IDs
    print("\n" + "="*60)
    print("STEP 10: LLM Generate Element IDs")
    print("="*60)
    result = answer_query(query, retriever, llm, top_k=3)
    llm_response = result['response'].strip()

    print(f"✓ LLM generated response")
    print(f"  Query: '{query}'")
    print(f"  LLM Response: '{llm_response}'")

    # Parse comma-separated IDs
    if ',' in llm_response:
        element_ids = [id.strip() for id in llm_response.split(',')]
        print(f"  Parsed as multiple IDs: {element_ids}")
    else:
        element_ids = [llm_response]
        print(f"  Parsed as single ID: {element_ids}")

    # Filter valid IDs
    valid_ids = [id for id in element_ids if id in id_mapping]
    print(f"  Valid IDs in mapping: {valid_ids}")

    if not valid_ids:
        print(f"  ✗ No valid IDs found!")
        similar = [k for k in id_mapping.keys() if 'button' in k or 'search' in k or 'input' in k or 'textarea' in k]
        print(f"  Available IDs with 'button', 'search', 'input', or 'textarea': {similar[:10]}")

    # STEP 11: Generate XPaths
    print("\n" + "="*60)
    print("STEP 11: Generate XPaths")
    print("="*60)
    if valid_ids:
        print(f"✓ Generating XPaths for {len(valid_ids)} elements")
        for i, element_id in enumerate(valid_ids, 1):
            xpath = generate_xpath(element_id, id_mapping, full_ir)
            uuid = id_mapping[element_id]
            node = full_ir.get_node_by_id(uuid)

            print(f"\n  Element {i}/{len(valid_ids)}:")
            print(f"    ID: {element_id}")
            print(f"    XPath: {xpath}")
            print(f"    Tag: {node.tag}")
            print(f"    Attributes: {node.attributes}")
    else:
        print(f"✗ Cannot generate XPaths - no valid element IDs")

    print("\n" + "="*60)
    print("DEBUG COMPLETE")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
