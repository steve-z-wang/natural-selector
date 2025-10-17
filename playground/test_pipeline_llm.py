"""
Standalone test script to track "Sign in to Google" popup through the pipeline.
Can be run directly: python test_pipeline_llm.py
"""

import sys
import os
import asyncio

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), '../src')))

from playwright.async_api import async_playwright
from natural_selector._internal.parsers.cdp_parser import parse_cdp_snapshot
from natural_selector._internal.filters import visibility_pass
from natural_selector._internal.filters.semantic.convert import convert_to_semantic_pass
from natural_selector._internal.filters.semantic.filter_attributes import filter_by_attributes_pass
from natural_selector._internal.filters.semantic.filter_empty import filter_empty_nodes_pass
from natural_selector._internal.filters.semantic.collapse_wrappers import collapse_wrappers_pass
from natural_selector._internal.filters.semantic.generate_ids import generate_ids_pass
from natural_selector._internal.ir.dom_ir import DomElement, DomText
from natural_selector._internal.ir.semantic_ir import SemanticElement, SemanticIR


def find_text_elements(dom_ir, search_text):
    """Find any elements containing specific text in DomIR."""
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
                    'text': combined_text[:80] + ('...' if len(combined_text) > 80 else ''),
                    'bounds': f"w={elem.bounds.width:.1f}, h={elem.bounds.height:.1f}" if elem.bounds else "no bounds",
                    'jsname': elem.attributes.get('jsname', 'N/A'),
                    'styles': elem.styles
                })
    return results


def count_text_in_semantic(root, search_text):
    """Count elements containing text in semantic tree."""
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


