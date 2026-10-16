"""Real broken display splits must receive complete translations, never word slices."""
import copy,unittest
from _support import load_script
s=load_script('video_subtitles','subtitle_display_r8')


def fixture():
    first='我是AI研究生，也练短跑，断更一年，总觉得发出去会被看低。'
    study='一项焦虑人群的小研究，让人逐条记担心再追踪，约91%没发生。'
    timings=[{'text':first,'startSeconds':0,'endSeconds':5.76,'englishText':"I'm an AI grad student who also sprints. I haven't posted in a year, and I keep feeling people will look down on me if I post."},
             {'text':study,'startSeconds':7.12,'endSeconds':13.76,'englishText':'A small study of anxious people had them log each worry and track it; about 91% never happened.'}]
    rows=[(0,107,'我是AI研究生，也练短跑，断更一年，',"I'm an AI grad student and a sprinter. I haven't posted for a year."),
          (107,173,'总觉得发出去会被看低。','I worry people will look down on me if I post.'),
          (214,360,'一项焦虑人群的小研究，让人逐条记担心再追踪，','In a small study, anxious participants logged their worries and followed up.'),
          (360,413,'约91%没发生。','About 91% of those worries never happened.')]
    frozen=[{'startFrame':a,'endFrame':b,'text':zh,'englishText':en} for a,b,zh,en in rows]
    return {'script':first+study,'narration':{'sentenceTimings':timings,'subtitleCues':frozen},'shots':[{'shot':{'endSeconds':14}}]},frozen


class DisplayTranslationTests(unittest.TestCase):
    def test_real_and_i_keep_and_track_it_splits_use_complete_display_translations(self):
        d,frozen=fixture();before=copy.deepcopy(d);cues=s.build_subtitle_cues(d,fps=30,total_frames=420)
        self.assertEqual(d,before)
        self.assertEqual([{k:c[k] for k in ['startFrame','endFrame','text','englishText']} for c in cues],frozen)
        self.assertFalse(any(c['englishText'].endswith(('and I keep','and track')) or c['englishText'].startswith('it;') for c in cues))

    def test_old_sentence_translation_requires_regeneration_instead_of_proportional_cutting(self):
        d,_=fixture();d['narration'].pop('subtitleCues')
        with self.assertRaisesRegex(Exception,'photo_subtitle_translation_plan_required'):
            s.build_subtitle_cues(d,fps=30,total_frames=420)

    def test_stale_frozen_chinese_or_timing_cannot_be_burned(self):
        for key,value in [('text','变过的中文'),('startFrame',1)]:
            d,_=fixture();d['narration']['subtitleCues'][0][key]=value
            with self.subTest(key=key),self.assertRaisesRegex(Exception,'photo_subtitle_translation_plan_stale'):
                s.build_subtitle_cues(d,fps=30,total_frames=420)
