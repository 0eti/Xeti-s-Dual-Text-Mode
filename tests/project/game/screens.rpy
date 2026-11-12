# Minimal screens for the test game.
define config.screen_width = 1280
define config.screen_height = 720

# Like Eternum, the say screen sets the dialogue size itself, so the style alone gives the wrong
# line height. The mod has to measure the drawn text and correct the layout.
default dialogue_size = 30

style say_dialogue:
    size 24

screen say(who, what):
    window:
        id "window"
        xfill True
        ysize 260
        yalign 1.0
        background Solid("#000a")

        if who is not None:
            text who id "who" xpos 60 ypos 12 size 24

        text what id "what":
            xpos 60
            ypos 50
            xsize 1160
            size dialogue_size

screen main_menu():
    tag menu
    add Solid("#000")