async def main():
    print("="*80)
    print("TESTING POPUP DIALOG FILTERING")
    print("="*80)

    # Step 1: Launch browser
    print("\n[1] Launching browser...")
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    page = await browser.new_page()
    print("✓ Browser launched")

    # Step 2: Capture CDP snapshot
    print("\n[2] Capturing CDP snapshot...")
    url = 'https://www.google.com'
    await page.goto(url, wait_until='networkidle')
    print("  Waiting 5 seconds for page to stabilize...")
    await asyncio.sleep(5)

    cdp = await page.context.new_cdp_session(page)
    cdp_snapshot = await cdp.send('DOMSnapshot.captureSnapshot', {
        'computedStyles': ['display', 'visibility', 'opacity'],
        'includePaintOrder': True,
        'includeDOMRects': True
    })
    print("✓ Captured snapshot")

    # Step 3: Parse to DomIR
    print("\n[3] Building DomIR...")
    dom_ir = parse_cdp_snapshot(cdp_snapshot)
    print(f"✓ Total nodes: {len(dom_ir.all_element_nodes())}")

    # Step 4: Check for popup in full-ir
    print("\n[4] Searching for popup in full-ir...")
    popup_elements = find_text_elements(dom_ir, "Sign in to Google")
    print(f"  Found {len(popup_elements)} elements with 'Sign in to Google'")

    # Find the actual popup dialog (non-zero height)
    actual_popup = None
    for elem in popup_elements:
        if elem['jsname'] == 'haAclf':
            actual_popup = elem
            print(f"  ✓ Found popup dialog: {elem['tag']}, bounds={elem['bounds']}, jsname={elem['jsname']}")
            print(f"    text='{elem['text']}'")
            print(f"    styles={elem['styles']}")
            break

    if not actual_popup:
        print("  ✗ Popup dialog NOT found in full-ir!")
        await browser.close()
        await playwright.stop()
        return

    # Step 5: Check parent chain before visibility filter
    print("\n[5] Checking popup's parent chain...")

    # Find the popup node in the tree
    def find_popup_node(node, search_jsname="haAclf"):
        """Find node with specific jsname."""
        if isinstance(node.data, DomElement):
            if node.data.attributes.get('jsname') == search_jsname:
                return node
        for child in node.children:
            result = find_popup_node(child, search_jsname)
            if result:
                return result
        return None

    popup_node = find_popup_node(dom_ir.root)
    if popup_node:
        print(f"  Found popup node in tree")
        # Use walk_up() to get parent chain
        print(f"  Tracing parent chain:")
        parent_path = popup_node.walk_up()  # Returns [popup, parent, grandparent, ..., root]

        # Show parent chain (closest 6 levels)
        for depth, node in enumerate(parent_path[:6]):
            elem = node.data
            if isinstance(elem, DomElement):
                jsname = elem.attributes.get('jsname', 'N/A')
                bounds = f"w={elem.bounds.width:.1f}, h={elem.bounds.height:.1f}" if elem.bounds else "no bounds"
                style_attr = elem.attributes.get('style', 'N/A')[:100]

                print(f"    [{depth}] <{elem.tag}> jsname={jsname}, bounds={bounds}")
                print(f"        styles={elem.styles}")
                if style_attr != 'N/A':
                    print(f"        inline style='{style_attr}'")

    # Step 6: Apply visibility filter
    print("\n[6] Applying visibility filter...")
    visible_dom_ir = visibility_pass(dom_ir)
    print(f"  Nodes after visibility: {len(visible_dom_ir.all_element_nodes())}")

    popup_after_vis = find_text_elements(visible_dom_ir, "Sign in to Google")
    print(f"  Popup elements after visibility: {len(popup_after_vis)}")

    popup_survived = False
    for elem in popup_after_vis:
        if elem['jsname'] == 'haAclf':
            popup_survived = True
            print(f"  ✓ Popup dialog SURVIVED visibility filter")
            print(f"    {elem['tag']}, bounds={elem['bounds']}, jsname={elem['jsname']}")
            break

    if not popup_survived:
        print("  ✗ Popup dialog FILTERED OUT by visibility filter!")
        print("\n" + "="*80)
        print("RESULT: Popup removed by visibility filter - check parent chain above")
        print("="*80)
        await browser.close()
        await playwright.stop()
        return

    # Step 7: Apply semantic filters
    print("\n[7] Applying semantic filters...")

    # Convert
    root = convert_to_semantic_pass(visible_dom_ir.root)
    popup_count = count_text_in_semantic(root, "Sign in to Google")
    print(f"  After convert: Popup count={popup_count}")

    # Filter attributes
    root = filter_by_attributes_pass(root)
    popup_count = count_text_in_semantic(root, "Sign in to Google")
    print(f"  After filter_attributes: Popup count={popup_count}")

    # Filter empty
    root = filter_empty_nodes_pass(root)
    popup_count = count_text_in_semantic(root, "Sign in to Google")
    print(f"  After filter_empty: Popup count={popup_count}")

    # Collapse wrappers
    root = collapse_wrappers_pass(root)
    popup_count = count_text_in_semantic(root, "Sign in to Google")
    print(f"  After collapse_wrappers: Popup count={popup_count}")

    # Generate IDs
    root, id_mapping = generate_ids_pass(root)

    # Create SemanticIR
    semantic_ir = SemanticIR(root, id_index=id_mapping)
    print(f"  ✓ Final semantic nodes: {len(semantic_ir.all_element_nodes())}")

    # Step 8: Check if popup is in final semantic-ir
    print("\n[8] Checking final semantic-ir...")

    # Search for popup in semantic tree
    def find_popup_in_semantic(root):
        """Find popup dialog in semantic tree."""
        results = []
        def traverse(node):
            if isinstance(node.data, SemanticElement):
                # Collect text
                all_text = []
                def collect_text(n):
                    for child in n.children:
                        if hasattr(child.data, 'text'):
                            all_text.append(child.data.text)
                        if isinstance(child.data, SemanticElement):
                            collect_text(child)
                collect_text(node)
                combined_text = ''.join(all_text).strip()

                if "Sign in to Google" in combined_text:
                    results.append({
                        'tag': node.data.tag,
                        'id': getattr(node.data, 'readable_id', 'NO_ID'),
                        'text': combined_text[:100],
                        'attrs': node.data.semantic_attributes
                    })

                for child in node.children:
                    traverse(child)
        traverse(root)
        return results

    popup_in_semantic = find_popup_in_semantic(root)
    if popup_in_semantic:
        print(f"  ✓ Popup FOUND in final semantic-ir!")
        for item in popup_in_semantic[:3]:
            print(f"    - {item['id']}: <{item['tag']}> attrs={item['attrs']}")
            print(f"      text='{item['text']}'")
    else:
        print(f"  ✗ Popup NOT found in final semantic-ir!")

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Full-ir: {'✓ Found' if actual_popup else '✗ Not found'}")
    print(f"After visibility: {'✓ Survived' if popup_survived else '✗ Filtered out'}")
    print(f"Final semantic-ir: {'✓ Present' if popup_in_semantic else '✗ Missing'}")

    if popup_in_semantic:
        print(f"\nPopup appears in semantic-ir with {len(popup_in_semantic)} element(s)")
    elif popup_survived:
        print(f"\n⚠ Popup survived visibility but removed by semantic filters!")
    else:
        print(f"\n⚠ Popup filtered out by visibility filter!")

    # Cleanup
    print("\n[9] Closing browser...")
    await browser.close()
    await playwright.stop()
    print("✓ Done")


if __name__ == '__main__':
    asyncio.run(main())
