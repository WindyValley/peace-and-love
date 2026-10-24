# Peace And Love

> Convince Minecraft's hostile mobs to put down their weapons and do business with you.

Tired of creepers blowing up your farm, or chasing endermen across the world for a single ender pearl? **Peace And Love** turns vanilla hostile mobs into **neutral, tradable creatures** — no sword required, just emeralds. Built for players who love farming, building, and peaceful survival.

This is an **early Beta release (0.1.0)**. The core gameplay is complete and playable; balance and polish are still being refined.

---

## What it does

Once installed, mobs that used to hunt you on sight become **neutral**:

- 🕊️ **No more unprovoked attacks** — 38 vanilla hostile mobs default to peaceful (creepers, skeletons, zombies, endermen, wardens, and more).
- 💎 **Right-click to trade** — walk up to a neutral mob and right-click empty-handed to open a trading screen; spend emeralds on their drops.
- ⚔️ **Hit one and it fights back** — neutral is not harmless. A mob holds a grudge against whoever struck it, and won't drag nearby teammates into it.
- 👥 **Mobs call for backup** — same-species mobs within 4 blocks come to help, but the alert doesn't chain infinitely.
- 🧘 **Walk it off** — after 30 seconds out of combat, or once you put 32 blocks between you, the mob calms down and returns to neutral.

---

## How to play

1. Find a formerly hostile mob that is now neutral (it won't chase you anymore).
2. Right-click it **empty-handed** to open a familiar villager-style trade screen.
3. Spend **emeralds** on its drops: ender pearls, bones, gunpowder, blaze rods, and more.
4. **Each offer can be bought once per in-game day** and restocks daily, preventing infinite farming.
5. Prices scale with drop rarity — common drops cost a few emeralds; rare items like a wither skeleton skull cost far more (exact prices are whatever the mob offers in-game).

> 📌 **Bosses don't trade.** Bosses such as the Wither are neutralized and won't attack unprovoked, but they won't become merchants. **The Ender Dragon is unaffected** and remains the final challenge.

---

## Admins: keep specific mobs hostile

You decide which mobs stay hostile using a **whitelist** (mobs in it keep their vanilla behavior):

```
/pal whitelist add minecraft:pillager      # keep pillagers hostile
/pal whitelist remove minecraft:pillager   # neutralize them again
```

- By default, **6 mobs stay hostile**: pillager, vindicator, evoker, vex, phantom, and shulker.
- Changes take effect **immediately, no restart needed**, and can be toggled back and forth.

---

## Installation

| | Requirement |
|---|---|
| Minecraft | **1.21.1** |
| Java | 21 |
| Loader | **Fabric** or **NeoForge** |
| Dependency | **Architectury API** (plus Fabric API on Fabric) |

✨ **Server-side only — vanilla clients don't need the mod.** Trading uses the vanilla villager screen and network protocol, so players on a plain vanilla client can join a server running the mod and trade normally. Perfect for a peaceful survival server. In singleplayer, just install it for your loader as usual.

---

## What it does NOT do

- **It does not touch third-party mod mobs** — only the 38 adapted vanilla mobs are affected; mobs added by other mods are unchanged.
- **It doesn't change world difficulty, remove drops, or add custom items** — it simply offers a peaceful alternative to combat.
- Neutral mobs keep their own quirks (e.g. endermen still anger when stared at); the mod only changes whether they actively seek a fight with players.

---

## Compatibility & feedback

This is a Beta — balance feedback and bug reports are welcome in the issue tracker. The mod only adjusts server-side behavior and is compatible with the vast majority of client-side optimization mods, shaders, and resource packs.

**License:** MIT — both the source code and the mod icon (icon.png) are released under MIT. Mob textures and the trading screen use vanilla Minecraft resources; the mod icon is original art.
