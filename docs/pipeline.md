# Pipeline Details

## Stage 1: CDP → Full IR

**Input**: CDP DOMSnapshot JSON
**Output**: IR with complete tree

**Process**:
- Parse CDP parallel arrays
- Create ElementNode for each element
- Assign unique ID + store cdp_index
- Store styles, bounds from CDP layout data
- Create TextNode for text content

## Stage 2: Full IR → Visible IR

**Input**: Full IR
**Output**: IR with only visible nodes (IDs preserved)

**Filter out**:
- `display: none`
- `visibility: hidden`
- `opacity: 0`
- Zero-size bounding boxes
- `hidden` attribute
- `<input type="hidden">`

**Process**:
- Traverse Full IR tree
- For each node, check visibility
- If visible, create new ElementNode with **same ID**
- Recursively process visible children

## Stage 3: Visible IR → Semantic IR

**Input**: Visible IR
**Output**: IR with only semantic nodes (IDs preserved)

**Transformations**:

1. **Filter Attributes**
   - Keep: `role`, `aria-*`, `type`, `href`, `name`, `placeholder`
   - Remove: `class`, `style`, `data-*`, etc.

2. **Remove Non-Semantic Nodes**
   - Keep: `button`, `a`, `input`, `select`, `h1-h6`, `img`, etc.
   - Remove: empty `div`, `span` with no semantic role

3. **Collapse Wrappers**
   - Single-child wrapper with no semantic value → promote child

**Process**:
- Traverse Visible IR tree
- Filter attributes on each node
- Remove meaningless children
- Collapse single-child wrappers
- Preserve IDs for surviving nodes

## Complete Flow

```python
# Parse
full_ir = parse_cdp_snapshot(cdp_data)

# Filter visibility
visible_ir = visibility_pass(full_ir)

# Extract semantic
semantic_ir = semantic_pass(visible_ir)

# Query
node = match(semantic_ir, "login button")

# Generate selector
full_node = full_ir.get_node_by_id(node.id)
selector = generate_selector(full_node, full_ir)
```
