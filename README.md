# Walsync image skill

A skill for AI agents (Claude Code, Codex, Hermes, OpenCode and anything that reads `SKILL.md`) that creates and edits
images through the Walsync image service (`https://img.walsync.com`, GPT Image 2.5 Flare / Sunburst).

You need a personal **key** from the person who gave you this link. The key is **not** in this repository: the agent asks you
for it when it installs the skill, and stores it only on your machine.

- 50 images per 48 hours per key
- text to image and image editing (up to 16 reference images)
- nothing to install except the skill itself (Python 3.8+, standard library only)

## Install (ask your agent)

Paste this to your agent. It does not contain a key:

```text
Hãy cài skill tạo ảnh Walsync cho tôi.
1. Clone https://github.com/tringuyen1032/walsync-image-skill vào thư mục skills của chính bạn, đặt tên thư mục là
   walsync-image (ví dụ Claude Code: ~/.claude/skills/walsync-image, Codex: ~/.codex/skills/walsync-image,
   Hermes: ~/.hermes/skills/walsync-image, OpenCode: ~/.config/opencode/skills/walsync-image; nếu agent của bạn
   dùng thư mục khác thì dùng thư mục đó). Nếu đã có thì chạy git pull.
2. Đọc SKILL.md trong thư mục vừa clone và làm đúng theo đó.
3. Sau khi cài, HỎI tôi KEY tạo ảnh Walsync và đợi tôi nhập. Không được tự nghĩ ra, tìm hay dùng key nào khác.
   Lưu key bằng lệnh `setkey` của skill (qua stdin), không in lại key và không ghi key vào file nào khác.
4. Chạy `usage` để xác nhận key hoạt động rồi báo tôi còn bao nhiêu ảnh, sau đó tạo thử một ảnh nhỏ cho tôi xem.
```

English version:

```text
Install the Walsync image skill for me.
1. Clone https://github.com/tringuyen1032/walsync-image-skill into your own skills folder as walsync-image
   (Claude Code: ~/.claude/skills/walsync-image, Codex: ~/.codex/skills/walsync-image, Hermes: ~/.hermes/skills/walsync-image,
   OpenCode: ~/.config/opencode/skills/walsync-image; otherwise your agent's own skills folder). If it exists, run git pull.
2. Read SKILL.md in that folder and follow it.
3. After installing, ASK me for my Walsync image KEY and wait for me to type it. Never invent, look up or reuse another key.
   Save it with the skill's `setkey` command (through stdin); do not echo it or write it anywhere else.
4. Run `usage` to confirm the key works, tell me how many images I have left, then make one small test image for me.
```

## Manual use

```bash
git clone https://github.com/tringuyen1032/walsync-image-skill ~/.claude/skills/walsync-image
python3 ~/.claude/skills/walsync-image/scripts/walsync_image.py setkey      # paste the key (hidden)
python3 ~/.claude/skills/walsync-image/scripts/walsync_image.py usage
python3 ~/.claude/skills/walsync-image/scripts/walsync_image.py generate "a cat reading under a lamp, warm evening light"
python3 ~/.claude/skills/walsync-image/scripts/walsync_image.py edit "make it a watercolor painting" -i cat.png
```

The key is stored in `~/.config/walsync-image/key` (`%APPDATA%\walsync-image\key` on Windows) or can be set in the
`WALSYNC_IMAGE_KEY` environment variable.

## Notes

- The service only forwards image generation and editing for a fixed list of image models; anything else is refused.
- Failed requests are not charged against the quota. Prompts and images are not stored by the Walsync gateway.
