# Test game for Dual Text Mode. Each line exercises one case; tests/project/game/tl/korean has the translation.
define config.save_directory = "dual-text-mode-tests"
define config.has_sound = False
define config.has_music = False
define config.has_voice = False

define e = Character("Eileen")
default hero = "Alex"

label start:
    e "Hello there."
    extend " How are you today?"
    e "This line is split in the translation."
    $ speaker = "Guest"
    speaker "A string speaker talks, [hero]."
    e "This translation carries pacing tags."
    e "This is a long line that wraps onto a second line of the dialogue box, so the second text has to be interleaved with it line by line."
    "A narrator line closes the scene."
    pause
    e "After the pause."
    return
