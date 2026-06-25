import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

# src/text_overlay_mcp/renderer.py -> src/text_overlay_mcp -> src -> Text_Overlay_MCP -> fonts
FONTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "fonts"))

# 值为 (文件名, variable-font 命名实例) 或仅文件名（静态字体）。
# variable-font 命名实例在加载后通过 set_variation_by_name() 选择对应字重。
FONT_FILES = {
    # bold display / "edit" titles
    "anton": "Anton-Regular.ttf",
    "bebas-neue": "BebasNeue-Regular.ttf",
    "montserrat-extrabold": ("Montserrat-Variable.ttf", "ExtraBold"),
    "poppins-extrabold": "Poppins-ExtraBold.ttf",
    "oswald-bold": ("Oswald-Variable.ttf", "Bold"),
    "archivo-black": "ArchivoBlack-Regular.ttf",
    "russo-one": "RussoOne-Regular.ttf",
    "black-ops-one": "BlackOpsOne-Regular.ttf",
    "bungee": "Bungee-Regular.ttf",
    "teko-bold": ("Teko-Variable.ttf", "SemiBold"),
    "roboto-condensed-bold": ("RobotoCondensed-Variable.ttf", "Bold"),
    "inter-black": ("Inter-Variable.ttf", "Black"),
    "fredoka-bold": ("Fredoka-Variable.ttf", "Bold"),
    "open-sans-bold": ("OpenSans-Variable.ttf", "Bold"),
    # playful / comic / display
    "bangers": "Bangers-Regular.ttf",
    "lobster": "Lobster-Regular.ttf",
    # script / handwritten
    "pacifico": "Pacifico-Regular.ttf",
    "permanent-marker": "PermanentMarker-Regular.ttf",
    "dancing-script-bold": ("DancingScript-Variable.ttf", "Bold"),
    "caveat-bold": ("Caveat-Variable.ttf", "Bold"),
    # serif (captions / narration style)
    "playfair-display-bold": ("PlayfairDisplay-Variable.ttf", "Bold"),
    "lora-bold": ("Lora-Variable.ttf", "Bold"),
    "merriweather-bold": ("Merriweather-Variable.ttf", "Bold"),
    "pt-serif-bold": "PTSerif-Bold.ttf",
}


def list_fonts():
    return sorted(FONT_FILES.keys())


def _font_entry(name):
    key = (name or "anton").lower().strip()
    if key not in FONT_FILES:
        raise ValueError(f"未知字体: {name}，可用字体: {list(FONT_FILES.keys())}")
    return FONT_FILES[key]


def _load_font(name, size):
    entry = _font_entry(name)
    if isinstance(entry, tuple):
        filename, variation = entry
        font = ImageFont.truetype(os.path.join(FONTS_DIR, filename), size)
        try:
            font.set_variation_by_name(variation)
        except Exception:
            pass
        return font
    return ImageFont.truetype(os.path.join(FONTS_DIR, entry), size)


def _parse_color(c):
    if isinstance(c, (tuple, list)) and not isinstance(c, str):
        if len(c) == 3:
            return (int(c[0]), int(c[1]), int(c[2]), 255)
        return tuple(int(x) for x in c)
    c = str(c).strip().lstrip("#")
    if len(c) == 6:
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
        return (r, g, b, 255)
    if len(c) == 8:
        r, g, b, a = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), int(c[6:8], 16)
        return (r, g, b, a)
    raise ValueError(f"无法解析颜色: {c}")


def _gradient_rgba(size, color1, color2, direction="vertical"):
    w, h = max(size[0], 1), max(size[1], 1)
    c1 = _parse_color(color1)
    c2 = _parse_color(color2)
    base = Image.new("RGBA", (w, h))
    px = base.load()
    if direction == "horizontal":
        for x in range(w):
            t = x / max(w - 1, 1)
            col = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(4))
            for y in range(h):
                px[x, y] = col
    else:
        for y in range(h):
            t = y / max(h - 1, 1)
            col = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(4))
            for x in range(w):
                px[x, y] = col
    return base


