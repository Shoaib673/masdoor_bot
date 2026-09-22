"""
Chat-command Minecraft bot for a Fabric/Aternos server on Minecraft 26.1.2.

Built on BotMine (https://pypi.org/project/botmine/), a young, native-Python
Java-edition bot library. It does NOT yet do world/block scanning, so this
script can't "find the nearest bed" or "find the cobblestone generator" by
itself -- you give it coordinates, and it acts on them. It also has no
sleep() or attack-entity call yet, so those are stubbed with clear TODOs
for when BotMine adds them (or if we switch to Mineflayer later).

Usage:
    pip install botmine
    python mc_bot.py

Then in-game (or from another account), type in chat:
    !come                  -> bot follows you
    !stop                  -> bot stops following / stops current task
    !mine X Y Z            -> bot walks to (X,Y,Z) and mines that block
    !mine X Y Z N          -> mines N blocks starting at (X,Y,Z), going +Y
                               (handy for a vertical cobblestone generator
                               column: give it the bottom block + a count)
    !goto X Y Z             -> bot walks to (X,Y,Z), no mining
    !status                -> prints basic server/bot info to chat
    !help                  -> lists commands
"""

import time
import botmine

# ---- Fill these in for your Aternos server ----
HOST = "oneblocksurviva-VWKW.aternos.me"
PORT = 62776
NICKNAME = "MateBot"          # pick any name not already taken on the server
VERSION = "26.1.2"
COMMAND_PREFIX = "!"          # chat commands must start with this
# -------------------------------------------------

bot = botmine.Bot(
    HOST,
    PORT,
    nickname=NICKNAME,
    version=VERSION,
    auto_connect=False,
    auto_swap_tools=True,      # auto-picks a known tool before mining
)

# Tracks whether we're mid-task so !stop can interrupt cleanly.
state = {"busy": False, "cancel": False}


def send(msg):
    bot.chat(msg)
    print(f"[bot] {msg}")


def cmd_help(args, sender):
    send(
        "Commands: !come, !stop, !goto X Y Z, "
        "!mine X Y Z [count], !status"
    )


def cmd_status(args, sender):
    try:
        info = bot.server_info()
        send(f"Players online: {info.get('players_count')}, "
             f"time: {info.get('time')}")
    except Exception as e:
        send(f"Couldn't read server info: {e}")


def cmd_come(args, sender):
    send(f"Coming to you, {sender}.")
    bot.follow_player(sender)


def cmd_stop(args, sender):
    state["cancel"] = True
    try:
        bot.follow_stop(sender)
    except Exception:
        pass
    try:
        bot.stop_following()
    except Exception:
        pass
    send("Stopped.")


def cmd_goto(args, sender):
    if len(args) < 3:
        send("Usage: !goto X Y Z")
        return
    x, y, z = (float(a) for a in args[:3])
    send(f"Heading to ({x:.0f}, {y:.0f}, {z:.0f})")
    bot.goto(x=x, y=y, z=z)


def cmd_mine(args, sender):
    if len(args) < 3:
        send("Usage: !mine X Y Z [count]")
        return
    x, y, z = (int(float(a)) for a in args[:3])
    count = int(args[3]) if len(args) >= 4 else 1

    state["busy"] = True
    state["cancel"] = False
    send(f"Mining {count} block(s) starting at ({x}, {y}, {z})...")

    for i in range(count):
        if state["cancel"]:
            send("Mining cancelled.")
            break
        target_y = y + i  # walk up one block at a time, e.g. a generator column
        try:
            bot.goto(x=x, y=target_y, z=z)
            bot.destroy(x=x, y=target_y, z=z)
        except Exception as e:
            send(f"Couldn't mine block {i + 1}: {e}")
            break
        time.sleep(0.3)  # small pause so we don't spam packets

    state["busy"] = False
    if not state["cancel"]:
        send("Done mining.")


# TODO: once BotMine (or a future library) exposes block-scanning and a
# right-click/"use on block" interaction, wire up:
#   !sleep  -> find nearest bed within N blocks, walk to it, if a villager
#              is standing on it, nudge/attack it off, then use_item on the
#              bed block to sleep. None of that is possible yet with the
#              current library version (no entity list, no interact-block
#              call, no attack call).
def cmd_sleep(args, sender):
    send(
        "Sleep isn't wired up yet -- BotMine doesn't expose block-scanning "
        "or bed interaction in this version. If you give me the bed's "
        "coordinates I can walk the bot there with !goto, but actually "
        "using the bed needs a library update."
    )


COMMANDS = {
    "help": cmd_help,
    "status": cmd_status,
    "come": cmd_come,
    "stop": cmd_stop,
    "goto": cmd_goto,
    "mine": cmd_mine,
    "sleep": cmd_sleep,
}


def on_chat(username, message):
    if username == NICKNAME:
        return
    if not message.startswith(COMMAND_PREFIX):
        return

    parts = message[len(COMMAND_PREFIX):].strip().split()
    if not parts:
        return
    name, args = parts[0].lower(), parts[1:]

    handler = COMMANDS.get(name)
    if handler is None:
        send(f"Unknown command '{name}'. Try !help")
        return

    if state["busy"] and name not in ("stop", "help", "status"):
        send("Still busy with the last task -- send !stop to cancel it first.")
        return

    try:
        handler(args, username)
    except Exception as e:
        send(f"Error running !{name}: {e}")


def on_join(player):
    print(f"[event] {player} joined")


def on_leave(player):
    print(f"[event] {player} left")


def on_kicked(reason):
    print(f"[event] Bot was kicked: {reason}")


def main():
    bot.on("chat", on_chat)
    bot.on("join", on_join)
    bot.on("leave", on_leave)
    bot.on("kicked", on_kicked)

    print(f"Connecting to {HOST}:{PORT} as {NICKNAME} (MC {VERSION})...")
    bot.connect()
    send("Online. Type !help in chat to see what I can do.")
    bot.wait()  # blocks and processes events until disconnected


if __name__ == "__main__":
    main()
