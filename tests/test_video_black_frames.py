"""Calibrate dark emptiness independently of theme brightness or subtitle burn-in."""
import unittest,tempfile,subprocess,json
from pathlib import Path
from PIL import Image,ImageDraw
from _support import load_script
m=load_script('video_black_frames','black_content_r8')

class BlackFrameContentTests(unittest.TestCase):
    def test_uniform_black_and_deep_gray_fail(self):
        for color in [(0,0,0),(16,16,16),(48,48,48)]:
            with self.subTest(color=color):self.assertTrue(m.frame_content(Image.new('RGB',(320,180),color))['emptyDark'])

    def test_content_with_small_area_is_not_empty(self):
        for graphic in ['header','dots']:
            image=Image.new('RGB',(320,180),(20,17,13));d=ImageDraw.Draw(image)
            if graphic=='header':d.text((12,10),'A SMALL HEADER',fill='white')
            else:
                for x in [80,100]:d.ellipse((x,70,x+4,74),fill=(180,180,180))
            with self.subTest(graphic=graphic):self.assertFalse(m.frame_content(image)['emptyDark'])

    def test_isolated_codec_speckle_does_not_count_as_content(self):
        image=Image.new('RGB',(320,180),(16,16,16));image.putpixel((80,60),(255,255,255))
        self.assertTrue(m.frame_content(image)['emptyDark'])

    def test_historical_misflagged_frames_keep_their_content(self):
        import hashlib
        root=Path(__file__).parent/'fixtures/dark-content-r8';manifest=json.loads((root/'manifest.json').read_text())
        self.assertEqual([row['frame'] for row in manifest['fixtures']],[0,610,1068,1550])
        for row in manifest['fixtures']:
            path=root/row['file'];self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),row['sha256'])
            with self.subTest(frame=row['frame']),Image.open(path) as image:
                self.assertFalse(m.frame_content(image)['emptyDark'])

    def test_one_empty_frame_between_content_frames_is_reported_by_index(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'fixture.mp4'
            subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=0x14110D:s=320x180:r=30:d=0.2',
                '-vf',"drawbox=x=12:y=12:w=30:h=3:color=white:t=fill:enable=not(eq(n\\,2))",'-c:v','libx264','-threads','1','-pix_fmt','yuv420p',str(source)],capture_output=True,check=True)
            result=m.inspect_black_frames(source,root/'check.json')
            self.assertEqual(result['framesInspected'],6);self.assertEqual(result['emptyFrames'],[2]);self.assertEqual(result['status'],'fail')
            self.assertEqual(json.loads((root/'check.json').read_text()),result)
