"""CDP snapshot capture utility."""

from typing import Dict, Any


async def capture_snapshot(page) -> Dict[str, Any]:
    """
    Capture CDP DOMSnapshot from a Playwright page.

    Args:
        page: Playwright page object

    Returns:
        Dict: CDP DOMSnapshot with documents, strings, and layout data
    """
    # Get CDP session
    cdp = await page.context.new_cdp_session(page)

    # Capture snapshot
    snapshot = await cdp.send('DOMSnapshot.captureSnapshot', {
        'computedStyles': ['display', 'visibility', 'opacity'],
        'includePaintOrder': True,
        'includeDOMRects': True
    })

    return snapshot
