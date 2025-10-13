# Natural Selector

⚠️ **Under Active Development - Not Production Ready**

Natural language browser automation. Query DOM elements using plain English.

## Quick Example

```python
from natural_selector import NaturalSelector
from natural_selector.integrations import OpenAILLM

# Create selector
selector = NaturalSelector(llm=OpenAILLM())

# Query with natural language
xpaths = selector.select(cdp_snapshot, "search button")
# Returns: ['(//input[@name="btnK"])[1]']
```

## How it Works

1. Capture DOM via Chrome DevTools Protocol
2. Filter invisible/non-semantic elements
3. Create embeddings and semantic search
4. LLM identifies elements from context
5. Generate guaranteed unique XPath selectors

## Features

- Natural language queries
- Guaranteed unique XPath selectors
- Automatic filtering of hidden elements
- Customizable LLMs and embedders

## Status

🚧 **In Development** - Testing phase, API may change
