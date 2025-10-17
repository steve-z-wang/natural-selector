# Natural Selector

⚠️ **Under Active Development - Not Production Ready**

Natural language browser automation. Query DOM elements using plain English.

## Quick Example

```python
from playwright.async_api import async_playwright
from natural_selector import Session
from natural_selector.integrations import OpenAILLM, SentenceTransformerEmbedder
from natural_selector.utils import capture_snapshot

# Capture page
async with async_playwright() as p:
    browser = await p.chromium.launch()
    page = await browser.new_page()
    await page.goto('https://www.google.com')
    snapshot = await capture_snapshot(page)
    await browser.close()

# Create session and query elements
session = Session(llm=OpenAILLM(), embedder=SentenceTransformerEmbedder())
page = session.create_page_from_cdp(snapshot)

# Query with natural language
button = page.select_one("search button")
print(button.to_xpath())  # (//input[@name="btnK"])[1]
print(button.to_css())     # input[name='btnK']
```

## How it Works

Natural Selector uses a multi-stage pipeline to find elements:

**1. DOM Capture**
- Uses Chrome DevTools Protocol to capture full DOM with computed styles and bounds

**2. Visibility Filtering (3 passes)**
- Pass 1: Remove non-rendered tags (script, style, head)
- Pass 2: Remove CSS-hidden elements (display:none, visibility:hidden, opacity:0)
- Pass 3: Remove zero-dimension elements without visible children (keeps positioned popups)

**3. Semantic Filtering (5 passes)**
- Convert DOM nodes to semantic representation
- Filter to semantic attributes only (role, aria-*, type, name, etc.)
- Remove empty nodes and collapse wrapper divs
- Generate readable IDs (button-1, input-2)

**4. RAG-Based Search**
- Chunk semantic tree into markdown with element IDs
- Embed chunks using sentence-transformers
- Vector search retrieves relevant chunks for query

**5. LLM Selection**
- LLM receives top-k chunks with element IDs
- Returns element ID(s) matching natural language query
- Generate XPath/CSS selectors from semantic tree

**Why this approach:**
- Visibility filtering handles dynamic content (modals, dropdowns)
- Semantic filtering reduces token usage (removes non-interactive elements)
- RAG enables querying large DOMs without context limits
- Readable IDs help LLM understand element purpose

## Features

- Natural language queries
- Multi-pass filtering (captures popups, modals, positioned elements)
- Guaranteed unique XPath/CSS selectors
- Handles large DOMs via chunking + RAG
- Customizable LLMs and embedders

## Roadmap

- [ ] HTML adapter (alternative to CDP for static HTML)
- [ ] Test with Mind2Web dataset
- [ ] Error handling & retry logic (LLM/embedding failures, timeouts)
- [ ] Selector validation (verify generated selectors work on page)
- [ ] Performance optimization (async operations, parallelization)
- [ ] Conditional RAG (skip embeddings for small DOMs, use direct LLM)
- [ ] More selector output formats (CSS variations, data-testid, etc.)
- [ ] Add tests (unit tests, integration tests)

## Status

🚧 **In Development** - Testing phase, API may change