def _text_masks(text, font, ox, oy, w, h, outline_width):
    interior = Image.new("L", (w, h), 0)
    ImageDraw.Draw(interior).text((ox, oy), text, font=font, fill=255)
    if outline_width > 0:
        full = Image.new("L", (w, h), 0)
        ImageDraw.Draw(full).text((ox, oy), text, font=font, fill=255,
                                   stroke_width=outline_width, stroke_fill=255)
        ring = ImageChops.subtract(full, interior)
    else:
        full = interior
        ring = Image.new("L", (w, h), 0)
    return interior, ring, full


def render_text_block(text, font, color, outline_color=None, outline_width=0,
                       shadow=False, shadow_offset=(6, 6), shadow_blur=4):
    """
    渲染单个文字片段（一个词或一行）为带透明背景的 RGBA 图像。

    color: 单一颜色 (hex字符串) 或长度为2的 [color1, color2] 渐变（垂直方向，从上到下）
    outline_color/outline_width: 描边颜色和宽度（像素），0表示不描边
    shadow: 是否添加投影
    """
    dummy = Image.new("RGBA", (10, 10))
    bbox = ImageDraw.Draw(dummy).textbbox((0, 0), text, font=font, stroke_width=outline_width)
    pad = outline_width + 4 + (shadow_blur * 2 if shadow else 0)
    w = (bbox[2] - bbox[0]) + pad * 2
    h = (bbox[3] - bbox[1]) + pad * 2
    ox, oy = pad - bbox[0], pad - bbox[1]

    interior, ring, full = _text_masks(text, font, ox, oy, w, h, outline_width)

    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    if shadow:
        sx, sy = shadow_offset
        shadow_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        black = Image.new("RGBA", (w, h), (0, 0, 0, 200))
        shadow_layer = Image.composite(black, shadow_layer, full)
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(shadow_blur))
        shadow_layer = ImageChops.offset(shadow_layer, sx, sy)
        layer = Image.alpha_composite(layer, shadow_layer)

    if outline_width > 0 and outline_color is not None:
        oc = _parse_color(outline_color)
        outline_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        outline_rgb = Image.new("RGBA", (w, h), oc)
        outline_layer = Image.composite(outline_rgb, outline_layer, ring)
        layer = Image.alpha_composite(layer, outline_layer)

    fill_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if isinstance(color, list) and len(color) == 2:
        grad = _gradient_rgba((w, h), color[0], color[1], "vertical")
        fill_layer = Image.composite(grad, fill_layer, interior)
    else:
        fc = _parse_color(color)
        fill_rgb = Image.new("RGBA", (w, h), fc)
        fill_layer = Image.composite(fill_rgb, fill_layer, interior)
    layer = Image.alpha_composite(layer, fill_layer)

    return layer


def _word_alpha(idx, total, progress, animation):
    if total == 0 or animation == "none":
        return 1.0
    if animation == "fade":
        return max(0.0, min(1.0, progress / 0.15))
    if animation == "word_by_word":
        seg = 1.0 / total
        fade = min(seg, 0.4)
        start = idx * seg
        if fade <= 0:
            return 1.0 if progress >= start else 0.0
        return max(0.0, min(1.0, (progress - start) / fade))
    if animation == "typewriter":
        seg = 1.0 / total
        return 1.0 if progress >= (idx + 1) * seg - seg * 0.3 else 0.0
    return 1.0


