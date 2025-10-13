# Architecture

## Pipeline

```
CDP Snapshot → Full IR → Visible IR → Semantic IR → Selector
```

## Three IRs with ID Preservation

### Full IR
- Complete tree from CDP
- All nodes, all data
- Each ElementNode has unique ID + cdp_index

### Visible IR
- Filtered: removes invisible nodes
- Preserves: original node IDs

### Semantic IR
- Filtered: removes non-semantic nodes
- Collapsed: single-child wrappers removed
- Preserves: original node IDs

## Selector Generation

```python
semantic_node = match(semantic_ir, "login button")
full_node = full_ir.get_node_by_id(semantic_node.id)  # Same ID!
selector = generate_selector(full_node, full_ir)
```

## Why This Works

Semantic IR has simplified structure for matching, but we generate selectors using Full IR's complete context (CDP index, full tree position).
