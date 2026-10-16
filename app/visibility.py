"""Element visibility in one browser round trip instead of one is_visible() call per element.

The rule is Playwright's own (computeBox in its injected script): display:contents defers to the children;
otherwise checkVisibility(), computed visibility 'visible', and a non-empty bounding box.
"""
VISIBLE_JS="""const visible=e=>{
    const s=getComputedStyle(e);
    if(s.display==='contents'){
        for(let c=e.firstChild;c;c=c.nextSibling){
            if(c.nodeType===1&&visible(c))return true;
            if(c.nodeType===3){const r=document.createRange();r.selectNode(c);const b=r.getBoundingClientRect();if(b.width>0&&b.height>0)return true;}
        }
        return false;
    }
    if(e.checkVisibility&&!e.checkVisibility())return false;
    if(s.visibility!=='visible')return false;
    const b=e.getBoundingClientRect();return b.width>0&&b.height>0;
};"""
VISIBLE_ALL='els=>{'+VISIBLE_JS+'return els.map(visible);}'

async def visible(locator):
    """The currently visible matches of a locator, in document order."""
    flags=await locator.evaluate_all(VISIBLE_ALL)
    return [locator.nth(i) for i,shown in enumerate(flags) if shown]

async def any_visible(locator):
    return any(await locator.evaluate_all(VISIBLE_ALL))
