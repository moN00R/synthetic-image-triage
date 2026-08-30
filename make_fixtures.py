"""Create provenance test fixtures from any image you already have.

    python make_fixtures.py samples/kodim01.png

Writes into samples/prov/:
    clean.jpg          no marking at all            -> no_marking_found
    exif_software.jpg  EXIF Software tag            -> marked
    exif_desc.jpg      EXIF ImageDescription tag    -> marked
    xmp.jpg            XMP packet                   -> marked
    c2pa_like.jpg      JUMBF/c2pa box in the bytes  -> marked
    stripped.jpg       exif_software.jpg re-saved without metadata -> no_marking_found
    png_text.png       PNG tEXt chunk (how SD/ComfyUI tag output)  -> ?
"""

import os
import sys

from PIL import Image
from PIL.PngImagePlugin import PngInfo

OUT = "samples/prov"

XMP = (
    b'<?xpacket begin="\xef\xbb\xbf" id="W5M0MpCehiHzreSzNTczkc9d"?>'
    b'<x:xmpmeta xmlns:x="adobe:ns:meta/">'
    b'<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
    b'<rdf:Description xmlns:dc="http://purl.org/dc/elements/1.1/">'
    b'<dc:creator>Some AI Model v2</dc:creator>'
    b'</rdf:Description></rdf:RDF></x:xmpmeta><?xpacket end="w"?>'
)


def main(src):
    os.makedirs(OUT, exist_ok=True)
    im = Image.open(src).convert("RGB").resize((512, 512))

    im.save(f"{OUT}/clean.jpg", quality=90)

    ex1 = im.getexif()
    ex1[0x0131] = "Stable Diffusion WebUI v1.9"       # Software
    im.save(f"{OUT}/exif_software.jpg", exif=ex1, quality=90) 

    ex2 = im.getexif()
    ex2 = im.getexif()
    ex2.pop(0x0131, None)                             # clear Software from the shared cache
    ex2[0x010E] = "Generated with a diffusion model" # ImageDescription
    im.save(f"{OUT}/exif_desc.jpg", exif=ex2, quality=90)

    try:
        im.save(f"{OUT}/xmp.jpg", xmp=XMP, quality=90)
    except TypeError:
        # older Pillow: splice an APP1 XMP segment in by hand
        raw = open(f"{OUT}/clean.jpg", "rb").read()
        seg = b"http://ns.adobe.com/xap/1.0/\x00" + XMP
        app1 = b"\xff\xe1" + (len(seg) + 2).to_bytes(2, "big") + seg
        open(f"{OUT}/xmp.jpg", "wb").write(raw[:2] + app1 + raw[2:])

    # A JUMBF-style box carrying a c2pa label, spliced in as APP11.
    box = b"\x00\x00\x00\x20jumb" + b"\x00\x00\x00\x18jumd" + b"c2pa" + b"\x00" * 12
    raw = open(f"{OUT}/clean.jpg", "rb").read()
    app11 = b"\xff\xeb" + (len(box) + 2).to_bytes(2, "big") + box
    open(f"{OUT}/c2pa_like.jpg", "wb").write(raw[:2] + app11 + raw[2:])

    # Re-encoding through a fresh Image drops every metadata block.
    with Image.open(f"{OUT}/exif_software.jpg") as m:
        Image.fromarray(__import__("numpy").array(m)).save(
            f"{OUT}/stripped.jpg", quality=90)

    benign = PngInfo()
    benign.add_text("Comment", "Scanned from 35mm negative, Kodak PCD0992")
    benign.add_text("Author", "A Human Photographer")
    im.save(f"{OUT}/benign_png_text.png", pnginfo=benign)

    gen = PngInfo()
    gen.add_text("parameters",
                 "a photo of a cat, Steps: 30, Sampler: DPM++ 2M, CFG scale: 7, "
                 "Model: sd_xl_base_1.0")
    im.save(f"{OUT}/png_text.png", pnginfo=gen)

    for f in sorted(os.listdir(OUT)):
        print(f"  {OUT}/{f}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "samples/kodim01.png")