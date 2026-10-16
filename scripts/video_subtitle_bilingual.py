"""Measured English caption geometry, kept separate from Chinese line rules."""
from functools import lru_cache
from PIL import ImageFont
from openclaw_product_contract import ProductContractError

@lru_cache(maxsize=64)
def _font(size):
    from video_subtitles import _caption_font
    return ImageFont.truetype(str(_caption_font()),size)

def caption_text_width(text,size):
    return _font(size).getlength(text)

def _wrap(text,size,width):
    lines=[];line=''
    for word in text.split():
        trial=(line+' '+word).strip()
        if caption_text_width(trial,size)<=width:line=trial;continue
        if line:lines.append(line);line=''
        for ch in word:
            if line and caption_text_width(line+ch,size)>width:lines.append(line);line=''
            line+=ch
    if line:lines.append(line)
    return lines

def bilingual_layout(chinese_lines,english,width,height):
    from video_subtitles import subtitle_style
    if not isinstance(english,str) or not english.strip() or any(ord(c)<32 for c in english):
        raise ProductContractError('photo_subtitle_translation_invalid')
    style=subtitle_style(width,height);font=style['fontSize'];maximum=width-2*(style['sideMargin']+style['padding'])
    size=max(1,round(font*.58));minimum=max(1,round(font*.45))
    while size>minimum and caption_text_width(english,size)>maximum:size-=1
    lines=_wrap(english,size,maximum)
    if len(lines)>2:raise ProductContractError('photo_subtitle_english_too_long')
    gap=max(1,round(font*.20));en_spacing=max(1,round(size*.20));zh_height=len(chinese_lines)*font+(len(chinese_lines)-1)*style['lineSpacing'];en_height=len(lines)*size+(len(lines)-1)*en_spacing
    box_height=2*style['padding']+zh_height+gap+en_height;top=round(height*.9-box_height/2)
    if top<height*.8 or top+box_height>height:raise ProductContractError('photo_subtitle_layout_rejected')
    return {**style,'englishFontSize':size,'englishLines':lines,'englishColor':'0xcfcfcf','englishLineSpacing':en_spacing,'maxTextWidth':maximum,'sharedBackplate':True,'boxTop':top,'boxHeight':box_height,'boxWidth':min(width-2*style['sideMargin'],max(caption_text_width(t,font) for t in chinese_lines)+2*style['padding'] if not lines else max(max(caption_text_width(t,font) for t in chinese_lines),max(caption_text_width(t,size) for t in lines))+2*style['padding']),'chineseTop':top+style['padding'],'englishTop':top+style['padding']+zh_height+gap}
