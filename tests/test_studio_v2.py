import base64
import tempfile
from pathlib import Path
import unittest
from speech_text import split_script,write_subtitles,caption_groups
from server import Studio
from documents import import_document


class StudioV2Tests(unittest.TestCase):
    def test_silence_markers_are_not_spoken(self):
        result=split_script('[1s silence] Hello. [2s silence] World. [5s silence]')
        self.assertEqual(result,[('silence',1),('text','Hello.'),('silence',2),('text','World.'),('silence',5)])
        for bad in ('Hello [6s silence]','Hello [0s silence]','Hello [2.5s silence]','Hello [oops silence]','[3s silence]'):
            with self.assertRaises(ValueError):split_script(bad)

    def test_paragraph_pause_and_inline_pause_both_count(self):
        result=split_script('Hello.\n\nPeace. [3s silence] Amen.',.5)
        self.assertEqual([v for k,v in result if k=='silence'],[.5,3])

    def test_srt_layout_offsets_and_millisecond_structure(self):
        words=[{'text':'First sentence.','start':.1,'end':1.5},{'text':'After the pause.','start':4.5,'end':6}]
        cues=caption_groups(words)
        with tempfile.TemporaryDirectory() as folder:
            stem=Path(folder)/'captions'
            final=write_subtitles(stem,cues,6.1)
            self.assertEqual(final[1]['start'],4.5)
            self.assertIn(b'00:00:04,500 --> 00:00:06,000',stem.with_suffix('.srt').read_bytes())
            self.assertIn(b'\r\n\r\n2\r\n',stem.with_suffix('.srt').read_bytes())
            self.assertTrue(stem.with_suffix('.vtt').read_bytes().startswith(b'WEBVTT\n\n'))

    def test_model_settings_are_saved_per_job(self):
        with tempfile.TemporaryDirectory() as folder:
            studio=Studio(folder)
            studio.voices=[{'ShortName':'en-US-AndrewNeural'}]
            raw={'engine':'kokoro','voice':'af_heart','text':'First script.','speed':.87,
                 'blend':[{'voice':'af_heart','weight':65},{'voice':'af_bella','weight':35}], 'pitch':-30}
            studio.add([raw])
            raw['blend'][0]['weight']=5
            studio.add([{'engine':'edge','voice':'en-US-AndrewNeural','text':'Second script.','speed':.65,'pitch':-12}])
            first,second=studio.jobs()
            self.assertEqual(first['blend'][0]['weight'],65)
            self.assertEqual(first['pitch'],0)
            self.assertEqual(first['speed'],.87)
            self.assertEqual(second['pitch'],-12)
            self.assertEqual(second['blend'],[])
            for update in ({'voice':'af_heart','engine':'edge'},{'blend':[{'voice':'bf_emma','weight':1}]},{'speed':2.5}):
                with self.assertRaises(ValueError):studio.validate({**raw,**update})
            studio.db.close()

    def test_kitten_cpu_engine_has_distinct_voices_and_local_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            studio=Studio(folder)
            voices=studio.catalog('kitten')
            self.assertEqual(len(voices),8)
            self.assertEqual(len({voice['ShortName'] for voice in voices}),8)
            job=studio.unpack(studio.validate({'engine':'kitten','voice':'Jasper',
                                               'text':'A calm local recording.','speed':1.25,
                                               'pitch':20,'volume':20}))
            self.assertEqual(job['engine'],'kitten')
            self.assertEqual(job['voice'],'Jasper')
            self.assertEqual(job['speed'],1.25)
            self.assertEqual((job['pitch'],job['volume']),(0,0))
            studio.db.close()

    def test_piper_catalog_exposes_american_speakers_without_loading_models(self):
        with tempfile.TemporaryDirectory() as folder:
            studio=Studio(folder)
            voices=studio.catalog('piper')
            self.assertEqual(len(voices),22)
            self.assertEqual(len({voice['ShortName'] for voice in voices}),22)
            self.assertTrue(all(voice['Locale']=='en-US' for voice in voices))
            job=studio.unpack(studio.validate({'engine':'piper','voice':'en_US-arctic-medium::2',
                                               'text':'American local voice.','speed':1.5}))
            self.assertEqual(job['engine'],'piper')
            self.assertEqual(job['speed'],1.5)
            studio.db.close()

    def test_chatterbox_nano_settings_and_builtin_voice(self):
        with tempfile.TemporaryDirectory() as folder:
            studio=Studio(folder)
            voices=studio.catalog('chatterbox')
            self.assertEqual([voice['ShortName'] for voice in voices],['builtin'])
            job=studio.unpack(studio.validate({
                'engine':'chatterbox','voice':'builtin','text':'A calm local recording.',
                'speed':1.25,'temperature':.65,'top_p':.9,'top_k':500,
                'repetition_penalty':1.3,'pitch':20,'volume':20,
            }))
            self.assertEqual((job['pitch'],job['volume']),(0,0))
            self.assertEqual((job['temperature'],job['top_p'],job['top_k'],job['repetition_penalty']),(.65,.9,500,1.3))
            with self.assertRaises(ValueError):
                studio.validate({'engine':'chatterbox','voice':'builtin','text':'Hello','temperature':3})
            studio.db.close()

    def test_recordings_are_numbered_sequentially_inside_each_title(self):
        with tempfile.TemporaryDirectory() as folder:
            studio=Studio(folder)
            studio.voices=[{'ShortName':'en-US-AndrewNeural'}]
            studio.add([{'title':'Morning prayer','text':'First section.'}])
            studio.add([{'title':'Morning prayer','text':'Second section.\n--------------------\nThird section.'}])
            studio.add([{'title':'Evening prayer','text':'A different series.'}])
            jobs=studio.jobs()
            self.assertEqual([(job['group_title'],job['part_number']) for job in jobs],[
                ('Morning prayer',1),('Morning prayer',2),('Morning prayer',3),
                ('Evening prayer',1),
            ])
            self.assertEqual([job['title'] for job in jobs[:3]],['Morning prayer']*3)
            studio.db.close()

    def test_legacy_automatic_titles_become_one_continuous_series(self):
        with tempfile.TemporaryDirectory() as folder:
            studio=Studio(folder)
            studio.voices=[{'ShortName':'en-US-AndrewNeural'}]
            for text in ('First old script.','Second old script.','Third old script.'):
                job_id=studio.add([{'text':text}])[0]
                studio.update(job_id,title=text[:55],group_title=text[:55],part_number=1)
            studio.db.close()
            studio=Studio(folder)
            jobs=studio.jobs()
            self.assertEqual([job['group_title'] for job in jobs],['Untitled recording']*3)
            self.assertEqual([job['part_number'] for job in jobs],[1,2,3])
            studio.db.close()

    def test_pdf_chapter_import(self):
        import pymupdf
        document=pymupdf.open()
        document.new_page().insert_text((72,72),'First chapter text.')
        document.new_page().insert_text((72,72),'Second chapter text.')
        document.set_toc([[1,'Chapter One',1],[1,'Chapter Two',2]])
        encoded=base64.b64encode(document.tobytes()).decode()
        document.close()
        result=import_document({'name':'book.pdf','content':encoded,'split_chapters':True})
        self.assertEqual(len(result),2)
        self.assertEqual(result[1]['title'],'Chapter Two')
        self.assertIn('Second chapter',result[1]['text'])

    def test_epub_chapter_import_in_spine_order(self):
        from ebooklib import epub
        book=epub.EpubBook()
        book.set_identifier('test-book')
        book.set_title('Test book')
        book.set_language('en')
        chapters=[]
        for n in (1,2):
            chapter=epub.EpubHtml(title=f'Chapter {n}',file_name=f'{n}.xhtml',lang='en')
            chapter.content=f'<h1>Chapter {n}</h1><p>Words for chapter {n}.</p><script>do not speak this</script>'
            book.add_item(chapter)
            chapters.append(chapter)
        book.spine=chapters
        book.toc=chapters
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'book.epub'
            epub.write_epub(str(path),book)
            encoded=base64.b64encode(path.read_bytes()).decode()
        result=import_document({'name':'book.epub','content':encoded,'split_chapters':True})
        self.assertEqual(len(result),2)
        self.assertIn('chapter 2',result[1]['text'])
        self.assertNotIn('do not speak',result[0]['text'])
