#!/usr/bin/env python3


"""


微信公众号视频生成器 - 跨平台版本


自动检测 Windows / Linux (WSL) / macOS 环境


"""


import os, json, subprocess, tempfile, shutil, sys, re


from pathlib import Path


from PIL import Image, ImageDraw, ImageFont, ImageOps





# ============================================================


# 1. 环境检测与路径配置


# ============================================================





def detect_environment():


    if sys.platform == 'win32':


        return 'windows'


    try:


        with open('/proc/version') as f:


            if 'WSL' in f.read() or 'microsoft' in f.read().lower():


                return 'wsl'


    except:


        pass


    if os.path.exists('/mnt/c') and os.path.exists('/usr/bin/wslvar'):


        return 'wsl'


    return 'linux'





ENV = detect_environment()

# 支持命令行参数: wechat_video_generator.py <content.json> [output_file]
if len(sys.argv) >= 3:
    _CLI_OUTPUT = sys.argv[2]
else:
    _CLI_OUTPUT = None





if ENV == 'windows':


    FFMPEG = 'C:\\\\ffmpeg\\\\ffmpeg-8.1.1-essentials_build\\\\bin\\\\ffmpeg.exe'


    ASSETS_BASE = Path(r'C:\Users\Administrator\.hermes\skills\wechat-video-generator')


    OUTPUT_DIR = Path(r'C:\Users\Administrator\Desktop\WeChatVideo输出')


    FONT_BOLD = 'C:/Windows/Fonts/msyhbd.ttc'


    FONT_REGULAR = 'C:/Windows/Fonts/msyh.ttc'


else:


    FFMPEG = '/usr/bin/ffmpeg'


    ASSETS_BASE = Path('/mnt/c/Users/Administrator/.hermes/skills/wechat-video-generator')


    OUTPUT_DIR = Path('/mnt/c/Users/Administrator/Desktop/WeChatVideo输出')


    FONT_BOLD = '/mnt/c/Windows/Fonts/msyhbd.ttc'


    FONT_REGULAR = '/mnt/c/Windows/Fonts/msyh.ttc'





os.makedirs(OUTPUT_DIR, exist_ok=True)





# ============================================================


# 2. 命令行参数


# ============================================================





if len(sys.argv) > 1:


    content_path = sys.argv[1]


else:


    content_path = ASSETS_BASE / 'content.json'





content = json.load(open(content_path, 'r', encoding='utf-8'))


skill_dir = ASSETS_BASE





# ============================================================


# 3. 视频参数 (CRF 0 = 无损)


# ============================================================





w, h = 1080, 1920


fps = 30


static_d, zoom_d = 2.9, 0.2


zoom_scale = 9.0


crf = 0          # 无损画质（CRF 0 = 绝对无损，适合素材质量高的情况）


img_y = 480


text_section_y = 1238





temp_dir = tempfile.mkdtemp()


images = content.get('images', [])[:3]





# ============================================================


# 4. 字体函数


# ============================================================





def get_font(s, b=False):


    font_path = FONT_BOLD if b else FONT_REGULAR


    try:


        return ImageFont.truetype(font_path, s)


    except Exception:


        try:


            return ImageFont.truetype(FONT_REGULAR, s)


        except:


            return ImageFont.load_default()





# ============================================================


# 5. 文本处理函数


# ============================================================





def wrap_text_by_pixels(text, font_size, max_pixels, font_bold=False):


    def get_char_width(char):


        try:


            bbox = get_font(font_size, font_bold).getbbox(char)


            return bbox[2] - bbox[0]


        except:


            return font_size * 0.7





    def is_breakable(char):


        if '\u4e00' <= char <= '\u9fff':


            return True


        if char in (' ', '-', '_', '，', '。', '、', '；', '：', '！', '？', ',', '.', ';', ':', '!', '?', ')'):


            return True


        return False





    result_lines, current_line, current_width = [], "", 0


    for char in text:


        char_w = get_char_width(char)


        if current_width + char_w > max_pixels and current_line:


            break_idx = -1


            for j in range(len(current_line) - 1, -1, -1):


                if is_breakable(current_line[j]):


                    break_idx = j


                    break


            if break_idx >= 0:


                result_lines.append(current_line[:break_idx+1])


                current_line = current_line[break_idx+1:]


                current_width = sum(get_char_width(c) for c in current_line)


            else:


                space_idx = current_line.rfind(' ')


                if space_idx > 0:


                    result_lines.append(current_line[:space_idx])


                    current_line = current_line[space_idx+1:]


                    current_width = sum(get_char_width(c) for c in current_line)


                else:


                    result_lines.append(current_line)


                    current_line = ""


                    current_width = 0


            current_line += char


            current_width += char_w


        else:


            current_line += char


            current_width += char_w





    if current_line:


        result_lines.append(current_line)


    return result_lines if result_lines else [""]





