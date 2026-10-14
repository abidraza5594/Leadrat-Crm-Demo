import sys
from pathlib import Path
sys.path.insert(0,r'C:\Users\abidk\AppData\Local\Temp\beacon-doc-render-20261012\python-packages')
import aspose.words as aw
root=Path(__file__).parent
doc=aw.Document(str(root/'Beacon_Technology_Architecture_and_Cost.docx'))
qa=root/'qa'; qa.mkdir(exist_ok=True)
doc.update_page_layout()
print('Pages:',doc.page_count)
for i in range(doc.page_count):
    options=aw.saving.ImageSaveOptions(aw.SaveFormat.PNG)
    options.page_set=aw.saving.PageSet(i)
    options.horizontal_resolution=110; options.vertical_resolution=110
    doc.save(str(qa/f'page-{i+1}.png'),options)
    print(i+1,doc.extract_pages(i,1).to_string(aw.SaveFormat.TEXT)[:120].replace('\n',' '))

