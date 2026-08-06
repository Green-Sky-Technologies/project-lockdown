"""Generate the Project Lockdown store/extension icon set.

A padlock (on-brand for "Lockdown") in white on a brand-green rounded tile.
Drawn on a large canvas and downscaled with LANCZOS so the small sizes stay crisp.
"""
import os
from PIL import Image, ImageDraw

OUT = "/Users/mitchell/projects/project-lockdown/extension/icons"
STORE = "/Users/mitchell/projects/project-lockdown/extension/store-assets"
os.makedirs(OUT, exist_ok=True)
os.makedirs(STORE, exist_ok=True)

S = 1024  # master canvas
GREEN_TOP = (18, 183, 143)   # a touch brighter at top
GREEN_BOT = (13, 138, 107)   # deeper at bottom  (#0D8A6B)
WHITE = (255, 255, 255)


def rounded_mask(size, radius):
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return m


def vertical_gradient(size, top, bot):
    grad = Image.new("RGB", (1, size))
    for y in range(size):
        t = y / (size - 1)
        grad.putpixel((0, y), tuple(round(top[i] + (bot[i] - top[i]) * t) for i in range(3)))
    return grad.resize((size, size))


img = Image.new("RGBA", (S, S), (0, 0, 0, 0))

# Background: green gradient clipped to a rounded tile.
bg = vertical_gradient(S, GREEN_TOP, GREEN_BOT).convert("RGBA")
img.paste(bg, (0, 0), rounded_mask(S, radius=round(S * 0.235)))

d = ImageDraw.Draw(img)

# Padlock geometry (centered).
cx = S // 2
body_w, body_h = round(S * 0.52), round(S * 0.40)
body_x0 = cx - body_w // 2
body_y0 = round(S * 0.46)
body_x1 = body_x0 + body_w
body_y1 = body_y0 + body_h
body_r = round(body_w * 0.16)

# Shackle: an open ring (top half) sitting on the body, with straight legs.
shackle_r = round(S * 0.155)   # outer radius of the arc centerline
shackle_w = round(S * 0.085)   # stroke thickness
shackle_cy = body_y0 + round(S * 0.01)
leg_len = round(S * 0.10)
# straight legs
for sx in (cx - shackle_r, cx + shackle_r):
    d.line([(sx, shackle_cy), (sx, shackle_cy + leg_len)], fill=WHITE, width=shackle_w)
    d.ellipse([sx - shackle_w // 2, shackle_cy + leg_len - shackle_w // 2,
               sx + shackle_w // 2, shackle_cy + leg_len + shackle_w // 2], fill=WHITE)
# top arc
bbox = [cx - shackle_r, shackle_cy - shackle_r, cx + shackle_r, shackle_cy + shackle_r]
d.arc(bbox, start=180, end=360, fill=WHITE, width=shackle_w)

# Body.
d.rounded_rectangle([body_x0, body_y0, body_x1, body_y1], radius=body_r, fill=WHITE)

# Keyhole (cut back to the green beneath) — circle + tapered slot.
kh_cx = cx
kh_cy = body_y0 + round(body_h * 0.42)
kh_r = round(S * 0.055)
key_color = GREEN_BOT
d.ellipse([kh_cx - kh_r, kh_cy - kh_r, kh_cx + kh_r, kh_cy + kh_r], fill=key_color)
slot_top = kh_cy
slot_bot = kh_cy + round(S * 0.11)
d.polygon(
    [(kh_cx - round(kh_r * 0.55), slot_top),
     (kh_cx + round(kh_r * 0.55), slot_top),
     (kh_cx + round(kh_r * 0.30), slot_bot),
     (kh_cx - round(kh_r * 0.30), slot_bot)],
    fill=key_color,
)

# Manifest-referenced sizes ship inside the extension.
for size in (128, 48, 32, 16):
    img.resize((size, size), Image.LANCZOS).save(os.path.join(OUT, f"icon-{size}.png"))
    print("wrote icons/icon-%d.png" % size)

# 128 store-listing icon (uploaded in the CWS dashboard, NOT bundled).
img.resize((128, 128), Image.LANCZOS).save(os.path.join(STORE, "store-icon-128.png"))
# A larger master for any promo art.
img.resize((512, 512), Image.LANCZOS).save(os.path.join(STORE, "icon-512.png"))
print("wrote store-assets/store-icon-128.png + icon-512.png")
