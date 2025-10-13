#!/usr/bin/env python
"""Test guaranteed unique XPaths with multiple queries"""

import sys
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), '../src')))

from playwright.async_api import async_playwright
from natural_selector import NaturalSelector
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
    print("="*60)
    print("Testing Guaranteed Unique XPaths")
    print("="*60)

    # Get snapshot
    cdp_snapshot = await get_snapshot('https://www.google.com')
    print(f"\n✓ Captured snapshot")

    # Create selector
    selector = NaturalSelector(
        llm=OpenAILLM(model="gpt-4o"),
        top_k=3
    )
    print(f"✓ Created NaturalSelector\n")

    # Test multiple queries
    queries = [
        "search button",
        "privacy link",
        "google search input",
        "about link",
    ]

    for query in queries:
        print(f"\n{'='*60}")
        print(f"Query: '{query}'")
        print(f"{'='*60}")

        xpaths = selector.select(cdp_snapshot, query)

        if xpaths:
            print(f"✓ Found {len(xpaths)} element(s)")
            for i, xpath in enumerate(xpaths, 1):
                print(f"  [{i}] {xpath}")
        else:
            print("✗ Not found")

    print(f"\n{'='*60}")
    print("Complete!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
