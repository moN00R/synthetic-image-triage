from  pathlib import Path
from PIL import Image 
from PIL.ExifTags import TAGS

BORING_INFO_KEYS = {
    "jfif", "jfif_version", "jfif_unit", "jfif_density", "dpi", "exif",
    "icc_profile", "xmp", "transparency", "gamma", "chromaticity", "srgb",
    "aspect", "adobe", "adobe_transform", "progression", "smooth",
    "interlace", "compression", "background", "resolution", "photoshop",
}
 
INTERESTING_EXIF_TAGS = {"Software", "ImageDescription", "Artist", "Copyright"}

C2PA_MARKERS = (b"c2pa", b"jumb")

GENERATOR_MARKERS = (
    "stable diffusion", "stable-diffusion", "dall-e", "dall·e", "midjourney",
    "comfyui", "automatic1111", "invokeai", "firefly", "imagen", "flux",
    "generated with", "ai-generated", "ai generated", "synthetic",
    "prompt", "sampler", "cfg scale", "denoising",
)

MAX_EVIDENCE = 200
 
 
def _marked(evidence):
    return {"status": "marked", "evidence": evidence[:MAX_EVIDENCE]}

def provenance_check(path):
    path = Path(path)
    with Image.open(path) as img:
        # EXIF tags that generators commonly write
        
        exif = img.getexif()
        for tag_id, value in exif.items():
            tag_name = TAGS.get(tag_id, tag_id)

            if tag_name in INTERESTING_EXIF_TAGS and value:
                return _marked(f"EXIF {tag_name}: {value}")

        # XMP. JPEG gives bytes, PNG gives str - normalise both
        xmp = img.info.get('xmp') or img.info.get("XML:com.adobe.xmp") 
        if xmp:
            text = xmp.decode("utf-8", 'ignore') if isinstance(xmp, bytes) else str(xmp)
            return _marked(f"XMP: {text}")

        # 3. PNG text chunks. Stable Diffusion WebUI, ComfyUI and similar tools write generation parameters here, and the key name varies by tool, so scan text values rather than naming keys.
        for key, value in img.info.items():
            if key in BORING_INFO_KEYS or not isinstance(value, str):
                continue
            blob = f"{key}: {value}".lower()
            if any(m in blob for m in GENERATOR_MARKERS):
                return _marked(f"{key}: {value}")

        # 4. Raw byte scan, last resort. A substring match against compressed data with no structure parsing - weak, so it only speaks when nothing above did.
        data = path.read_bytes()
        for marker in C2PA_MARKERS:
            if marker in data:
                return _marked(f"{marker.decode()} box marker present in file bytes")
    
    return {
        "status": "no_marking_found",
        "evidence": None
    }
