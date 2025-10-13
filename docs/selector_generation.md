# Selector Generation

## Input

- SemanticNode (from query match)
- Full IR (complete tree)

## Process

1. Lookup Full IR node: `full_ir.get_node_by_id(semantic_node.id)`
2. Generate selector using Full IR context

## Selector Strategies

### Priority Order

1. **Unique ID**: `#login-btn`
2. **Test ID**: `[data-testid="login"]`
3. **CSS + Position**: `div.header > button.primary:nth-child(2)`
4. **XPath**: `/html/body/div[1]/button[2]`

## Example

```python
# Semantic IR match
semantic_node = match(semantic_ir, "login button")
# ElementNode(id="abc123", tag="button", attributes={"role": "button"})

# Lookup in Full IR
full_node = full_ir.get_node_by_id("abc123")
# ElementNode(id="abc123", tag="button", cdp_index=42,
#             attributes={"id": "login-btn", "class": "btn primary"})

# Generate selector
selector = generate_selector(full_node, full_ir)
# Returns: "#login-btn"
```

## Why Full IR is Needed

Semantic IR has filtered attributes, but Full IR has:
- All attributes (including `id`, `class`, `data-*`)
- CDP index for precise positioning
- Complete tree structure for nth-child calculations
