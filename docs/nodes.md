# Node Structures

## Node Hierarchy

```python
Node (ABC)
├── TextNode
└── ElementNode
```

## TextNode

```python
class TextNode(Node):
    id: str
    text: str
```

## ElementNode

```python
class ElementNode(Node):
    id: str              # UUID, preserved across all IRs
    cdp_index: int       # Original CDP node index (Full IR only)
    tag: str
    attributes: Dict[str, str]
    children: List[Node]  # Can be TextNode or ElementNode

    # CDP data (Full IR only)
    styles: Dict[str, str]
    bounds: BoundingBox
```

## BoundingBox

```python
@dataclass
class BoundingBox:
    x: float
    y: float
    width: float
    height: float
```

## IR Container

```python
class IR:
    root: ElementNode

    def get_node_by_id(id: str) -> ElementNode
    def all_nodes() -> List[ElementNode]
```

## Node Data by IR Stage

| Field | Full IR | Visible IR | Semantic IR |
|-------|---------|------------|-------------|
| id | ✓ | ✓ (same) | ✓ (same) |
| cdp_index | ✓ | ✗ | ✗ |
| tag | ✓ | ✓ | ✓ |
| attributes | ✓ (all) | ✓ (all) | ✓ (filtered) |
| styles | ✓ | ✗ | ✗ |
| bounds | ✓ | ✗ | ✗ |
| children | ✓ | ✓ (filtered) | ✓ (filtered+collapsed) |
