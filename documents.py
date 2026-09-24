"""Extract text/chapter drafts without executing imported document content."""
import base64
import io
from pathlib import Path
import re
import tempfile
import zipfile


def import_document(raw):
    name=Path(str(raw.get('name','document.txt'))).name
    payload=base64.b64decode(raw.get('content',''),validate=True)
    if len(payload)>15*1024*1024: raise ValueError('Each imported document must be under 15 MB.')
    ext=Path(name).suffix.lower()
    chapters=[]
    if ext=='.txt':
        text=payload.decode('utf-8-sig')
        if raw.get('split_chapters',True):
            parts=re.split(r'(?im)(?=^chapter\s+(?:\d+|[ivxlcdm]+)\b)|^\s*---\s*$',text)
        else: parts=[text]
        for i,text in enumerate(parts):
            if text.strip(): chapters.append({'title':text.strip().splitlines()[0][:80] if len(parts)>1 else Path(name).stem,'text':text.strip()})
    elif ext=='.pdf':
        import pymupdf
        with pymupdf.open(stream=payload,filetype='pdf') as pdf:
            if pdf.needs_pass: raise ValueError('This PDF is password protected. Import an unlocked copy.')
            if len(pdf)>1000: raise ValueError('Import PDFs up to 1,000 pages at a time.')
            toc=[x for x in pdf.get_toc() if x[0]==1 and x[2]>0] if raw.get('split_chapters',True) else []
            starts=[(x[2]-1,x[1]) for x in toc]
            if not starts or starts[0][0]>0: starts.insert(0,(0,Path(name).stem))
            for i,(start,title) in enumerate(starts):
                end=starts[i+1][0] if i+1<len(starts) else len(pdf)
                text='\n\n'.join(pdf[n].get_text() for n in range(start,min(end,len(pdf)))).strip()
                if text: chapters.append({'title':title,'text':text})
    elif ext=='.epub':
        from bs4 import BeautifulSoup
        from ebooklib import epub
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            if sum(f.file_size for f in archive.infolist())>80*1024*1024: raise ValueError('The expanded EPUB is too large.')
        with tempfile.TemporaryDirectory(prefix='stillwater-import-') as folder:
            path=Path(folder)/'book.epub'
            path.write_bytes(payload)
            book=epub.read_epub(str(path),options={'ignore_ncx':True})
            for item_id,_ in book.spine:
                item=book.get_item_with_id(item_id)
                if item is None: continue
                soup=BeautifulSoup(item.get_content(),'html.parser')
                for element in soup(['script','style','nav']): element.decompose()
                title=soup.find(['h1','h2','title'])
                text=soup.get_text(separator='\n',strip=True)
                if text: chapters.append({'title':title.get_text(strip=True)[:120] if title else f'{Path(name).stem} · {len(chapters)+1}','text':text})
        if not raw.get('split_chapters',True) and chapters:
            chapters=[{'title':Path(name).stem,'text':'\n\n'.join(c['text'] for c in chapters)}]
    else: raise ValueError('Import TXT, PDF, or EPUB files.')
    if not chapters: raise ValueError('No readable text found. Scanned PDFs need OCR before import.')
    if sum(len(c['text']) for c in chapters)>1000000: raise ValueError('Import up to 1 million text characters at a time.')
    # Safely divide long chapters at paragraphs for the queue's per-script limit.
    result=[]
    for chapter in chapters:
        text=chapter['text']
        part=1
        while text:
            cut=len(text)
            if cut>39000:
                cut=text.rfind('\n',0,39000)
                if cut<1000: cut=text.rfind(' ',0,39000)
                if cut<1000: cut=39000
            result.append({'title':chapter['title']+(f' · Part {part}' if len(chapter['text'])>39000 else ''),'text':text[:cut].strip()})
            text=text[cut:].strip()
            part+=1
    return result
