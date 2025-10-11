# Natural Selector

A natural language HTML selector engine that lets you query DOM elements using plain English instead of CSS selectors or XPath.

## Concept

```javascript
// Instead of this:
const button = document.querySelector('#user-profile > div.actions > button:nth-child(2)');

// Do this:
const button = naturalSelector(html, 'the red logout button');
```

## Features

- Natural language element selection
- Works with static HTML or Chrome DevTools Protocol (CDP)
- Drop-in replacement for traditional selectors
- More resilient to DOM changes
- Perfect for LLM-powered browser automation

## Status

🚧 Under development