def render_karaoke_frame(canvas_size, words, t, font_name="anton", font_size=60,
                          color="#FFFFFF", highlight_color="#FFD700",
                          outline_color="#000000", outline_width=4, shadow=False,
                          position="bottom"):
    """
    渲染一帧"卡拉OK"字幕：words 为当前行的单词列表 [{word, start, end}, ...]，
    已经开始播放(t >= word.start)的词使用 highlight_color 高亮，其余词使用 color。

    position: "top" | "center" | "bottom" (默认)
    """
    cw, ch = canvas_size
    font = _load_font(font_name, font_size)

    space_bbox = font.getbbox(" ")
    space_w = (space_bbox[2] - space_bbox[0]) if space_bbox else font_size // 3
    if space_w <= 0:
        space_w = font_size // 3

    rendered = []
    for w in words:
        fill = highlight_color if t >= w["start"] else color
        rendered.append(render_text_block(w["word"], font, fill, outline_color, outline_width, shadow))

    canvas = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    if not rendered:
        return canvas

    line_w = sum(img.width for img in rendered) + space_w * (len(rendered) - 1)
    line_h = max(img.height for img in rendered)

    if position == "top":
        y = int(ch * 0.08)
    elif position == "center":
        y = (ch - line_h) // 2
    else:
        y = ch - int(ch * 0.1) - line_h

    x = (cw - line_w) // 2
    for img in rendered:
        canvas.alpha_composite(img, (x, y + (line_h - img.height) // 2))
        x += img.width + space_w

    return canvas


def render_frame(canvas_size, text, font_name="anton", font_size=80, color="#FFFFFF",
                  outline_color="#000000", outline_width=0, shadow=False,
                  position="center", progress=1.0, animation="word_by_word",
                  line_spacing=1.2):
    """
    渲染一帧叠加层（RGBA，尺寸与视频画布相同）。

    text: 文本内容，可用 "\\n" 分多行
    progress: 当前帧在整个叠加动画中的进度 0.0~1.0
    animation: "none" | "fade" | "word_by_word" | "typewriter"
    position: "top" | "center" | "bottom"
    """
    cw, ch = canvas_size
    font = _load_font(font_name, font_size)

    lines = [ln for ln in text.split("\n")]
    all_words = []
    for li, line in enumerate(lines):
        for w in line.split(" "):
            if w:
                all_words.append((li, w))
    total = len(all_words)

    rendered = {}
    for idx, (li, w) in enumerate(all_words):
        rendered[idx] = render_text_block(w, font, color, outline_color, outline_width, shadow)

    space_bbox = font.getbbox(" ")
    space_w = (space_bbox[2] - space_bbox[0]) if space_bbox else font_size // 3
    if space_w <= 0:
        space_w = font_size // 3

    li_to_words = {}
    for idx, (li, w) in enumerate(all_words):
        li_to_words.setdefault(li, []).append(idx)

    canvas = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))

    line_order = sorted(li_to_words)
    line_heights = []
    line_widths = []
    for li in line_order:
        idxs = li_to_words[li]
        h = max(rendered[i].height for i in idxs)
        wsum = sum(rendered[i].width for i in idxs) + space_w * (len(idxs) - 1)
        line_heights.append(h)
        line_widths.append(wsum)

    extra_spacing = int(font_size * (line_spacing - 1))
    total_h = sum(line_heights) + extra_spacing * max(len(line_heights) - 1, 0)

    if position == "top":
        y = int(ch * 0.08)
    elif position == "bottom":
        y = ch - int(ch * 0.08) - total_h
    else:
        y = (ch - total_h) // 2

    for li_idx, li in enumerate(line_order):
        idxs = li_to_words[li]
        lw = line_widths[li_idx]
        lh = line_heights[li_idx]
        x = (cw - lw) // 2
        for idx in idxs:
            img = rendered[idx]
            alpha = _word_alpha(idx, total, progress, animation)
            if alpha < 1.0:
                if alpha <= 0.0:
                    x += img.width + space_w
                    continue
                img = img.copy()
                a = img.split()[3].point(lambda p, al=alpha: int(p * al))
                img.putalpha(a)
            canvas.alpha_composite(img, (x, y + (lh - img.height) // 2))
            x += img.width + space_w
        y += lh + extra_spacing

    return canvas
