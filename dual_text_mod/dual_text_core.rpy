# Xeti's Dual Text Mode
#
# 모드의 함수와 상태는 store.dual_text_mod 네임스페이스에 둔다. 게임 코드와 이름이 겹치지 않고,
# 실행 중에 바뀌는 값은 클래스 속성에 두어 세이브·롤백에 섞이지 않게 한다.
# 화면·스타일·트랜스폼 이름은 Ren'Py에서 전역이므로 모두 dual_text_ 로 시작한다.

style dual_text_text is text:
    font "dual_text_mod/Paperlogy-6SemiBold.ttf"

style dual_text_button_text is button_text:
    font "dual_text_mod/Paperlogy-6SemiBold.ttf"

style dual_text_settings_scrollbar is default:
    bar_vertical True
    bar_invert True
    xsize 10
    base_bar Solid("#ffffff33")
    thumb Solid("#ffffffcc")
    unscrollable "hide"

default persistent.show_dual_text = True
default persistent.sub_language = "None"
default persistent.dual_text_size = 30
default persistent.dual_text_yalign = 0.8
default persistent.dual_text_xpos = 0.2
default persistent.dual_text_line_spacing = 0
default persistent.dual_text_color = "#FFFFFF"
default persistent.dual_text_alpha = 100
default persistent.dual_text_behind = False
# 원본 대사 줄 간격. None이면 게임이 정한 값을 그대로 둔다.
# (예전 persistent.original_line_spacing은 기본값 0이 게임 값을 덮어써서 더 이상 읽지 않는다)
default persistent.dual_text_dialogue_line_spacing = None

init python in dual_text_mod:
    import store

    # --------------------------------------------------------------------------
    # 서브텍스트 박스 너비 (화면 너비 대비 비율)
    # --------------------------------------------------------------------------

    # 예전 버전은 픽셀(persistent.dual_text_xmaximum)로 저장했으므로 한 번 비율로 옮긴다.
    if store.persistent.dual_text_width is None:
        if store.persistent.dual_text_xmaximum is not None:
            _width = store.persistent.dual_text_xmaximum / float(store.config.screen_width)
        else:
            _width = 0.7
        store.persistent.dual_text_width = max(0.1, min(1.0, round(_width, 2)))

    def box_width():
        """서브텍스트 박스 너비(px). 화면 오른쪽 끝을 넘지 않게 자른다."""
        width = store.persistent.dual_text_width or 0.7
        room = 1.0 - (store.persistent.dual_text_xpos or 0.0)
        return max(1, int(store.config.screen_width * max(0.05, min(width, room))))

    # --------------------------------------------------------------------------
    # 서브텍스트 색상
    # --------------------------------------------------------------------------

    def text_color():
        """저장된 색에서 투명도를 뺀 색. 투명도는 dual_text_fade로 글자와 테두리에 함께 준다."""
        try:
            return store.Color(store.persistent.dual_text_color or "#FFFFFF").replace_opacity(1.0)
        except Exception:
            return store.Color("#FFFFFF")

    def apply_color(picker):
        store.persistent.dual_text_color = picker.color.hexcode
        renpy.restart_interaction()

    # --------------------------------------------------------------------------
    # 원본 대사 줄 간격
    # --------------------------------------------------------------------------

    class _LineSpacing(object):
        game_value = None   # 게임이 정한 값
        applied = None      # 모드가 마지막으로 넣은 값 (안 건드렸으면 None)

    def apply_line_spacing():
        state = _LineSpacing
        style = store.style
        target = store.persistent.dual_text_dialogue_line_spacing
        current = style.say_dialogue.line_spacing

        # 모드가 넣은 값이 아니면 지금 값이 게임 값이다.
        # (Ren'Py는 언어를 바꾸거나 시작할 때 스타일을 init 직후 상태로 되돌린다)
        if state.applied is None or current != state.applied:
            state.game_value = current
            state.applied = None

        if target is None:
            if state.applied is not None:
                style.say_dialogue.line_spacing = state.game_value
                style.rebuild()
                state.applied = None
            return

        if current != target:
            style.say_dialogue.line_spacing = target
            style.rebuild()
        state.applied = target

    def start_custom_line_spacing():
        """'직접 조절'을 누르면 지금 게임 값에서 슬라이더를 시작한다."""
        current = store.style.say_dialogue.line_spacing or 0
        store.persistent.dual_text_dialogue_line_spacing = max(0, min(50, int(current)))

    # 인터랙션마다 확인한다. 값이 같으면 아무것도 하지 않으므로 비용은 비교 한 번이다.
    if apply_line_spacing not in store.config.interact_callbacks:
        store.config.interact_callbacks.append(apply_line_spacing)

    # --------------------------------------------------------------------------
    # 서브텍스트 찾기
    # --------------------------------------------------------------------------

    class _Cache(object):
        key = None
        result = ""

    def wanted_language():
        """서브텍스트로 보여 줄 언어. None은 원문 스크립트."""
        lang = store.persistent.sub_language
        if lang is None or lang == "None":
            return None
        return lang

    def _lookup(identifier, lang):
        try:
            translator = renpy.game.script.translator
            if lang is None:
                node = translator.default_translates.get(identifier)
            else:
                node = translator.language_translates.get((identifier, lang))

            if node is None:
                return ""
            if hasattr(node, "what"):
                return node.what
            for child in getattr(node, "block", ()):
                if hasattr(child, "what"):
                    return child.what

        except Exception as e:
            renpy.log("dual_text error: {}".format(e))

        return ""

    def get_sub_text():
        identifier = renpy.game.context().translate_identifier
        if not identifier:
            return ""

        lang = wanted_language()

        # 게임이 이미 같은 언어로 보여 주고 있으면 같은 대사가 두 번 나오므로 숨긴다.
        if lang == store._preferences.language:
            return ""

        key = (identifier, lang)
        if key != _Cache.key:
            _Cache.key = key
            _Cache.result = _lookup(identifier, lang)
        return _Cache.result

