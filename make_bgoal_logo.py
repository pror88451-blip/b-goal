import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ASSET_DIR = Path("assets")
LOGO_PATH = ASSET_DIR / "bgoal_world_ball_logo.png"
BACKGROUND_PATH = ASSET_DIR / "bgoal_app_background.png"


def star_points(cx, cy, outer, inner, points=5, rotation=-math.pi / 2):
    coords = []
    for index in range(points * 2):
        radius = outer if index % 2 == 0 else inner
        angle = rotation + index * math.pi / points
        coords.append((cx + math.cos(angle) * radius, cy + math.sin(angle) * radius))
    return coords


def add_glow(base, center, radius, color):
    glow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    for scale, alpha in [(2.6, 36), (1.8, 58), (1.1, 90)]:
        r = radius * scale
        draw.ellipse(
            (center[0] - r, center[1] - r, center[0] + r, center[1] + r),
            fill=(*color, alpha),
        )
    base.alpha_composite(glow.filter(ImageFilter.GaussianBlur(18)))


def draw_wave(draw, points, fill, outline=(230, 184, 84, 230), width=5):
    draw.polygon(points, fill=fill)
    draw.line(points + [points[0]], fill=outline, width=width, joint="curve")


def make_background_from_logo(logo):
    bg = Image.new("RGBA", (1200, 800), (245, 248, 244, 255))
    bgd = ImageDraw.Draw(bg)
    for y in range(800):
        shade = int(248 - y * 0.035)
        bgd.line((0, y, 1200, y), fill=(245, shade, 244, 255))

    bg_logo = logo.resize((620, 620), Image.Resampling.LANCZOS)
    bg_logo = bg_logo.filter(ImageFilter.GaussianBlur(0.1))
    bg.alpha_composite(bg_logo, (650, 98))

    veil = Image.new("RGBA", bg.size, (245, 248, 244, 132))
    bg.alpha_composite(veil)
    bg.save(BACKGROUND_PATH)


def make_logo():
    ASSET_DIR.mkdir(exist_ok=True)

    size = 1024
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.ellipse((198, 220, 826, 848), fill=(9, 30, 24, 100))
    shadow = shadow.filter(ImageFilter.GaussianBlur(34))
    img.alpha_composite(shadow)

    ball = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(ball)
    bounds = (178, 166, 846, 834)
    draw.ellipse(bounds, fill=(252, 252, 248, 255), outline=(12, 14, 15, 255), width=10)

    mask = Image.new("L", (size, size), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse(bounds, fill=255)

    star_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sd = ImageDraw.Draw(star_layer)
    stars = [
        (512, 272, 70, 30, 0),
        (332, 374, 48, 21, 0.25),
        (692, 374, 48, 21, -0.25),
        (302, 602, 45, 19, -0.05),
        (722, 602, 45, 19, 0.05),
        (512, 742, 52, 22, 0),
    ]
    for cx, cy, outer, inner, rotation in stars:
        sd.polygon(
            star_points(cx, cy, outer, inner, rotation=-math.pi / 2 + rotation),
            fill=(10, 12, 14, 255),
        )

    star_layer.putalpha(mask)
    ball.alpha_composite(star_layer)

    seam = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sm = ImageDraw.Draw(seam)
    sm.arc((226, 220, 798, 804), 124, 236, fill=(24, 26, 28, 55), width=5)
    sm.arc((226, 220, 798, 804), -56, 56, fill=(24, 26, 28, 55), width=5)
    sm.arc((304, 196, 720, 856), 72, 108, fill=(24, 26, 28, 48), width=5)
    sm.arc((304, 196, 720, 856), 252, 288, fill=(24, 26, 28, 48), width=5)
    seam.putalpha(mask)
    ball.alpha_composite(seam)

    highlight = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    hd = ImageDraw.Draw(highlight)
    hd.ellipse((286, 226, 500, 382), fill=(255, 255, 255, 82))
    highlight = highlight.filter(ImageFilter.GaussianBlur(22))
    highlight.putalpha(mask)
    ball.alpha_composite(highlight)

    add_glow(ball, (414, 470), 44, (35, 178, 255))
    add_glow(ball, (610, 470), 44, (35, 178, 255))

    face = ImageDraw.Draw(ball)
    for cx in [414, 610]:
        face.ellipse((cx - 38, 432, cx + 38, 512), fill=(5, 38, 91, 255))
        face.ellipse((cx - 25, 447, cx + 25, 501), fill=(38, 178, 255, 255))
        face.ellipse((cx - 11, 458, cx + 12, 481), fill=(230, 250, 255, 255))

    try:
        font = ImageFont.truetype("arialbd.ttf", 250)
    except OSError:
        font = ImageFont.load_default()

    mouth = Image.new("RGBA", (320, 320), (0, 0, 0, 0))
    mouth_draw = ImageDraw.Draw(mouth)
    mouth_draw.text((30, 15), "D", fill=(255, 255, 255, 255), font=font, stroke_width=12, stroke_fill=(8, 10, 12, 255))
    mouth = mouth.rotate(-90, expand=True, resample=Image.Resampling.BICUBIC)
    ball.alpha_composite(mouth, (355, 506))

    img.alpha_composite(ball)
    img.save(LOGO_PATH)
    make_background_from_logo(img)

    print(LOGO_PATH)
    print(BACKGROUND_PATH)


if __name__ == "__main__":
    make_logo()
