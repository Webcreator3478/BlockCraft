# BlockCraft

Minecraft game clone written in Rust, using the Bevy game engine.

<br>

![image](./docs/preview1.png)

![image](./docs/preview2.png)

<br>

# Table of contents

- [Features](#features)
- [Installation](#installation)
    - [Package Managers](#package-managers)
    - [Manual](#manual)
- [Controls](#controls)
- [Multiplayer](#multiplayer)
- [Saves](#saves)
- [Command-line options](#command-line-options)
    - [Client](#client)
    - [Server](#server)
- [Licenses](#licenses)
- [How to Build](#how-to-build)
    - [Prerequisites](#prerequisites)
    - [Running the Project](#running-the-project)
- [Contributing](#contributing)
    - [Guidelines](#guidelines)

<br>

# Features
- Procedurally generated worlds with biomes (Plains, Forest, Mountains, Desert, Savanna, Jungle, Ice Plain, Ice Spikes, Flower plains, Flower forest, Grove, rivers and oceans), trees, cactus, tall grass, ferns and flowers, in four world types: default, large biomes, archipelago and single biome.
- Multiplayer functionality.
- Day/night cycle
- Block breaking and placing mechanics.
- Inventory system with a functional hotbar.
- An item browser beside the open inventory: every item of the game, searched by name or by `#category` and filtered by category chips; a drawer at the right edge in a small window. It is also the recipe book: the recipes and the uses of any item, the furnace's included, the ingredients you lack in red, in Survival what you can craft now, and a button that fills the crafting grid with a recipe, or lays a faint ghost of it over the grid, the lacking cells in red, when ingredients are missing. Ctrl+click on an item fills the grid with its first recipe made now, without opening it. In Creative it hands out stacks of any item, and destroys the stack you hold. A over any item slot bookmarks its item: the bookmarks show above the list, kept for each world and each server, and a Recent row under them holds the last items crafted in the session.
- World saving and loading.
- Survival and creative game modes: in survival, players have 10 hearts, cannot fly and get hurt by falls of more than 3 blocks; a dead player respawns at the spawn of the world. New players start in survival.
- A furnace that smelts with an input, a fuel and an output slot, also while nobody watches it, as long as its chunk is loaded: iron and gold ore into ingots, diamond ore into diamonds, sand into glass, cobblestone into stone and logs into charcoal. Coal and charcoal burn for 8 items, wood for 1.5, wooden tools and sticks for less. Lit, it glows; it keeps what it holds in the save and drops it when broken.
- Tool tiers: wooden, stone, iron, golden and diamond pickaxes, axes, shovels, hoes and swords, each tier faster and longer-lasting (gold is the fastest and wears out the soonest). Ores need a pickaxe of their level, or they break without dropping anything: a wooden one for coal, a stone one for iron, an iron one for gold and diamonds, found deep underground. Nine ingots or diamonds make a block of iron, gold or diamond, and a block gives them back.
- A bucket, of three iron ingots, takes a water source and pours it elsewhere, where it flows.
- Weather: clear spells, rain and thunderstorms follow each other on their own, the same for every player and kept in the save. Rain rolls in under thicker, darker clouds and a grey sky that dims the light and closes the fog in; drops slanted by the wind splash on the ground and ring the water, but not under a roof or the leaves; snow falls in the cold, nothing in the deserts. In the High and Ultra shaders the ground open to the rain darkens, glistens and gathers puddles that mirror the sky, and dries after. Thunderstorms strike lightning that lights the world and the clouds, its thunder heard after the flash. The rain hisses in the open and drums on a roof, at its own Weather volume in Settings > Audio.
- Sprinting, sneaking and swimming.
- In-game chat, with commands open to every player: `/time set <day|night>`, `/give <item> <count>` (e.g. `/give oak_log 64`), `/gamemode <creative|survival>` and `/weather <clear|rain|thunder>`, completed as they are typed (Tab, ↑↓).
- Customizable keybindings, and a render distance set in Settings > Video or with O and P.

<br>

# Installation

## Manual

You can download the game for **Windows** and **Linux** from the [Releases page](https://github.com/Webcreator3478/BlockCraft/releases) of the GitHub repository.

Once downloaded, extract the archive for your operating system. The executable will be located in the `/bin` folder of the extracted directory.

## Package Managers

### Arch Linux

There are 2 [AUR](https://aur.archlinux.org) packages available for blockcraft:

- [rustcraft](https://aur.archlinux.org/packages/rustcraft): The latest release built from source
- [rustcraft-bin](https://aur.archlinux.org/packages/rustcraft-bin): The latest release pre-built

You can install them using your preferred [AUR helper](https://wiki.archlinux.org/title/AUR_helpers), e.g. `paru`:
```bash
paru -S rustcraft
