# OBS Overlay Prototype

Standalone prototype for a Cookie Clicker OBS Browser Source overlay. It
receives local UDP events from the bot, streams them to a transparent browser
canvas, and spawns the "I did that" sticker at clicked shimmer coordinates.

## Run

```powershell
python .\obs_overlay\server.py
```

Useful options:

```powershell
python .\obs_overlay\server.py --demo-clicks
python .\obs_overlay\server.py --no-snake
python .\obs_overlay\server.py --bidens 5
python .\obs_overlay\server.py --fruit-interval-seconds 5
python .\obs_overlay\server.py --port 47651 --udp-port 47651
```

Then add an OBS Browser Source:

```text
http://127.0.0.1:47651/
```

## OBS Notes

Use Game Capture for Cookie Clicker and put the Browser Source above it.

Size the overlay source to exactly match the Cookie Clicker game capture source.
The bot sends normalized game-client coordinates, so the overlay still lines up
in OBS even if the real game window is minimized or elsewhere.

No chroma key is needed; the Browser Source page background is transparent.
Enable **Control Audio via OBS** on the Browser Source if you want the overlay
sound effects to appear as their own channel in the OBS audio mixer.
In Advanced Audio Properties, make sure the Browser Source is not muted and is
assigned to the stream/recording track you use, usually Track 1. Use
`Monitor and Output` only if you also want to hear the sounds locally.

The server listens for bot UDP events on `127.0.0.1:47651` and serves the OBS
Browser Source at `http://127.0.0.1:47651/`.

Snake mode is enabled by default. Each shimmer click spawns a golden-cookie
target for the self-playing grandma-head snake while still showing the Biden
pointer animation. The Browser Source also spawns a random target immediately
and then every 20 seconds for visual verification. Use `--no-snake` to disable
the mini game. The snake treats the overlay edges as borders and restarts from
one segment when it hits a wall or itself.

The server can also emit random target events. Set `--fruit-interval-seconds 0`
to disable the server-side timer or lower it while testing.
Use `--bidens SECONDS` to spawn an extra Biden sticker every `SECONDS` seconds;
for example, `--bidens 5` is useful for testing snake growth and target chasing
without waiting for bot clicks.

Grandma switches between classic snake movement and heat-seeking movement every
three eaten Bidens. Mode changes are announced in a translucent combat-log panel
in the bottom-right corner of the overlay. Names use World of Warcraft class
colors: `biden` is Hunter green, `grandma` is Warlock purple, and `durgular` is
Warrior tan. Every tenth Biden spawn also adds a pink italic whisper from
`biotachyonic` with a Druid-orange name. Durgular also yells in chat every 20
seconds.

Snake mode uses local Cookie Clicker game sprites copied from the Steam install:
`buildings.png` for the smoothed grandma segment head and `goldCookie.png` for
the target.
When the snake eats a target, the Browser Source plays `grandma_cookie.mp3`.
When a Biden sticker spawns, it plays `dean_scream.mp3`.
To test OBS audio routing without waiting for gameplay, open these URLs while
the server and OBS Browser Source are running:

```text
http://127.0.0.1:47651/test-sound/dean
http://127.0.0.1:47651/test-sound/grandma
```

The overlay Browser Source mixer meter should move immediately after either
test URL is opened.

The bundled prototype asset is a transparent cutout made from a gas-pump-style
reference image:
https://knowyourmeme.com/photos/2345278-i-did-that-gas-station-stickers
