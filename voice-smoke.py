import asyncio
import edge_tts

async def main():
    total=0
    async for item in edge_tts.Communicate('Welcome to Beacon. Let us explore the Leads workspace.','en-IN-NeerjaNeural',rate='+8%').stream():
        if item['type']=='audio':total+=len(item['data'])
    print('Neural speech audio bytes:',total)
    assert total>1000
asyncio.run(main())