# ==============================================================================
# 설정창
# ==============================================================================

screen dual_text_icon():
    zorder 100

    imagebutton:
        xalign 0.99
        yalign 0.02

        idle Transform("dual_text_mod/setting_icon.png", alpha=0.5)
        hover Transform("dual_text_mod/setting_icon.png", alpha=1.0)

        action Show("dual_text_settings")


screen dual_text_settings():
    zorder 101
    modal True
    style_prefix "dual_text"
    add Solid("#000000aa")

    frame:
        xalign 0.5
        yalign 0.5
        xpadding 40
        ypadding 25
        background Solid("#0000004c")

        vbox:
            spacing 12

            text "듀얼 텍스트 모드 설정" size 30 bold True xalign 0.5

            # 화면이 작은 게임에서도 제목과 닫기 버튼은 늘 보이도록 본문만 스크롤한다.
            # 게임의 vscrollbar 스타일에 따라 scrollbars 속성을 쓰면 내용이 사라지는 경우가 있어
            # 스크롤바를 직접 붙이고 모드 전용 스타일을 쓴다.
            side "c r":
                spacing 8

                viewport id "dual_text_settings_viewport":
                    xsize min(900, config.screen_width - 120)
                    ymaximum config.screen_height - 170
                    xfill False
                    yfill False
                    mousewheel True

                    vbox:
                        xfill True
                        spacing 15

                        $ current_status = "켜짐" if persistent.show_dual_text else "꺼짐"

                        textbutton "모드 켜기/끄기 (현재: [current_status])":
                            action ToggleVariable("persistent.show_dual_text", True, False)
                            xalign 0.5

                        vbox:
                            spacing 8
                            xalign 0.5
                            text "서브텍스트에 표시할 언어:" size 25 xalign 0.5

                            # 언어가 많아도 화면 밖으로 나가지 않게 줄바꿈한다.
                            hbox:
                                box_wrap True
                                spacing 15
                                xalign 0.5
                                xmaximum min(860, config.screen_width - 160)

                                textbutton "원문":
                                    action SetVariable("persistent.sub_language", "None")
                                    selected (dual_text_mod.wanted_language() is None)
                                for lang in sorted(renpy.known_languages()):
                                    textbutton str(lang).capitalize():
                                        action SetVariable("persistent.sub_language", lang)
                                        selected (persistent.sub_language == lang)

                            text "게임이 지금 보여 주는 언어와 같으면 서브텍스트는 표시되지 않습니다." size 18 color "#BBBBBB" xalign 0.5

                        null height 5

                        hbox:
                            spacing 60
                            xalign 0.5

                            vbox:
                                spacing 20

                                vbox:
                                    spacing 5
                                    if persistent.dual_text_dialogue_line_spacing is None:
                                        text "원본 대사 줄 간격: 게임 기본값" size 20 color "#FFD700"
                                    else:
                                        text "원본 대사 줄 간격: [persistent.dual_text_dialogue_line_spacing]px" size 20 color "#FFD700"
                                    hbox:
                                        spacing 15
                                        textbutton "게임 기본값":
                                            action SetVariable("persistent.dual_text_dialogue_line_spacing", None)
                                            selected (persistent.dual_text_dialogue_line_spacing is None)
                                        textbutton "직접 조절":
                                            action Function(dual_text_mod.start_custom_line_spacing)
                                            selected (persistent.dual_text_dialogue_line_spacing is not None)
                                    if persistent.dual_text_dialogue_line_spacing is not None:
                                        bar value VariableValue("persistent.dual_text_dialogue_line_spacing", range=50, offset=0, step=1) xmaximum 350

                                vbox:
                                    spacing 5
                                    text "서브텍스트 글자 크기: [persistent.dual_text_size]" size 20
                                    bar value VariableValue("persistent.dual_text_size", range=30, offset=10, step=1) xmaximum 350

                                vbox:
                                    spacing 5
                                    text "서브텍스트 줄 간격: [persistent.dual_text_line_spacing]px" size 20
                                    bar value VariableValue("persistent.dual_text_line_spacing", range=110, offset=-10, step=1) xmaximum 350

                                vbox:
                                    spacing 5
                                    text "서브텍스트 투명도: [persistent.dual_text_alpha]%" size 20
                                    bar value VariableValue("persistent.dual_text_alpha", range=90, offset=10, step=10) xmaximum 350

                                vbox:
                                    spacing 5
                                    text "서브텍스트 글자 색상: [persistent.dual_text_color]" size 20
                                    textbutton "색상 고르기":
                                        action Show("dual_text_color_picker_popup")

                            vbox:
                                spacing 20

                                vbox:
                                    spacing 5
                                    text "서브텍스트 박스 상하 위치 (위 <-> 아래)" size 20
                                    bar value VariableValue("persistent.dual_text_yalign", range=1.0, offset=0.0, step=0.05) xmaximum 350

                                vbox:
                                    spacing 5
                                    text "서브텍스트 박스 좌우 시작 위치 (좌 <-> 우)" size 20
                                    bar value VariableValue("persistent.dual_text_xpos", range=1.0, offset=0.0) xmaximum 350

                                vbox:
                                    spacing 5
                                    $ dual_text_width_pct = int(round((persistent.dual_text_width or 0.7) * 100))
                                    text "서브텍스트 박스 너비: 화면의 [dual_text_width_pct]%" size 20
                                    bar value VariableValue("persistent.dual_text_width", range=0.9, offset=0.1, step=0.05) xmaximum 350

                                vbox:
                                    spacing 5
                                    text "서브텍스트 박스 레이어 순서 (대사창 기준):" size 20
                                    hbox:
                                        spacing 15
                                        textbutton "앞으로 (기본)":
                                            action SetVariable("persistent.dual_text_behind", False)
                                            selected (not persistent.dual_text_behind)
                                        textbutton "뒤로 (숨기기)":
                                            action SetVariable("persistent.dual_text_behind", True)
                                            selected persistent.dual_text_behind

                vbar value YScrollValue("dual_text_settings_viewport") style "dual_text_settings_scrollbar"

            textbutton "닫기":
                xalign 0.5
                action [Function(dual_text_mod.apply_line_spacing), Hide("dual_text_settings")]

