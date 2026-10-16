"""Detect empty dark frames; a dark canvas containing strokes is not empty."""
from pathlib import Path
import json,subprocess,tempfile
from PIL import Image,ImageFilter,ImageStat


def frame_content(image):
    image=image.convert('RGB')
    gray=image.convert('L');clean=gray.filter(ImageFilter.MedianFilter(3))
    edges=clean.filter(ImageFilter.FIND_EDGES)
    # FIND_EDGES retains its border: do not mistake the image boundary for art.
    edge_pixels=sum(edges.crop((1,1,edges.width-1,edges.height-1)).histogram()[17:])
    stddev=ImageStat.Stat(gray).stddev[0]
    dark=max(ImageStat.Stat(image).mean)<=64
    empty=dark and stddev<=3 and edge_pixels<8
    return {'emptyDark':empty,'dark':dark,'lumaStddev':round(stddev,6),'edgePixels':edge_pixels}


def inspect_black_frames(video: Path,diagnostic: Path):
    metadata=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height','-of','json',str(video)]))['streams'][0]
    width=min(320,metadata['width']);height=max(4,round(metadata['height']*width/metadata['width']))
    frame_bytes=width*height*3;count=0;empty=[];examples=[]
    with tempfile.TemporaryFile() as errors:
        process=subprocess.Popen(['ffmpeg','-nostdin','-v','error','-xerror','-i',str(video),'-map','0:v:0','-vf',f'scale={width}:{height}:flags=area','-pix_fmt','rgb24','-f','rawvideo','-'],stdout=subprocess.PIPE,stderr=errors)
        try:
            while raw:=process.stdout.read(frame_bytes):
                if len(raw)!=frame_bytes:raise ValueError('photo_black_frame_decode_incomplete')
                metric=frame_content(Image.frombytes('RGB',(width,height),raw))
                if metric['emptyDark']:empty.append(count)
                if len(examples)<12 or metric['emptyDark']:examples.append({'frame':count,**metric})
                count+=1
            if process.wait(timeout=30) or not count:raise ValueError('photo_black_frame_decode_failed')
        finally:
            if process.poll() is None:process.kill()
            process.wait();process.stdout.close()
    result={'status':'fail' if empty else 'pass','framesInspected':count,'emptyFrames':empty,'analysisSize':[width,height],
        'criteria':{'maxMeanChannel':64,'maxLumaStddev':3,'minEdgePixelsForContent':8,'medianNoiseFilter':3,'edgeThreshold':16},'examples':examples}
    diagnostic.write_text(json.dumps(result,indent=2)+'\n');return result