def wrap(t, m):


    lines, cur = [], ""


    for c in t:


        cur += c


        if len(cur) >= m:


            lines.append(cur)


            cur = ""


    if cur:


        lines.append(cur)


    return lines





# ============================================================


# 6. 绘图函数


# ============================================================





def draw_round(draw, xy, r, fill):


    x1, y1, x2, y2 = xy


    r = min(r, (x2-x1)//2, (y2-y1)//2)


    if r <= 0:


        return


    draw.rectangle([x1+r, y1, x2-r, y2], fill=fill)


    draw.rectangle([x1, y1+r, x2, y2-r], fill=fill)


    for dx, dy in [(0, 0), (x2-x1-2*r, 0), (0, y2-y1-2*r), (x2-x1-2*r, y2-y1-2*r)]:


        draw.ellipse([x1+dx, y1+dy, x1+dx+r*2, y1+dy+r*2], fill=fill)





def text_img(text, width, fs, bold, tc, bc, op, r, pad, mc, line_spacing=1.0, fit_text=False, stroke_width=0, stroke_color='#000000'):


    font = get_font(fs, bold)


    max_pixels = width - 300


    lines = wrap_text_by_pixels(text, fs, max_pixels, bold)


    tmp = Image.new('RGBA', (1, 1))


    dr = ImageDraw.Draw(tmp)





    line_heights, line_widths = [], []


    for ln in lines:


        bbox = dr.textbbox((0, 0), ln, font=font)


        line_widths.append(bbox[2] - bbox[0])


        line_heights.append(bbox[3] - bbox[1])





    avg_lh = int(fs * line_spacing)


    total_height = len(lines) * avg_lh + pad * 2





    if fit_text:


        img = Image.new('RGBA', (width, total_height), (0, 0, 0, 0))


        draw = ImageDraw.Draw(img)


        trgb = tuple(int(tc[i:i+2], 16) for i in (1, 3, 5))


        brgb = tuple(int(bc[i:i+2], 16) for i in (1, 3, 5)) + (int(255 * op),)


        for i, ln in enumerate(lines):


            y = pad + i * avg_lh


            lw = line_widths[i]


            text_h = line_heights[i]


            bg_x1 = (width - lw) // 2 - pad


            bg_x2 = bg_x1 + lw + pad * 2


            bg_h = text_h + pad * 1.2


            bg_y1 = y + (avg_lh - bg_h) // 2


            bg_y2 = bg_y1 + bg_h


            draw_round(draw, [bg_x1, bg_y1, bg_x2, bg_y2], r, brgb)


            text_y = bg_y1 + pad * 0.2


            cx = (width - lw) // 2


            if stroke_width > 0:


                srgb = tuple(int(stroke_color[i:i+2], 16) for i in (1, 3, 5))


                draw.text((cx, text_y), ln, font=font, fill=srgb)


                for dx in (-stroke_width, stroke_width):


                    for dy in (-stroke_width, stroke_width):


                        if dx != 0 or dy != 0:


                            draw.text((cx + dx, text_y + dy), ln, font=font, fill=srgb)


            draw.text((cx, text_y), ln, font=font, fill=trgb)


    else:


        mw = max(line_widths) if line_widths else 0


        bw = min(mw + pad * 2, width - 200)


        bh = total_height


        img = Image.new('RGBA', (width, bh), (0, 0, 0, 0))


        draw = ImageDraw.Draw(img)


        x1 = (width - bw) // 2


        brgb = tuple(int(bc[i:i+2], 16) for i in (1, 3, 5)) + (int(255 * op),)


        draw_round(draw, [x1, 0, x1 + bw, bh], r, brgb)


        trgb = tuple(int(tc[i:i+2], 16) for i in (1, 3, 5))


        for i, ln in enumerate(lines):


            y = pad + i * avg_lh


            bbox = draw.textbbox((0, 0), ln, font=font)


            text_y = y + (avg_lh - (bbox[3] - bbox[1])) // 2


            cx = (width - (bbox[2]-bbox[0])) // 2


            if stroke_width > 0:


                srgb = tuple(int(stroke_color[i:i+2], 16) for i in (1, 3, 5))


                draw.text((cx, text_y), ln, font=font, fill=srgb)


                for dx in (-stroke_width, stroke_width):


                    for dy in (-stroke_width, stroke_width):


                        if dx != 0 or dy != 0:


                            draw.text((cx + dx, text_y + dy), ln, font=font, fill=srgb)


            draw.text((cx, text_y), ln, font=font, fill=trgb)





    return img





def create_bg(idx):


    bg = str(skill_dir / 'assets' / 'backgrounds' / 'ai_not_cool_bg.jpg')


    frame = Image.open(bg).convert('RGBA').resize((w, h)) if os.path.exists(bg) else Image.new('RGBA', (w, h), (26, 26, 26, 255))





    offset_y = 100





    # --- Logo: 80x80 圆形，无3D效果，边缘羽化 ---
    logo = str(skill_dir / 'assets' / 'logos' / 'ai_not_cool_logo.jpg')
    if os.path.exists(logo):
        try:
            l = Image.open(logo).convert('RGBA')
            l = ImageOps.fit(l, (80, 80), Image.Resampling.LANCZOS)
            # 用径向渐变做柔和圆形遮罩（衰减范围收窄，边缘更 crisp）
            size = 80
            center = size // 2
            feather = 4  # 边缘羽化范围（像素），越小越 crisp
            mask = Image.new('L', (size, size), 0)
            for y in range(size):
                for x in range(size):
                    dist = ((x - center) ** 2 + (y - center) ** 2) ** 0.5
                    if dist < center:
                        # 在 center - feather 到 center 之间渐变到 0
                        if dist >= center - feather:
                            alpha = int(255 * (center - dist) / feather)
                        else:
                            alpha = 255
                        mask.putpixel((x, y), max(0, alpha))
            l.putalpha(mask)
            frame.paste(l, ((w - 80) // 2, 20 + offset_y), l)
        except Exception as e:
            import traceback
            print(f"LOGO ERROR: {e}")
            traceback.print_exc()



    # --- 文字 ---


    mt = content.get('main_title', '')


    st = content.get('sub_title', '')


    txts = content.get('text_sections', [])[:3]





    mt_lines = wrap_text_by_pixels(mt, 72, 1000, True)[:3]


    mt_text = '\n'.join(mt_lines) if mt_lines else ''





    st_lines = wrap_text_by_pixels(st, 48, 1000, True)[:2]


    st_text = '\n'.join(st_lines) if st_lines else ''





    mi = text_img(mt_text, w, 72, True, '#FFFFFF', '#000000', 0.7, 20, 25, 20, stroke_width=4, stroke_color='#000000')


    frame.paste(mi, (0, 118 + offset_y), mi)





    mh = mi.height





    si = text_img(st_text, w, 48, True, '#000000', '#FFD700', 0.9, 20, 20, 20, line_spacing=1.0)


    frame.paste(si, (0, 118 + offset_y + mh + 10), si)





    if idx < len(txts):
        ti = text_img(txts[idx], w, 48, True, '#FFFFFF', '#000000', 0.7, 20, 25, 20, line_spacing=1.8, fit_text=True)
        frame.paste(ti, (0, text_section_y), ti)





    return frame





# ============================================================


# 7. 执行生成


# ============================================================





print(f"[{ENV}] Creating {len(images)} scenes...")





scenes = []





for i in range(len(images)):


    if not os.path.exists(images[i]):


        print(f"  Skip {i+1}: file not found - {images[i]}")


        continue


    is_last = (i == len(images) - 1)


    print(f"\nScene {i+1}")





    frame_dir = os.path.join(temp_dir, f'f{i}')


    os.makedirs(frame_dir, exist_ok=True)


    bg = create_bg(i)





    img_h = int(h * 0.38)





    if is_last:


        total = int(2.8 * fps)


        print(f"  {total} static frames")


        img = Image.open(images[i]).convert('RGBA')


        # 裁剪图片比例以匹配目标区域（填满，无黑边）
        target_ratio = w / img_h
        img_ratio = img.width / img.height
        if img_ratio > target_ratio:
            # 图片太宽：左右裁掉多余部分
            new_img_w = int(img.height * target_ratio)
            left = (img.width - new_img_w) // 2
            img = img.crop((left, 0, left + new_img_w, img.height))
        else:
            # 图片太高：上下裁掉多余部分
            new_img_h = int(img.width / target_ratio)
            top = (img.height - new_img_h) // 2
            img = img.crop((0, top, img.width, top + new_img_h))


        # 缩放到目标尺寸
        z = img.resize((w, img_h), Image.Resampling.LANCZOS)
        c = z


        for f in range(total):


            composed = bg.copy()


            composed.paste(c, (0, img_y))


            composed.save(os.path.join(frame_dir, f'fr_{f:04d}.png'))


    else:


        static_f = int(static_d * fps)


        zoom_f = int(zoom_d * fps)


        total = static_f + zoom_f


        print(f"  {static_f} static + {zoom_f} zoom = {total} frames")





        img = Image.open(images[i]).convert('RGBA')


        # 裁剪图片比例以匹配目标区域（填满，无黑边）
        target_ratio = w / img_h
        img_ratio = img.width / img.height
        if img_ratio > target_ratio:
            # 图片太宽：左右裁掉多余部分
            new_img_w = int(img.height * target_ratio)
            left = (img.width - new_img_w) // 2
            img = img.crop((left, 0, left + new_img_w, img.height))
        else:
            # 图片太高：上下裁掉多余部分
            new_img_h = int(img.width / target_ratio)
            top = (img.height - new_img_h) // 2
            img = img.crop((0, top, img.width, top + new_img_h))


        # 缩放到目标尺寸
        z = img.resize((w, img_h), Image.Resampling.LANCZOS)
        c = z





        for f in range(static_f):


            composed = bg.copy()


            composed.paste(c, (0, img_y))


            composed.save(os.path.join(frame_dir, f'fr_{f:04d}.png'))





        for f in range(zoom_f):


            progress = f / zoom_f


            zoom = 1 + zoom_scale * progress


            alpha = 1 - progress


            # 基于裁剪后的 img 做 zoom 动效
            zoomed_w = int(w * zoom)


            zoomed_h = int(img_h * zoom)


            z = img.resize((zoomed_w, zoomed_h), Image.Resampling.LANCZOS)


            left = (zoomed_w - w) // 2


            top = (zoomed_h - img_h) // 2


            c = z.crop((left, top, left + w, top + img_h))


            if alpha < 1:


                c = c.convert('RGBA')


                c.putalpha(Image.new('L', c.size, int(255 * alpha)))


            composed = bg.copy()


            composed.paste(c, (0, img_y), c if alpha < 1 else None)


            composed.save(os.path.join(frame_dir, f'fr_{static_f + f:04d}.png'))





    scene = os.path.join(temp_dir, f's{i}.mp4')


    subprocess.run([


        FFMPEG, '-y',


        '-framerate', str(fps),


        '-i', os.path.join(frame_dir, 'fr_%04d.png'),


        '-c:v', 'libx264', '-pix_fmt', 'yuv444p',


        '-crf', str(crf), '-preset', 'medium',


        scene


    ], capture_output=True, check=True)


    scenes.append(scene)


    print(f"  Scene done")





# ============================================================


# 8. 合并场景


# ============================================================





print("\nConcatenating scenes...")


main_title = content.get('main_title', 'video')


safe_title = re.sub(r'[\\/*?:"<>|]', '', main_title)


if len(safe_title) > 50:


    safe_title = safe_title[:50]


if _CLI_OUTPUT:
    output = _CLI_OUTPUT
else:
    output = str(OUTPUT_DIR / f'{safe_title}.mp4')





final_txt = os.path.join(temp_dir, 'final.txt')


with open(final_txt, 'w') as f:


    for s in scenes:


        escaped = s.replace('\\', '/')


        f.write(f"file '{escaped}'\n")





subprocess.run([


    FFMPEG, '-y',


    '-f', 'concat', '-safe', '0', '-i', final_txt,


    '-c:v', 'libx264', '-crf', str(crf), '-pix_fmt', 'yuv444p',


    '-preset', 'medium', '-c:a', 'copy',


    output


], capture_output=True, check=True)





print(f"\n✓ Video saved: {output}")





# ============================================================


# 9. 添加背景音乐


# ============================================================





bgm = str(skill_dir / 'assets' / 'music' / 'ai_not_cool_bgm.mp3')


if os.path.exists(bgm) and os.path.exists(output):


    print("Adding background music...")


    temp_out = output.replace('.mp4', '_temp.mp4')


    result = subprocess.run([


        FFMPEG, '-y', '-i', output, '-i', bgm,


        '-filter_complex', '[1:a]volume=0.3[a]',


        '-map', '0:v', '-map', '[a]',


        '-c:v', 'copy', '-c:a', 'aac', '-shortest',


        temp_out


    ], capture_output=True)


    if os.path.exists(temp_out):


        try:


            os.remove(output)


            os.rename(temp_out, output)


            print("  Music added")


        except Exception as e:


            print(f"  Music add failed: {e}")





shutil.rmtree(temp_dir, ignore_errors=True)


