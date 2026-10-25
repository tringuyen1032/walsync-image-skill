---
name: walsync-image
description: Create and edit images (text-to-image, image-to-image, restyling, combining up to 16 reference images) with the Walsync image service at img.walsync.com, using GPT Image 2.5 Flare / Sunburst. Use whenever the user asks to generate, draw, design, illustrate, restyle or edit an image or photo, or says "tạo ảnh", "vẽ", "chỉnh sửa ảnh", "sửa ảnh", "làm ảnh". Needs a personal Walsync key that the user was given; ask for it if it is missing.
---

# Walsync image

Generates and edits images through `https://img.walsync.com` with a personal key. Everything goes through one stdlib-only
script, `scripts/walsync_image.py` (Python 3.8+, nothing to install). In the commands below, `SKILL_DIR` is the folder that
contains this file; use its absolute path.

```
python3 SKILL_DIR/scripts/walsync_image.py usage
python3 SKILL_DIR/scripts/walsync_image.py generate "PROMPT" [-m flare|sunburst|gpt-image-2] [-q auto|low|medium|high|xhigh|max] [-a square|landscape|portrait] [-n 1-4] [-o PATH]
python3 SKILL_DIR/scripts/walsync_image.py edit "PROMPT" -i photo.png [-i other.png ...] [same options]
```

On success it prints `IMAGE: /absolute/path.png` for each image and `DONE: ...` with the images left in the quota.

## 1. The key (do this first, every time)

The service only works with a personal key. **Never invent, guess, search for, or reuse a key from anywhere else.**

1. Run `usage`. If it prints a quota line, a key is already saved: go to step 2.
2. If it exits with code 3 / `NO_KEY`, **ask the user for their key** and wait for the answer, for example:
   "Để tạo ảnh mình cần KEY Walsync mà người cung cấp đã gửi cho bạn. Bạn dán KEY vào đây giúp mình nhé." (use the user's language).
3. Save what they send by piping it to `setkey` through stdin, never as a command-line argument:
   `printf '%s' 'THE_KEY' | python3 SKILL_DIR/scripts/walsync_image.py setkey --stdin`
   `setkey` checks the key with the server and stores it in `~/.config/walsync-image/key` (owner-only permissions;
   `%APPDATA%\walsync-image\key` on Windows). Alternatively the user can run `python3 SKILL_DIR/scripts/walsync_image.py setkey`
   in their own terminal and paste the key at the hidden prompt.
4. If `setkey` or any call says `KEY_REJECTED` (exit 5), tell the user the key was not accepted and ask them to re-check it or
   get a new one from whoever gave it to them. Do not retry with other values.

Key hygiene: never print the key back, never write it into project files, notes, memory, commits, logs or screenshots, and
never include it in a prompt. Only `setkey` (or the `WALSYNC_IMAGE_KEY` environment variable) may hold it.

## 2. Quota

Each key may create **50 images per day (a rolling 24 hours; the key itself never expires)** (every image in `-n` counts; a request that fails is not charged).
- Run `usage` before a batch and tell the user how many images are left when it matters.
- Ask before generating more than 4 images in one go. Do not loop to "try again" for variations without being asked.
- On `QUOTA_USED_UP` (exit 4) stop, tell the user when the next slot frees up (the message says so; the daily allowance comes back gradually as older images pass 24 hours), and offer to continue
  then. Do not look for ways around the limit.

## 3. Making images

- `generate` for a new image, `edit` when the user gives or points to existing images (photo to restyle, object to change,
  several references to combine). Send the original with `-i`; describe only what should change and say what must stay the same.
- Models: `flare` (default) is fast and good for everyday work; `sunburst` is slower and more precise for detailed or
  text-heavy images; `gpt-image-2` is also available. `models` lists everything the key may use. Other models are refused.
- `-a landscape|portrait|square` sets the shape; `-q` is a quality hint. The service decides the final size and quality, and
  the `DONE:` line reports what it returned.
- Write the prompt in the language the user is most comfortable with, but concrete: subject, setting, light, style, mood,
  camera or medium. For text inside the image, quote the exact words. Natural, believable results usually come from plain
  photographic wording (real light, real materials) rather than piling on adjectives.
- Source images must be png, jpg, webp or gif, up to 25 MB each, at most 16 per request.
- Save into the user's working folder (default `./walsync-images/`) unless they name another place, then show them the
  result: give the file path and, if the interface can display images, show the image itself. Say which prompt and model you used.

## 4. Problems

| Message | What to do |
|---|---|
| `NO_KEY` (exit 3) | Section 1: ask the user for the key. |
| `KEY_REJECTED` (exit 5) | Key wrong or revoked: ask the user to check it. |
| `QUOTA_USED_UP` (exit 4) | Section 2. |
| `ERROR 400 ... rejected` | The request was refused (often a content-policy block). Tell the user plainly and suggest a different wording; do not try to disguise the request. |
| `ERROR 502/503`, `network problem` | Temporary. The script already retried twice; nothing was charged. Wait a minute and try once more, then tell the user. |