# ==============================================================================
# 대사 오버레이 (대사창 앞 / 뒤)
# ==============================================================================

transform dual_text_fade(a):
    alpha a

screen dual_text_content():
    $ sub_text = dual_text_mod.get_sub_text()

    if sub_text:
        vbox:
            xpos persistent.dual_text_xpos
            ypos persistent.dual_text_yalign
            yanchor 0.0
            xmaximum dual_text_mod.box_width()
            at dual_text_fade(persistent.dual_text_alpha / 100.0)

            text sub_text:
                font "dual_text_mod/Paperlogy-6SemiBold.ttf"
                size persistent.dual_text_size
                color dual_text_mod.text_color()
                outlines [(2, "#000000", 0, 0)]
                text_align 0.0
                line_spacing persistent.dual_text_line_spacing

screen dual_text_overlay_front():
    zorder 50
    if renpy.get_screen("say") and persistent.show_dual_text and not persistent.dual_text_behind:
        use dual_text_content

screen dual_text_overlay_behind():
    zorder -1
    if renpy.get_screen("say") and persistent.show_dual_text and persistent.dual_text_behind:
        use dual_text_content

init python:
    for _dual_text_screen in ("dual_text_icon", "dual_text_overlay_front", "dual_text_overlay_behind"):
        if _dual_text_screen not in config.overlay_screens:
            config.overlay_screens.append(_dual_text_screen)

# ==============================================================================
# 색상 선택 팝업 (color_picker.rpy)
# ==============================================================================

style dual_text_color_vbar:
    xysize (30, 300)
    base_bar At(Transform("#000", xysize=(30, 300)), dual_text_spectrum(horizontal=False))
    thumb Transform("dual_text_selector_bg", xysize=(30, 10))
    thumb_offset 5

screen dual_text_color_picker_popup():
    zorder 102
    modal True
    style_prefix "dual_text"
    add Solid("#000000cc")

    default picker = DualTextColorPicker(300, 300, persistent.dual_text_color)

    frame:
        xalign 0.5
        yalign 0.5
        padding (30, 30)

        vbox:
            spacing 20
            text "서브텍스트 글자 색상 선택" size 25 bold True xalign 0.5

            hbox:
                spacing 20

                add picker

                vbar value FieldValue(picker, "hue_rotation", 1.0) style "dual_text_color_vbar"

                vbox:
                    spacing 15
                    xsize 150

                    text "미리보기" size 20 xalign 0.5
                    add picker.swatch(xsize=80, ysize=80) xalign 0.5

                    add picker.hexcode() xalign 0.5

                    null height 20

                    textbutton "적용하기":
                        xalign 0.5
                        action [Function(dual_text_mod.apply_color, picker), Hide("dual_text_color_picker_popup")]

                    textbutton "취소":
                        xalign 0.5
                        action Hide("dual_text_color_picker_popup")
