# TODO

Finish making sure the github actions setup uses the correct file references, as we have moved installer related files into installer, also, it seems the build script is still plasing build and dist in the project root and not in the installer folder

If possible, update our github pages page so it has a link to the installer at the top, not just the links. And if possible, populate it with missing information from the @docs\README.md , and give it a style that matches how the README.md would be rendered(color and typography)

Add a screenshot of the bot in action, and a gif of a sidebyside of the bot hud and the game running

Add the ability to auto click fortunes, check the game's source for how fortunes work, we'll have to verify the ascension skill has been unlocked to do so.

Create a new Ascension tab in the HUD that will let us see what ascension buffs we currently own and what we have available for purchase, and what we can afford.

When we sacrifice 200 of everything for Train Secondary Aura(Cookie dragon), we need to make sure we don't take a loss on any of the building minigames, if there would be a loss we need to make sure we have enough buildings remaining after the sacrifice so we do not.

A bug has surfaced where if the farm minigame window is not completely visible our automation gets stuck in a loop between autoclicking and attempting to interact with the farm

The center column where the minigames are shown needs a scrolling or better targeting mechanism, for example, currently if the minigame for the Wizard Tower is out of view, the automation will attempt to click it, but the cursor is actually landing in the Pantheon(temple) area and the spell that is intended is not cast

Add a graph that shows CPS over time