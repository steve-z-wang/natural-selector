# %% [markdown]
# # Natural-Selector API Test
#
# Test the public API with a simple example

# %%
import sys
import os
import json

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), '../src')))

from playwright.async_api import async_playwright
from natural_selector import NaturalSelector
from natural_selector.integrations import OpenAILLM

# %% [markdown]
# ## Step 1: Capture CDP Snapshot

# %%
async def get_snapshot(url: str):
    """Get CDP snapshot from URL."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url, wait_until='networkidle')

        # Get CDP session
        cdp = await page.context.new_cdp_session(page)

        # Capture snapshot
        snapshot = await cdp.send('DOMSnapshot.captureSnapshot', {
            'computedStyles': ['display', 'visibility', 'opacity'],
            'includePaintOrder': True,
            'includeDOMRects': True
        })

        await browser.close()
        return snapshot

# Capture from google.com
cdp_snapshot = await get_snapshot('https://www.google.com')

print(f"✓ Captured CDP snapshot")
print(f"  Strings: {len(cdp_snapshot.get('strings', []))}")
print(f"  Documents: {len(cdp_snapshot.get('documents', []))}")

# %% [markdown]
# ## Step 2: Initialize Natural Selector

# %%
# Create selector with OpenAI LLM
selector = NaturalSelector(
    llm=OpenAILLM(model="gpt-4o"),  # Uses OPENAI_API_KEY from .env
    top_k=3
)

print("✓ Created NaturalSelector")

# %% [markdown]
# ## Step 3: Query with Natural Language

# %%
# Test queries
queries = [
    "search button",
    "privacy link",
    "google search input",
]

for query in queries:
    print(f"\n{'='*60}")
    print(f"Query: '{query}'")
    print(f"{'='*60}")

    xpath = selector.select(cdp_snapshot, query)

    if xpath:
        print(f"XPath: {xpath}")
    else:
        print("Not found")

# %%
