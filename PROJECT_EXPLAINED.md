# synthetic-image-triage — Project Explainer

**دليل شرح المشروع — نسخة ثنائية اللغة**

A non-technical walkthrough of what this project is, how it was built, what it proves, and what it does not.

هذا المستند مكتوب بالإنجليزية أولًا ثم بالعربية كاملة. اقرأ أي نسخة من البداية إلى النهاية دون الحاجة للتنقل.

- [English version](#english-version)
- [النسخة العربية](#النسخة-العربية)

---
---

# English version

## Table of contents

1. [The problem](#1-the-problem)
2. [Idea 1 — Look for the official mark first](#2-idea-1--look-for-the-official-mark-first)
3. [What metadata actually is](#3-what-metadata-actually-is)
4. [EXIF, XMP and C2PA](#4-exif-xmp-and-c2pa)
5. [Why changing the file format destroys the mark](#5-why-changing-the-file-format-destroys-the-mark)
6. [Idea 2 — Analyse the pixels themselves](#6-idea-2--analyse-the-pixels-themselves)
7. [Low and high frequency in an image](#7-low-and-high-frequency-in-an-image)
8. [The pattern real photographs follow](#8-the-pattern-real-photographs-follow)
9. [The three numbers, and how to read them](#9-the-three-numbers-and-how-to-read-them)
10. [Idea 3 — Testing the tool against itself](#10-idea-3--testing-the-tool-against-itself)
11. [Bugs found and fixed](#11-bugs-found-and-fixed)
12. [What is proven and what is not](#12-what-is-proven-and-what-is-not)
13. [The next step](#13-the-next-step)
14. [Reference: every measured number](#14-reference-every-measured-number)

---

## 1. The problem

Article 50 of the EU AI Act applies from **2 August 2026**. It requires companies producing AI-generated images to attach a **machine-readable mark** to every output saying: this image was generated. Systems already on the market before that date have until **2 December 2026** to comply.

Two practical problems follow.

**First:** during this transition window, a large volume of generated content is circulating **legally and with no mark at all**.

**Second, and more serious:** the mark is fragile. If someone screenshots the image, uploads it to a platform that recompresses it, or converts the file format, **the mark is erased**. The image is still generated; the evidence is gone.

Picture an insurance clerk receiving a damage photo as part of a claim. Or a journalist receiving an image from an event. The image carries no mark. **What do they do now?** They have no signal to work from.

This tool gives them a fallback signal.

---

## 2. Idea 1 — Look for the official mark first

The tool inspects the file for any provenance marking buried inside it. Four methods, ordered from strongest to weakest: EXIF data, then XMP, then embedded text chunks in PNG files, and finally a raw byte scan for the C2PA standard.

**Why check this first?** Because the law treats the mark as the primary evidence. It would be methodologically backwards to jump to statistical analysis while the file contains an explicit declaration that it was generated.

**Evidence this works:** we built 8 test fixtures covering all four paths, plus three negative cases (clean images that must *not* be flagged). All pass. More importantly, the tool caught a **real generated image from ChatGPT** that was not one of our synthetic fixtures — it caught it through the actual C2PA standard.

**What does not work, stated plainly:** the fourth method (byte scanning) is technically weak. It is a substring search inside a compressed file with no structural parsing. It could produce a false positive in theory. That is why it is placed **last**, and why its weakness is documented explicitly in the technical README rather than hidden.

---

## 3. What metadata actually is

This is the point that unlocks everything else.

When you open an image file, you see the **pixels** — the arranged colours that form the scene. But an image file on disk actually contains **two completely separate things**:

```
┌─────────────────────────────────┐
│   One image file (.jpg / .png)  │
├─────────────────────────────────┤
│  1. The pixels — what you see   │
│     (millions of colour numbers)│
├─────────────────────────────────┤
│  2. Metadata                    │
│     Plain text, never displayed │
│     on screen                   │
└─────────────────────────────────┘
```

The second part — metadata — is **ordinary text written inside the file**, but it is never drawn on screen. An image viewer reads the first part and ignores the second.

**A "provenance mark" is information written into that second part** saying: this image was produced by an AI system.

### What you can know about an image without looking at it

A normal photo from your phone typically carries:

| Information | Example |
|---|---|
| Device model | iPhone 15 Pro |
| Date and time taken | 2026-03-14, 18:42:07 |
| **GPS coordinates** | 52.3676° N, 4.9041° E |
| Camera settings | shutter speed, aperture, ISO |
| Editing software | Adobe Photoshop 25.1 |
| Owner or copyright | if configured on the device |

**Note the third row.** This is why privacy experts warn against uploading photos directly — they can reveal your home address without your knowledge. It makes the concept concrete: **the information is in the file, but invisible.**

In this project we use the same mechanism for a different purpose. Instead of looking for a camera model, we look for a **generator name**. When Stable Diffusion produces an image, it writes the prompt, the model name, and the generation settings inside the file.

This is exactly what our tool captured in testing:

```
parameters: a photo of a cat, Steps: 30, Sampler: DPM++ 2M,
CFG scale: 7, Model: sd_xl_base_1.0
```

The image itself shows nothing. But the file contained a full written confession.

---

## 4. EXIF, XMP and C2PA

The confusing part: there is no **single agreed place** to write this information. Three standards emerged in different eras for different purposes, and all three exist simultaneously today.

### EXIF — the camera standard

**Born in the 1990s** for digital cameras.

It is simply a **fixed table of numbered slots**. Each slot has a specific number and a fixed meaning:

| Number | Meaning |
|---|---|
| 271 | Camera manufacturer |
| 272 | Camera model |
| **305** | **Software** |
| **270** | **ImageDescription** |

**Strength:** very simple, supported almost everywhere.

**Weakness:** rigid. You cannot add a new slot. If a generator wants to write information that has no slot, there is nowhere to put it.

During development we collided with slot **305** concretely — it caused a crash in our fixture generator because we tried to delete it from an image that did not have it.

### XMP — Adobe's flexible answer

**Born around 2001** because EXIF was too narrow.

Instead of numbered slots, it is a **flexible text document** in XML format where you can write anything. You can see it in our project's output:

```
XMP: <?xpacket begin=""?><x:xmpmeta xmlns:x="adobe:ns:meta/">...
```

**Strength:** completely flexible, holds any information.

**Weakness:** that same flexibility. There is no single rule forcing everyone to write "AI-generated" the same way. Each company writes it differently.

### C2PA — the modern standard, and the one that matters for this law

**Born around 2021**, with Adobe, Microsoft, Intel and media organisations involved.

It differs fundamentally from the other two for one reason:

> **EXIF and XMP are just text that anyone can write or edit. C2PA is cryptographically signed.**

The difference is like a handwritten note versus a document with an official seal. C2PA uses cryptographic signing, so you can verify:
- **who** actually produced the image
- and that **nobody has tampered with** the record since

**This is precisely why the EU AI Act points to it** when it talks about a machine-readable mark.

**And this is the standard that caught the ChatGPT image in our test.**

### An honest note about our tool

I should be clear about one thing: **our tool does not verify the C2PA signature.**

It only **detects the presence** of the mark inside the file's bytes. It says "there is a C2PA record here", not "this record is valid and cryptographically authenticated".

Full cryptographic verification is a much larger job. That is why we placed this method **last** among the four rules, and documented its weakness explicitly rather than hiding it.

---

## 5. Why changing the file format destroys the mark

This is the heart of the whole project.

### The cause: metadata is not part of the image

Return to the first diagram. Pixels and metadata are **separate**. When you convert a format, this happens:

```
Original PNG file
├── Pixels ──────────────► read ✓
└── C2PA record ─────────► ignored ✗
                              │
                    Program decodes the pixels
                              │
                              ▼
                    Writes a new JPEG file
                              │
                              ▼
                    ┌──────────────────┐
                    │  New JPEG file   │
                    ├──────────────────┤
                    │  Pixels ✓        │
                    │  (nothing else)  │
                    └──────────────────┘
```

**The program did not "delete" the mark. It simply did not copy it.**

This is not a bug — it is the default behaviour of most software. The converter cares about pixels; metadata is not its concern.

### The worst case: screenshots

When you screenshot an image, you are **not copying the file at all**. You are photographing the light displayed on screen and creating a **completely new file** from scratch.

The original file, with all its metadata, **was never touched and never shared**. The new file was born empty.

**Result:** a screenshot of an AI-generated image is an AI-generated image **with no legal trace**. Doing this takes two seconds and requires no technical knowledge.

### And social platforms do it automatically

Most platforms recompress every uploaded image to save storage and bandwidth. Recompression produces a new file. Same result.

**Nobody may have intended to hide anything.** A user uploaded an image, the platform compressed it as it compresses everything, and the mark vanished in transit.

### Which is exactly why this project exists

**The law says:** mark generated images.

**Reality says:** the mark lives in a layer separate from the image, and that layer is erased by a screenshot, a format conversion, or simply uploading to a social platform.

**Result:** a reviewer receiving an unmarked image cannot tell whether it is real, or generated and stripped along the way.

**Our tool's role:** when the legal layer fails, fall back to the pixels themselves — because the pixels are the only thing that **cannot be separated from the image**. However you copy, compress or screenshot it, the pixels remain.

---

## 6. Idea 2 — Analyse the pixels themselves

First, a clarification. The word "fingerprint" can mislead. I do not mean a number that identifies one image versus another like a human fingerprint. I mean a **statistical description of the image's nature** — closer to a "character" than an "identity".

### In audio

When you hear a song, your ear hears everything mixed together. But the song is really the **sum** of separate things:

| Type | Source |
|---|---|
| Low frequencies | Drums, bass — deep, slow sounds |
| Mid frequencies | Human voice, guitar |
| High frequencies | Cymbals, hiss — sharp, fast sounds |

The **equaliser** in a music player shows you exactly this: how much energy exists in each frequency band.

### In images — the direct translation

In audio, frequency means **how fast the sound changes over time**.

In images, frequency means **how fast the colour changes over distance**.

---

## 7. Low and high frequency in an image

| | Low frequency | High frequency |
|---|---|---|
| **In audio** | Sound changing slowly over time (drum) | Sound changing fast (cymbal) |
| **In an image** | Colour changing slowly over distance | Colour changing fast over distance |
| **Visual example** | Sky gradient from light to dark blue | Gravel texture, hair, fabric weave |

### A concrete example from our project

Take the stone wall image we worked with (kodim01):

**Low frequencies** = the large shapes. The wall is a light mass, the door a dark mass. You can walk dozens of pixels without much colour change. **Slow change over distance.**

**High frequencies** = the fine detail. The roughness of the stone surface, the thin lines between blocks, the grain. Here the colour changes **from one pixel to its immediate neighbour**. Very fast change.

### A thought experiment that fixes the idea

Imagine two images:

1. **A clear blue sky** — you walk 500 pixels and the colour barely changes. Almost purely low frequency.
2. **A close-up of coarse fabric** — every pixel differs from its neighbour. Dense high frequency.

These two images have completely different "frequency character", even if their average brightness is identical.

**The tool computes this mathematically** using the Fourier transform — which does exactly what an audio equaliser does: separates the image into bands and measures the energy in each.

---

## 8. The pattern real photographs follow

### The natural rule

Real photographs — of landscapes, faces, buildings, anything — follow a **shared mathematical law**:

> As frequency rises, energy falls — **at a regular, predictable rate.**

Put simply: in any natural image, large shapes carry far more energy than fine details, and the decline between them is **smooth and steady**.

In practice: if you plot energy against frequency on a logarithmic scale, you get a **straight descending line**.

This is not a guess — it is one of the most established results in natural image statistics. The reason is that the world itself is built this way: few large objects, many small details, at a roughly constant ratio.

**And this is what we actually observed.** The third plot in every panel we generated was a nearly straight descending line. The measured numbers:

| Image | Slope |
|---|---|
| kodim01 (stone wall) | −1.76 |
| kodim05 (motorcycles) | −2.31 |

Both in the expected natural range.

### How generated images differ

Image generators do not paint the picture in one go. They start with a very small image (say 8×8 pixels) and **enlarge it in stages**: 8 → 16 → 32 → 64... up to the final size.

Each enlargement invents new pixels that did not exist. By its mathematical nature, this process tends to leave a **regular periodic pattern** in the image.

The theoretically expected result: instead of a smooth descending line, **bumps or deviations** appear at specific frequencies corresponding to the enlargement steps.

**Now the honest part:** this is what the research and theory say. But in our project, **we did not prove it.** The next section explains why.

---

## 9. The three numbers, and how to read them

### The three numbers

**Number 1 — the slope**
Measures: **how steep the descending line is.** That is, how quickly fine detail fades relative to large shapes.

**Number 2 — high-frequency residual (`hf_residual`)**
Measures: **is there more or less fine detail than the straight line predicts?** That is, how far the image deviates from its own natural pattern in the high band.

**Number 3 — half-Nyquist peak (`nyquist_peak`)**
Measures: **is there a sudden bump at a specific location?** This is the number designed specifically to catch the enlargement signature.

### Now — how does a user read them?

**Here I have to give you the honest answer, and it is not the one you want.**

> **They cannot. And neither can we.**

This is not modesty. It is a result **we measured ourselves**, and it is written explicitly in the project's technical README.

### Why? Here is what we found

We took a single real image and applied entirely ordinary processing to it — nothing generated whatsoever:

| Version | Slope | `hf_residual` |
|---|---|---|
| Original | −1.76 | −0.56 |
| JPEG quality 95 | −1.78 | −0.53 |
| JPEG quality 40 | −1.83 | −0.77 |
| **Bilinear down/upsample** | **−3.98** | **−1.98** |

Look at the last row. **Simply shrinking the image and enlarging it again** moved the slope from −1.76 to −3.98.

Now compare with the actually-generated ChatGPT image: its slope was **−3.29**.

**The problem is clear:** a real image that went through a resize gave −3.98. A generated image gave −3.29. **The two numbers are in the same region.** They cannot be separated.

And any generated image that reaches you over the internet **has certainly been resized somewhere**. So the number we see could be the generation signature, or the resize signature, and with one sample there is no way to tell.

### What about the third number?

The ChatGPT image gave **0.895**, while the seven non-generated images ranged from **0.377 to 0.491** — roughly double.

Very tempting. But:
- **One sample** is not a result
- and that same image carries resize indicators, and resizing moves the numbers strongly as you just saw

So we cannot know: is 0.895 a generation signature, or a resize signature?

---

## 10. Idea 3 — Testing the tool against itself

**This is the most important idea in the whole project.**

It is easy to build a tool that outputs convincing-looking numbers that mean nothing. So we ran two tests **against the tool itself**, not against the images.

### Test 1: does the number measure the image, or luck?

We took **the same image** and cropped five sections from slightly different positions. Logically the five should give nearly identical results — it is the same image.

The result was startling:

| Feature | Variation between crops |
|---|---|
| Slope | **0.7%** — excellent |
| Second feature (first version) | **80%** — catastrophic |

The second feature moved 80% merely because we shifted the crop. **That means it was measuring where we cropped, not the image.** We deleted it and redesigned it. The new version is about **17× more stable**.

**Why this matters:** this test revealed that one of the "findings" we thought we had was **pure noise**. We were seeing a 4% difference and believing it was signal, while the natural noise was 80%. **We removed that claim from the final report** rather than publishing it.

### Test 2: what fools the tool?

We took one image and created six versions using entirely ordinary processing (JPEG compression at different qualities, shrink-and-enlarge by two methods). All were **real** images — nothing generated.

The result: one simple resize changed the tool's reading **more than anything else we tested**.

**This is the trap that published research papers have fallen into:** if you compare real PNG images against generated JPEG images, you get 99% accuracy — but you are actually detecting **the file format**, not the fake. The tool would look brilliant while being completely worthless.

We measured this, documented it with numbers and plots, and built the design rules around it.

---

## 11. Bugs found and fixed

During final review we found **six real bugs**. Two are worth describing because they show the nature of the work.

### Bug A (serious): authentic photos flagged as AI-marked

The tool was classifying **genuine 1990s photographs** as "carrying an AI mark". The cause: the image contained the name of the scanner that digitised it, and the tool treated any buried text as evidence.

**This is the worst possible error direction** — telling a reviewer that a real photo is labelled as AI. Fixed; both images now classify correctly.

### Bug B (the most serious methodologically): a test that lied

We had an automated test printing "**8/8 passing**" — while checking **only one file** out of eight. A green test that tested nothing.

**This is the direct reason bug A stayed hidden.** We had a fixture designed specifically to catch it, but it was never running. Fixed; the test now fails loudly if any fixture is missing.

---

## 12. What is proven and what is not

### Proven

- The official-mark path works: 8/8 fixtures pass, **plus a real ChatGPT image caught**
- Two stable, measured features (0.7% and 0.009 variation across crops)
- Confounds measured and documented with numbers, not assumed
- The tool does not crash on unusual inputs (corrupt files, odd colour modes, varying sizes) — tested
- Results are reproducible: two consecutive runs produce an identical file

### Not proven — and this is written in the README itself

The tool is **not a classifier**, and there is **no accuracy claim anywhere** in the project. The reason is simple: we did not run a controlled experiment on a validated dataset.

We have one intriguing preliminary observation — the ChatGPT image gave roughly **double** the reading of the seven non-generated images. But it is a single sample, and that image also shows resize indicators, and we proved ourselves that resizing moves the numbers strongly.

We wrote this explicitly in the README rather than turning it into a claim that sells.

### Why this counts as success

The easier project would have said: "AI image detector, 98% accuracy". You would have believed it, and it would have collapsed at the first real test.

What we built instead is a tool that **knows and measures its own limits**:
- we deleted a feature because it failed a test we set for ourselves
- we deleted a "finding" because we measured the noise and found it larger than the signal
- we fixed a test that was lying to us about passing
- and we refused the one tempting claim we could have made

In anything touching legal compliance, **a tool that clearly says "I don't know" is more valuable than one that guesses confidently** — because the second one pushes people into wrong decisions while feeling reassured.

---

## 13. The next step

To turn the preliminary observation (n=1) into a real result, we need a **controlled pair**: hundreds of real images and hundreds of generated images, at **the same format, the same resolution, and the same processing path**.

Only then are all confounds matched between the two groups, and the only remaining difference is: generated or not. Only then does the third number become meaningful.

This is written in the README as a declared next step, not a hidden gap.

---

## 14. Reference: every measured number

| Measurement | Value | What it means |
|---|---|---|
| Slope, kodim01 (real) | −1.76 | Natural range |
| Slope, kodim05 (real) | −2.31 | Natural range |
| Slope, bilinear resize (real) | −3.98 | Confound, largest effect measured |
| Slope, ChatGPT image (generated) | −3.29 | Inside the confound region — inconclusive |
| `hf_residual`, kodim01 | −0.56 | Baseline |
| `hf_residual`, bilinear | −1.98 | Confound |
| `nyquist_peak`, 7 non-generated | 0.377 – 0.491 | Baseline range |
| `nyquist_peak`, ChatGPT image | 0.895 | ~2× — n=1, uncontrolled |
| Slope stability across crops | 0.7% | Usable |
| `hf_ratio` stability (deleted) | 80% | Unusable — feature removed |
| `hf_residual` stability | 0.009 log-units | Usable, ~17× better |
| Cross contrast, no window | ~2.3 log-units | Boundary artifact present |
| Cross contrast, with Hann window | ~0.05 log-units | Artifact removed, ~50× |
| Provenance fixtures | 8/8 | All four rules plus three negatives |

---
---

# النسخة العربية

## المحتويات

1. [المشكلة](#١-المشكلة)
2. [الفكرة الأولى — ابحث عن العلامة الرسمية أولًا](#٢-الفكرة-الأولى--ابحث-عن-العلامة-الرسمية-أولًا)
3. [ما هي البيانات الوصفية فعلًا](#٣-ما-هي-البيانات-الوصفية-فعلًا)
4. [EXIF و XMP و C2PA](#٤-exif-و-xmp-و-c2pa)
5. [لماذا يمحو تغيير الصيغة العلامة](#٥-لماذا-يمحو-تغيير-الصيغة-العلامة)
6. [الفكرة الثانية — حلّل البكسلات نفسها](#٦-الفكرة-الثانية--حلّل-البكسلات-نفسها)
7. [الترددات المنخفضة والعالية في الصورة](#٧-الترددات-المنخفضة-والعالية-في-الصورة)
8. [النمط الذي تتبعه الصور الحقيقية](#٨-النمط-الذي-تتبعه-الصور-الحقيقية)
9. [الأرقام الثلاثة وكيف تُقرأ](#٩-الأرقام-الثلاثة-وكيف-تُقرأ)
10. [الفكرة الثالثة — اختبار الأداة ضد نفسها](#١٠-الفكرة-الثالثة--اختبار-الأداة-ضد-نفسها)
11. [الأخطاء التي وُجدت وأُصلحت](#١١-الأخطاء-التي-وُجدت-وأُصلحت)
12. [ما هو مُثبت وما هو غير مُثبت](#١٢-ما-هو-مُثبت-وما-هو-غير-مُثبت)
13. [الخطوة التالية](#١٣-الخطوة-التالية)
14. [مرجع: كل رقم مقيس](#١٤-مرجع-كل-رقم-مقيس)

---

## ١. المشكلة

اعتبارًا من **2 أغسطس 2026**، صار قانون الذكاء الاصطناعي الأوروبي (المادة 50) يُلزم الشركات التي تنتج صورًا بالذكاء الاصطناعي بأن تضع على كل صورة **علامة قابلة للقراءة آليًا** تقول: هذه الصورة مولّدة. والشركات التي كانت أنظمتها في السوق قبل ذلك التاريخ لديها مهلة حتى **2 ديسمبر 2026**.

هنا تنشأ مشكلتان عمليتان.

**المشكلة الأولى:** في هذه الأشهر الانتقالية، هناك كمّ هائل من الصور المولّدة تتداول **قانونيًا وبدون أي علامة**.

**المشكلة الثانية، وهي الأهم:** العلامة نفسها هشّة. إذا أخذ أحدهم لقطة شاشة للصورة، أو رفعها على منصة تعيد ضغطها، أو حوّل صيغتها — **تُمحى العلامة تمامًا**. الصورة تبقى مولّدة، لكن الدليل يختفي.

تخيّل موظفًا في شركة تأمين تصله صورة ضرر في سيارة كجزء من مطالبة. أو صحفيًا تصله صورة من حدث. الصورة لا تحمل أي علامة. **ما الذي يفعله الآن؟** لا يملك أي إشارة يبني عليها.

هذه الأداة تعطيه إشارة احتياطية.

---

## ٢. الفكرة الأولى — ابحث عن العلامة الرسمية أولًا

الأداة تفحص الصورة بحثًا عن أي علامة مصدر مدفونة داخل الملف. أربع طرق مرتبة من الأقوى إلى الأضعف: بيانات EXIF، ثم XMP، ثم النصوص المدمجة في ملفات PNG، وأخيرًا مسح خام لبايتات الملف بحثًا عن معيار C2PA.

**لماذا هذا أولًا؟** لأن القانون يعتبر العلامة هي الدليل الأساسي. من الخطأ منهجيًا أن نقفز إلى التحليل الإحصائي بينما الملف يحمل إقرارًا صريحًا بأنه مولّد.

**الدليل أن هذا يعمل:** بنينا 8 حالات اختبار تغطي المسارات الأربعة، بالإضافة إلى ثلاث حالات سلبية (صور نظيفة يجب ألّا تُصنّف كمولّدة). كلها تنجح. والأهم: **الأداة التقطت صورة حقيقية مولّدة من ChatGPT** لم تكن ضمن حالات الاختبار المصطنعة — التقطتها عبر معيار C2PA الفعلي.

**وما لا يعمل، بصراحة:** الطريقة الرابعة (مسح البايتات) ضعيفة تقنيًا. هي بحث عن نص داخل ملف مضغوط دون فهم بنيته. قد تُخطئ نظريًا. لهذا وضعناها **أخيرًا** ووثّقنا ضعفها صراحة في المستند التقني بدل إخفائه.

---

## ٣. ما هي البيانات الوصفية فعلًا

هذه هي النقطة التي تفتح كل شيء.

عندما تفتح ملف صورة، أنت ترى **البكسلات** — الألوان المرتبة التي تشكّل المنظر. لكن ملف الصورة على القرص يحتوي في الواقع على **شيئين منفصلين تمامًا**:

```
┌─────────────────────────────────┐
│  ملف صورة واحد (.jpg / .png)   │
├─────────────────────────────────┤
│  1. البكسلات — ما تراه عينك    │
│     (ملايين الأرقام للألوان)    │
├─────────────────────────────────┤
│  2. البيانات الوصفية (Metadata) │
│     نصّ مكتوب، لا يظهر أبدًا     │
│     على الشاشة                  │
└─────────────────────────────────┘
```

الجزء الثاني — البيانات الوصفية — هو **نصّ عادي مكتوب داخل الملف**، لكنه لا يُرسم على الشاشة أبدًا. برنامج عرض الصور يقرأ الجزء الأول ويتجاهل الثاني.

**"علامة المصدر" هي معلومة مكتوبة في هذا الجزء الثاني** تقول: هذه الصورة أنتجها نظام ذكاء اصطناعي.

### ما الذي يمكن معرفته من الصورة دون النظر إليها؟

صورة عادية من هاتفك تحمل عادةً:

| المعلومة | مثال |
|---|---|
| نوع الجهاز | iPhone 15 Pro |
| تاريخ ووقت الالتقاط | 2026-03-14, 18:42:07 |
| **الإحداثيات الجغرافية** | 52.3676° N, 4.9041° E |
| إعدادات التصوير | سرعة الغالق، فتحة العدسة، ISO |
| البرنامج الذي عدّلها | Adobe Photoshop 25.1 |
| اسم المالك أو حقوق النشر | إن كان مضبوطًا في الجهاز |

**لاحظ السطر الثالث.** هذا سبب تحذير خبراء الخصوصية من رفع الصور مباشرة: قد تكشف عنوان منزلك دون أن تدري. وهذا يوضح الفكرة بشكل ملموس — **المعلومة موجودة في الملف، لكنها غير مرئية**.

في مشروعنا نستفيد من الآلية نفسها لغرض مختلف: بدل البحث عن موديل الكاميرا، نبحث عن **اسم مولّد الصور**. عندما ينتج Stable Diffusion صورة، يكتب داخلها النص الذي طُلب منه، واسم النموذج، وإعدادات التوليد.

وهذا بالضبط ما التقطته أداتنا في اختبارها:

```
parameters: a photo of a cat, Steps: 30, Sampler: DPM++ 2M,
CFG scale: 7, Model: sd_xl_base_1.0
```

الصورة نفسها لا تُظهر شيئًا. لكن الملف كان يحمل اعترافًا كاملًا مكتوبًا بالنص.

---

## ٤. EXIF و XMP و C2PA

الأمر الذي يربك الناس: لا يوجد **مكان واحد** متفق عليه لكتابة هذه المعلومة. ثلاثة معايير نشأت في عصور مختلفة ولأغراض مختلفة، والثلاثة موجودة اليوم في وقت واحد.

### EXIF — معيار الكاميرات

**نشأ في التسعينيات** للكاميرات الرقمية.

هو ببساطة **جدول ثابت من الخانات المرقّمة**. كل خانة لها رقم محدد ومعنى محدد لا يتغير:

| الرقم | المعنى |
|---|---|
| 271 | صانع الكاميرا |
| 272 | موديل الكاميرا |
| **305** | **البرنامج (Software)** |
| **270** | **الوصف (ImageDescription)** |

**نقطة قوته:** بسيط جدًا، ومدعوم في كل مكان تقريبًا.

**نقطة ضعفه:** جامد. لا يمكنك إضافة خانة جديدة. إذا أراد مولّد صور أن يكتب معلومة لا توجد لها خانة، فلا مكان له.

أثناء عملنا اصطدمنا بهذا الرقم **305** بشكل ملموس — كان يسبب خطأً برمجيًا في مولّد حالات الاختبار لأننا حاولنا حذفه من صورة لا تحتوي عليه أصلًا.

### XMP — الحل المرن من Adobe

**نشأ في 2001** لأن EXIF كان ضيقًا.

بدل الخانات المرقّمة، هو **مستند نصّي مرن** بصيغة XML يمكنك كتابة ما تشاء فيه. تراه في نتائج مشروعنا:

```
XMP: <?xpacket begin=""?><x:xmpmeta xmlns:x="adobe:ns:meta/">...
```

**نقطة قوته:** مرن تمامًا، يستوعب أي معلومة.

**نقطة ضعفه:** المرونة نفسها. لا توجد قاعدة موحّدة تفرض على الجميع كتابة "مولّد بالذكاء الاصطناعي" بالصيغة ذاتها. كل شركة تكتبها بطريقتها.

### C2PA — المعيار الحديث، وهو الأهم لقانوننا

**نشأ حوالي 2021**، بمشاركة Adobe و Microsoft و Intel وشركات إعلامية.

وهو مختلف جوهريًا عن الاثنين السابقين، لسبب واحد:

> **EXIF و XMP مجرد نصّ يستطيع أي شخص كتابته أو تعديله. أما C2PA فهو موقّع رقميًا.**

الفرق كالفرق بين ورقة مكتوبة بخط اليد ووثيقة مختومة من جهة رسمية. C2PA يستخدم التوقيع التشفيري، فيمكن التحقق من:
- **من** أنتج الصورة فعلًا
- وأن أحدًا **لم يعبث** بالسجل بعد ذلك

**ولهذا السبب تحديدًا هو المعيار الذي يشير إليه قانون الذكاء الاصطناعي الأوروبي** عندما يتحدث عن علامة قابلة للقراءة آليًا.

**وهذا هو المعيار الذي التقط صورة ChatGPT في اختبارنا.**

### نقطة صدق مهمة عن أداتنا

يجب أن أوضح شيئًا: **أداتنا لا تتحقق من توقيع C2PA**.

هي فقط **تبحث عن وجود العلامة** داخل بايتات الملف. أي أنها تقول "يوجد سجل C2PA هنا"، لا "هذا السجل صحيح وموثّق تشفيريًا".

التحقق التشفيري الكامل عمل أكبر بكثير. لهذا وضعنا هذه الطريقة **أخيرًا** في ترتيب القواعد الأربع، ووثّقنا ضعفها صراحة.

---

## ٥. لماذا يمحو تغيير الصيغة العلامة

هذا جوهر المشروع كله.

### السبب: البيانات الوصفية ليست جزءًا من الصورة

عد إلى الرسم الأول. البكسلات والبيانات الوصفية **منفصلان**. عند تحويل الصيغة، يحدث التالي:

```
ملف PNG أصلي
├── البكسلات ────────────► تُقرأ ✓
└── سجل C2PA ────────────► يُتجاهل ✗
                              │
                    البرنامج يفك ترميز البكسلات
                              │
                              ▼
                    يكتب ملف JPEG جديد
                              │
                              ▼
                    ┌──────────────────┐
                    │ ملف JPEG جديد    │
                    ├──────────────────┤
                    │ البكسلات ✓       │
                    │ (لا شيء آخر)     │
                    └──────────────────┘
```

**البرنامج لم "يحذف" العلامة. هو ببساطة لم ينسخها.**

هذه ليست خطأً برمجيًا، بل السلوك الافتراضي لمعظم البرامج. برنامج التحويل يهتم بالبكسلات؛ البيانات الوصفية ليست شغله.

### والأخطر: لقطة الشاشة

عندما تأخذ لقطة شاشة لصورة، أنت **لا تنسخ الملف إطلاقًا**. أنت تصوّر الضوء المعروض على الشاشة وتنشئ **ملفًا جديدًا تمامًا** من الصفر.

الملف الأصلي بكل بياناته الوصفية **لم يُلمس ولم يُشارك**. الملف الجديد وُلد فارغًا.

**النتيجة:** لقطة شاشة لصورة مولّدة بالذكاء الاصطناعي = صورة مولّدة **بدون أي أثر قانوني**. والقيام بذلك يستغرق ثانيتين ولا يتطلب أي معرفة تقنية.

### وأيضًا: منصات التواصل تفعلها تلقائيًا

معظم المنصات تعيد ضغط كل صورة تُرفع إليها لتوفير المساحة وسرعة التحميل. إعادة الضغط تنتج ملفًا جديدًا. النتيجة نفسها.

**قد لا ينوي أحد إخفاء شيء على الإطلاق.** المستخدم رفع صورة، والمنصة ضغطتها كما تفعل مع كل صورة، والعلامة اختفت في الطريق.

### ولهذا بالضبط بُني هذا المشروع

**القانون يقول:** ضعوا علامة على الصور المولّدة.

**الواقع يقول:** العلامة موجودة في طبقة منفصلة عن الصورة، وهذه الطبقة تُمحى بلقطة شاشة، أو تحويل صيغة، أو مجرد الرفع على منصة تواصل.

**النتيجة:** المراجع الذي تصله صورة بلا علامة لا يعرف: هل هي حقيقية؟ أم مولّدة وفقدت علامتها في الطريق؟

**دور أداتنا:** عندما تفشل الطبقة القانونية، ننتقل إلى البكسلات نفسها — لأن البكسلات هي الشيء الوحيد الذي **لا يمكن فصله عن الصورة**. مهما نسختها أو ضغطتها أو صوّرت شاشتك، تبقى البكسلات هناك.

---

## ٦. الفكرة الثانية — حلّل البكسلات نفسها

أولًا توضيح: كلمة "بصمة" قد تكون مضلّلة. لا أقصد رقمًا يميّز صورة عن أخرى كبصمة الإصبع. أقصد **وصفًا إحصائيًا لطبيعة الصورة** — أقرب إلى "طابع" منه إلى "هوية".

### في الصوت

عندما تسمع أغنية، أذنك تسمع كل الأصوات مختلطة. لكن الأغنية في الحقيقة **مجموع** أشياء منفصلة:

| النوع | المصدر |
|---|---|
| ترددات منخفضة | الطبل، الباص — أصوات عميقة بطيئة |
| ترددات متوسطة | الصوت البشري، الجيتار |
| ترددات عالية | الصنج، الصفير — أصوات حادة سريعة |

**المُعادِل الصوتي (Equalizer)** في مشغّل الموسيقى يعرض لك بالضبط هذا: كم من الطاقة موجودة في كل نطاق تردد.

### في الصورة — الترجمة المباشرة

في الصوت، التردد يعني **سرعة تغيّر الصوت عبر الزمن**.

في الصورة، التردد يعني **سرعة تغيّر اللون عبر المسافة**.

---

## ٧. الترددات المنخفضة والعالية في الصورة

| | الترددات المنخفضة | الترددات العالية |
|---|---|---|
| **في الصوت** | صوت يتغيّر ببطء عبر الزمن (طبل) | صوت يتغيّر بسرعة (صنج) |
| **في الصورة** | لون يتغيّر ببطء عبر المسافة | لون يتغيّر بسرعة عبر المسافة |
| **مثال بصري** | تدرّج السماء من الأزرق الفاتح إلى الغامق | ملمس الحصى، شعر، نسيج قماش |

### مثال ملموس من مشروعنا

خذ صورة الجدار الحجري (kodim01):

**الترددات المنخفضة** = الأشكال الكبيرة. الجدار كتلة فاتحة، الباب كتلة داكنة. تمشي عشرات البكسلات دون أن يتغيّر اللون كثيرًا. **تغيّر بطيء عبر المسافة**.

**الترددات العالية** = التفاصيل الدقيقة. خشونة سطح الحجر، الخطوط الرفيعة بين الأحجار، الحبيبات. هنا يتغيّر اللون **من بكسل إلى البكسل المجاور مباشرة**. تغيّر سريع جدًا.

### اختبار ذهني يثبّت الفكرة

تخيّل صورتين:

1. **سماء زرقاء صافية** — تمشي 500 بكسل واللون يكاد لا يتغيّر. ترددات منخفضة تقريبًا فقط.
2. **صورة مقرّبة لقماش خشن** — كل بكسل يختلف عن جاره. ترددات عالية بكثافة.

هاتان الصورتان لهما "طابع ترددي" مختلف تمامًا، حتى لو كان متوسط سطوعهما متطابقًا.

**والأداة تحسب هذا رياضيًا** عبر تحويل فورييه — الذي يقوم بالضبط بما يفعله المُعادِل الصوتي: يفصل الصورة إلى نطاقات ويقيس الطاقة في كل نطاق.

---

## ٨. النمط الذي تتبعه الصور الحقيقية

### القاعدة الطبيعية

الصور الفوتوغرافية الحقيقية — للمناظر، الوجوه، المباني، أي شيء — تتبع **قانونًا رياضيًا مشتركًا**:

> كلما زاد التردد، قلّت الطاقة — **بمعدل منتظم وقابل للتنبؤ**.

بعبارة أبسط: في أي صورة طبيعية، الأشكال الكبيرة تحمل طاقة أكبر بكثير من التفاصيل الدقيقة، والانخفاض بينهما **سلس ومطّرد**.

عمليًا: إذا رسمت الطاقة مقابل التردد على مقياس لوغاريتمي، تحصل على **خط مستقيم نازل**.

هذا ليس تخمينًا — إنه من أرسخ النتائج في مجال إحصاء الصور الطبيعية. سببه أن العالم نفسه مبني هكذا: أشياء كبيرة قليلة، وتفاصيل صغيرة كثيرة، بنسبة ثابتة تقريبًا.

**وهذا ما رأيناه فعلًا.** الرسم البياني الثالث في كل لوحة أنتجناها كان خطًا نازلًا شبه مستقيم. الأرقام المقاسة:

| الصورة | الميل |
|---|---|
| kodim01 (الجدار الحجري) | −1.76 |
| kodim05 (الدراجات) | −2.31 |

كلاهما في النطاق الطبيعي المتوقع.

### كيف تختلف الصور المولّدة؟

مولّدات الصور لا ترسم الصورة دفعة واحدة. تبدأ بصورة صغيرة جدًا (مثلًا 8×8 بكسل) ثم **تكبّرها على مراحل**: 8 ← 16 ← 32 ← 64... حتى الحجم النهائي.

كل عملية تكبير تخترع بكسلات جديدة لم تكن موجودة. وهذه العملية — بحكم طبيعتها الرياضية — تميل إلى ترك **نمط دوري منتظم** في الصورة.

النتيجة المتوقعة نظريًا: بدل الخط النازل السلس، تظهر **نتوءات أو انحرافات** عند ترددات محددة تقابل خطوات التكبير.

**والآن الجزء الصادق:** هذا ما تقوله الأبحاث والنظرية. لكن في مشروعنا، **لم نثبته**. القسم التالي يشرح لماذا.

---

## ٩. الأرقام الثلاثة وكيف تُقرأ

### الأرقام الثلاثة

**الرقم الأول: الميل (slope)**
يقيس: **مدى انحدار الخط النازل**. أي كم بسرعة تتلاشى التفاصيل الدقيقة مقارنة بالأشكال الكبيرة.

**الرقم الثاني: انحراف الترددات العالية (hf_residual)**
يقيس: **هل التفاصيل الدقيقة أكثر أم أقل مما يتوقعه الخط المستقيم؟** أي كم تنحرف الصورة عن نمطها الطبيعي في النطاق العالي.

**الرقم الثالث: قمة نصف نايكويست (nyquist_peak)**
يقيس: **هل هناك نتوء مفاجئ في مكان محدد؟** وهذا هو الرقم المصمَّم خصيصًا لالتقاط بصمة التكبير التدريجي.

### الآن — كيف يقرأها المستخدم؟

**وهنا يجب أن أعطيك الإجابة الصادقة، وهي ليست الإجابة التي تريدها.**

> **لا يستطيع. ولا نحن نستطيع.**

هذا ليس تواضعًا. هذه نتيجة **قِسناها بأنفسنا**، وهي مكتوبة صراحة في المستند التقني للمشروع.

### لماذا؟ إليك ما وجدناه

أخذنا صورة حقيقية واحدة، وطبّقنا عليها معالجات عادية تمامًا — لا شيء مولّد فيها إطلاقًا:

| النسخة | الميل | انحراف الترددات العالية |
|---|---|---|
| الأصل | −1.76 | −0.56 |
| ضغط JPEG جودة 95 | −1.78 | −0.53 |
| ضغط JPEG جودة 40 | −1.83 | −0.77 |
| **تصغير/تكبير bilinear** | **−3.98** | **−1.98** |

انظر إلى السطر الأخير. **مجرد تصغير الصورة ثم تكبيرها** غيّر الميل من −1.76 إلى −3.98.

ثم قارن بصورة ChatGPT المولّدة فعلًا: ميلها كان **−3.29**.

**المشكلة واضحة:** صورة حقيقية مرّت بتصغير/تكبير أعطت −3.98. صورة مولّدة أعطت −3.29. **الرقمان في المنطقة نفسها.** لا يمكن الفصل بينهما.

وأي صورة مولّدة تصلك عبر الإنترنت **مرّت حتمًا بإعادة تحجيم في مكان ما**. فالرقم الذي نراه قد يكون بصمة التوليد، أو بصمة التحجيم، ولا سبيل للتمييز بعيّنة واحدة.

### وماذا عن الرقم الثالث؟

صورة ChatGPT أعطت **0.895** بينما الصور السبع غير المولّدة كانت بين **0.377 و 0.491**. أي ما يقارب الضعف.

مغرٍ جدًا. لكن:
- **عيّنة واحدة** لا تُبنى عليها نتيجة
- وتلك الصورة نفسها تحمل علامات إعادة تحجيم، والتحجيم يحرّك الأرقام بقوة كما رأيت

فلا نستطيع أن نعرف: هل الـ 0.895 بصمة توليد، أم بصمة تحجيم؟

---

## ١٠. الفكرة الثالثة — اختبار الأداة ضد نفسها

**هذه أهم فكرة في المشروع كله.**

من السهل جدًا بناء أداة تُخرج أرقامًا تبدو مقنعة وهي بلا معنى. لذلك أجرينا اختبارين للأداة **ضد نفسها**، وليس للصور.

### الاختبار الأول: هل الرقم يقيس الصورة أم يقيس الحظ؟

أخذنا **الصورة نفسها** واقتصصنا منها خمسة مقاطع من مواضع مختلفة قليلًا. منطقيًا يجب أن تعطي الخمسة النتيجة نفسها تقريبًا — فهي الصورة ذاتها.

النتيجة كانت صادمة:

| الخاصية | التغيّر بين المقاطع |
|---|---|
| الميل (slope) | **0.7%** — ممتازة |
| الخاصية الثانية (النسخة الأولى) | **80%** — كارثية |

الخاصية الثانية كانت تتغيّر 80% لمجرد أننا حرّكنا القص قليلًا. **هذا يعني أنها كانت تقيس مكان القص، لا الصورة.** حذفناها وأعدنا تصميمها. النسخة الجديدة استقرارها أفضل بحوالي **17 ضعفًا**.

**لماذا هذا مهم:** هذا الاختبار كشف أن أحد "الاكتشافات" التي ظننا أننا وجدناها كان **ضجيجًا محضًا**. كنا نرى فرقًا بنسبة 4% ونعتقد أنه إشارة، بينما الضجيج الطبيعي 80%. **حذفنا هذا الادعاء من التقرير النهائي** بدل نشره.

### الاختبار الثاني: ما الذي يخدع الأداة؟

أخذنا صورة واحدة وأنشأنا منها ست نسخ بمعالجات عادية تمامًا (ضغط JPEG بجودات مختلفة، تصغير وتكبير بطريقتين). كلها صور **حقيقية** — لا شيء مولّد فيها.

النتيجة: عملية تصغير/تكبير واحدة بسيطة غيّرت قراءة الأداة **أكثر مما يغيّرها أي شيء آخر اختبرناه**.

**وهذا هو الفخ الذي وقعت فيه أوراق بحثية منشورة:** لو قارنّا صورًا حقيقية بصيغة PNG مقابل صور مولّدة بصيغة JPEG، لحصلنا على دقة 99% — ولكنا في الواقع نكتشف **صيغة الملف**، لا الزيف. الأداة كانت ستبدو عبقرية وهي عديمة القيمة تمامًا.

قِسنا هذا، ووثّقناه بالأرقام والرسوم، وبنينا قواعد التصميم عليه.

---

## ١١. الأخطاء التي وُجدت وأُصلحت

خلال المراجعة النهائية وجدنا **ستة أخطاء حقيقية**. أذكر اثنين لأنهما يوضحان طبيعة العمل.

### الخطأ الأول (خطير): صور أصلية صُنّفت كموسومة بالذكاء الاصطناعي

الأداة كانت تصنّف **صورًا فوتوغرافية أصلية من التسعينيات** على أنها "تحمل علامة ذكاء اصطناعي". السبب: الصورة كانت تحمل داخلها اسم الماسح الضوئي الذي رقمنها، والأداة اعتبرت أي نص مدفون دليلًا.

**هذا أسوأ اتجاه ممكن للخطأ** — أن تخبر مراجعًا بأن صورة حقيقية موسومة كذكاء اصطناعي. أُصلح، والصورتان الآن تُصنّفان بشكل صحيح.

### الخطأ الثاني (الأخطر منهجيًا): اختبار يكذب

كان لدينا اختبار آلي يطبع "**8/8 ناجح**" — بينما كان يفحص **ملفًا واحدًا فقط** من الثمانية. اختبار أخضر لا يختبر شيئًا.

**وهذا هو السبب المباشر في أن الخطأ الأول بقي مخفيًا.** لدينا حالة اختبار مصممة تحديدًا لالتقاطه، لكنها لم تكن تعمل أصلًا. أُصلح، والاختبار الآن يفشل بصوت عالٍ إذا لم تُنفَّذ كل الحالات.

---

## ١٢. ما هو مُثبت وما هو غير مُثبت

### مُثبت

- مسار العلامة الرسمية يعمل: 8/8 حالات اختبار، **بالإضافة إلى التقاط صورة ChatGPT حقيقية**
- خاصيتان مستقرتان ومقيستان (0.7% و 0.009 تغيّر بين المقاطع)
- العوامل المُربكة مقيسة وموثّقة بالأرقام، لا مفترضة
- الأداة لا تنهار على مدخلات شاذة (ملفات تالفة، صيغ ألوان غريبة، أحجام مختلفة) — اختُبرت
- النتائج قابلة لإعادة الإنتاج: تشغيلان متتاليان ينتجان ملفًا متطابقًا

### غير مُثبت — وهذا مكتوب في المستند نفسه

الأداة **ليست مصنّفًا**، ولا يوجد **أي ادعاء بنسبة دقة** في أي مكان في المشروع. السبب بسيط: لم نُجرِ تجربة مضبوطة على مجموعة بيانات موثّقة.

لدينا ملاحظة أولية مثيرة — صورة ChatGPT أعطت قراءة تقارب **ضعف** ما أعطته الصور السبع غير المولّدة. لكنها عيّنة واحدة، وتلك الصورة تحمل أيضًا علامات إعادة تحجيم، وقد أثبتنا بأنفسنا أن التحجيم يحرّك الأرقام بقوة.

كتبنا هذا صراحة في المستند بدل تحويله إلى ادعاء يبيع.

### لماذا أعتبر هذا نجاحًا

المشروع الأسهل كان سيقول: "أداة كشف صور ذكاء اصطناعي بدقة 98%". كنت ستصدّقه، وكان سينهار عند أول اختبار حقيقي.

ما بنيناه بدلًا من ذلك أداة **تعرف حدودها وتقيسها**:
- حذفنا خاصية لأنها فشلت في اختبار وضعناه نحن لأنفسنا
- حذفنا "اكتشافًا" لأننا قسنا الضجيج واكتشفنا أنه أكبر من الإشارة
- أصلحنا اختبارًا كان يكذب علينا بادعاء النجاح
- ورفضنا الادعاء الوحيد المغري الذي كان بإمكاننا تقديمه

في أي مجال يتعلق بالامتثال القانوني، **الأداة التي تقول "لا أعرف" بوضوح أكثر قيمة من الأداة التي تخمّن بثقة** — لأن الثانية تدفع الناس إلى قرارات خاطئة وهم مطمئنون.

---

## ١٣. الخطوة التالية

لتحويل الملاحظة الأولية (عيّنة واحدة) إلى نتيجة حقيقية، نحتاج **زوجًا مضبوطًا**: مئات الصور الحقيقية ومئات الصور المولّدة، **بنفس الصيغة، ونفس الدقة، ونفس مسار المعالجة تمامًا**.

عندها فقط تكون كل العوامل المُربكة متطابقة بين المجموعتين، والفرق الوحيد المتبقي هو: مولّدة أم لا. وحينها فقط يصبح الرقم الثالث ذا معنى.

هذه الخطوة مكتوبة في المستند كخطوة تالية معلنة، لا كثغرة مخفية.

---

## ١٤. مرجع: كل رقم مقيس

| القياس | القيمة | المعنى |
|---|---|---|
| الميل، kodim01 (حقيقية) | −1.76 | نطاق طبيعي |
| الميل، kodim05 (حقيقية) | −2.31 | نطاق طبيعي |
| الميل، تحجيم bilinear (حقيقية) | −3.98 | عامل مُربك، أكبر أثر مقيس |
| الميل، صورة ChatGPT (مولّدة) | −3.29 | داخل منطقة العامل المُربك — غير حاسم |
| hf_residual، kodim01 | −0.56 | خط الأساس |
| hf_residual، bilinear | −1.98 | عامل مُربك |
| nyquist_peak، 7 صور غير مولّدة | 0.377 – 0.491 | نطاق الأساس |
| nyquist_peak، صورة ChatGPT | 0.895 | ~الضعف — عيّنة واحدة، غير مضبوطة |
| استقرار الميل بين المقاطع | 0.7% | صالح |
| استقرار hf_ratio (محذوفة) | 80% | غير صالح — حُذفت الخاصية |
| استقرار hf_residual | 0.009 وحدة لوغاريتمية | صالح، أفضل بـ~17 ضعفًا |
| تباين الصليب، بدون نافذة | ~2.3 وحدة لوغاريتمية | أثر الحدود موجود |
| تباين الصليب، مع نافذة Hann | ~0.05 وحدة لوغاريتمية | أُزيل الأثر، ~50 ضعفًا |
| حالات اختبار المصدر | 8/8 | القواعد الأربع + ثلاث حالات سلبية |

---

*This document accompanies the `synthetic-image-triage` repository. Every number in it was measured, not estimated.*

*هذا المستند مرافق لمستودع `synthetic-image-triage`. كل رقم فيه مقيس، لا مقدَّر.*
