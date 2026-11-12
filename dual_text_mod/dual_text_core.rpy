#Xeti's Dual Text Mode 
style dual_text_text is text:
    font "dual_text_mod/Paperlogy-6SemiBold.ttf"
    
style dual_text_button_text is button_text:
    font "dual_text_mod/Paperlogy-6SemiBold.ttf"

default persistent.show_dual_text = True
default persistent.sub_language = "None"
default persistent.dual_text_size = 30
default persistent.dual_text_yalign = 0.8
default persistent.dual_text_xpos = 0.2
default persistent.dual_text_xmaximum = 1400
default persistent.dual_text_line_spacing = 0
default persistent.dual_text_color = "#FFFFFF"
default persistent.dual_text_alpha = 100
default persistent.dual_text_behind = False
default persistent.original_line_spacing = 0

init python:
    import re
    _previous_line_spacing = None

    def apply_original_line_spacing():
        global _previous_line_spacing
        if persistent.original_line_spacing is not None:
            if _previous_line_spacing != persistent.original_line_spacing:
                style.say_dialogue.line_spacing = persistent.original_line_spacing
                style.rebuild()
                _previous_line_spacing = persistent.original_line_spacing
                
    if apply_original_line_spacing not in config.start_callbacks:
        config.start_callbacks.append(apply_original_line_spacing)
    if apply_original_line_spacing not in config.after_load_callbacks:
        config.after_load_callbacks.append(apply_original_line_spacing)

# --------------------------------------------------------
# 서브 텍스트 추출 
# --------------------------------------------------------
    _dual_text_cache_id = None
    _dual_text_cache_lang = None
    _dual_text_cache_result = ""

    def get_sub_text():
        global _dual_text_cache_id, _dual_text_cache_lang, _dual_text_cache_result

        current_id = renpy.game.context().translate_identifier
        target_lang = persistent.sub_language

        if not current_id:
            return ""

        if current_id == _dual_text_cache_id and target_lang == _dual_text_cache_lang:
            return _dual_text_cache_result

        _dual_text_cache_id = current_id
        _dual_text_cache_lang = target_lang

        try:
            if not target_lang or target_lang == "None":
                target_dict = renpy.game.script.translator.default_translates
                node = target_dict.get(current_id)
            else:
                node = renpy.game.script.translator.language_translates.get((current_id, target_lang))

            if not node:
                _dual_text_cache_result = ""
                return ""

            if hasattr(node, 'what'):
                _dual_text_cache_result = node.what
                return node.what
            elif hasattr(node, 'block'):
                for child in node.block:
                    if hasattr(child, 'what'):
                        _dual_text_cache_result = child.what
                        return child.what

        except Exception as e:
            renpy.log("dual_text error: {}".format(e))
            _dual_text_cache_result = ""
            return ""

        _dual_text_cache_result = ""
        return ""

# ==============================================================================
# 모드 전용 UI 및 설정창 화면
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
        xpadding 50
        ypadding 40
        background Solid("#0000004c")

        vbox:
            spacing 20
            
            text "듀얼 텍스트 모드 설정" size 30 bold True xalign 0.5
            
            null height 10

            vbox:
                spacing 15
                xalign 0.5 

                $ current_status = "켜짐" if persistent.show_dual_text else "꺼짐"

                textbutton "모드 켜기/끄기 (현재: [current_status])":
                    action ToggleVariable("persistent.show_dual_text", True, False)
                    xalign 0.5
                
                vbox:
                    spacing 10
                    text "서브 텍스트에 표시할 언어:" size 25 xalign 0.5
                    
                    hbox:
                        spacing 15
                        xalign 0.5 
                        
                        textbutton "원문":
                            action SetVariable("persistent.sub_language", "None")
                            selected (persistent.sub_language == "None" or persistent.sub_language is None)
                        for lang in renpy.known_languages():
                            textbutton str(lang).capitalize():
                                action SetVariable("persistent.sub_language", lang)
                                selected (persistent.sub_language == lang)

            null height 20

            hbox:
                spacing 60
                xalign 0.5
                
                vbox:
                    spacing 20

                    vbox:
                        spacing 5
                        text "원본 대사 줄 간격: [persistent.original_line_spacing]px" size 20 color "#FFD700"
                        bar value VariableValue("persistent.original_line_spacing", range=50, offset=0, step=1) xmaximum 350

                    vbox:
                        spacing 5
                        text "서브 텍스트 글자 크기: [persistent.dual_text_size]" size 20
                        bar value VariableValue("persistent.dual_text_size", range=30, offset=10, step=1) xmaximum 350

                    vbox:
                        spacing 5
                        text "서브텍스트 줄 간격 조절: [persistent.dual_text_line_spacing]px" size 20
                        bar value VariableValue("persistent.dual_text_line_spacing", range=110, offset=-10, step=1) xmaximum 350

                    vbox:
                        spacing 5
                        text "서브텍스트 글자 투명도: [persistent.dual_text_alpha]%" size 20
                        bar value VariableValue("persistent.dual_text_alpha", range=90, offset=10, step=10) xmaximum 350
                        
                    vbox:
                        spacing 5
                        text "서브텍스트 글자 색상: [persistent.dual_text_color]" size 20
                        textbutton "색상 커스텀 팝업 열기":
                            action Show("dual_text_color_picker_popup")

                vbox:
                    spacing 20
                    
                        
                    vbox:
                        spacing 5
                        text "서브텍스트 박스 상하 위치 조절 (위 <-> 아래)" size 20
                        bar value VariableValue("persistent.dual_text_yalign", range=1.0, offset=0.0, step=0.05) xmaximum 350
                        
                    vbox:
                        spacing 5
                        text "서브텍스트 박스 좌우 시작 위치 조절 (좌 <-> 우)" size 20
                        bar value VariableValue("persistent.dual_text_xpos", range=1.0, offset=0.0) xmaximum 350
                        
                    vbox:
                        spacing 5
                        text "서브텍스트 박스 너비 조절: [persistent.dual_text_xmaximum]px" size 20
                        bar value VariableValue("persistent.dual_text_xmaximum", range=1900, offset=100, step=10) xmaximum 350

                    vbox:
                        spacing 5
                        text "서브텍스트 박스 레이어 순서 (텍스트 박스 기준):" size 20
                        hbox:
                            spacing 15
                            textbutton "앞으로 (기본)":
                                action SetVariable("persistent.dual_text_behind", False)
                                selected (persistent.dual_text_behind == False)
                            textbutton "뒤로 (숨기기)":
                                action SetVariable("persistent.dual_text_behind", True)
                                selected (persistent.dual_text_behind == True)

            
            null height 20
            
            textbutton "저장 및 닫기":
                xalign 0.5
                action [Function(apply_original_line_spacing), Hide("dual_text_settings")]


init python:
    if "dual_text_icon" not in config.overlay_screens:
        config.overlay_screens.append("dual_text_icon")

# ==============================================================================
# 독립형 대사 오버레이
# ==============================================================================

init python:
    if persistent.dual_text_yalign is None:
        persistent.dual_text_yalign = 0.8

# ==============================================================================
# 독립형 대사 오버레이 (레이어 분리형)
# ==============================================================================

screen dual_text_content():
    python:
        sub_text = get_sub_text()
        alpha_hex = format(int(persistent.dual_text_alpha / 100.0 * 255), '02x')
        base_color = persistent.dual_text_color.lstrip('#')
        
        if len(base_color) == 3:
            base_color = ''.join(c*2 for c in base_color)
            
        text_color = "#" + base_color[:6] + alpha_hex

    if sub_text != "":
        vbox:
            xpos persistent.dual_text_xpos
            ypos persistent.dual_text_yalign
            yanchor 0.0 
            xmaximum int(persistent.dual_text_xmaximum)
            
            text sub_text:
                font "dual_text_mod/Paperlogy-6SemiBold.ttf" 
                size persistent.dual_text_size 
                color text_color
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
    if "dual_text_overlay" in config.overlay_screens:
        config.overlay_screens.remove("dual_text_overlay")
        
    if "dual_text_overlay_front" not in config.overlay_screens:
        config.overlay_screens.append("dual_text_overlay_front")
    if "dual_text_overlay_behind" not in config.overlay_screens:
        config.overlay_screens.append("dual_text_overlay_behind")

# ==============================================================================
# 컬러 피커 연동 UI
# ==============================================================================
init python:
    def apply_dual_text_color(picker):
        persistent.dual_text_color = picker.color.hexcode
        renpy.restart_interaction()

style dual_text_color_vbar:
    xysize (30, 300)
    base_bar At(Transform("#000", xysize=(30, 300)), spectrum(horizontal=False))
    thumb Transform("selector_bg", xysize=(30, 10))
    thumb_offset 5

screen dual_text_color_picker_popup():
    zorder 102
    modal True 
    style_prefix "dual_text"
    add Solid("#000000cc")
    
    default picker = ColorPicker(300, 300, persistent.dual_text_color)
    
    frame:
        xalign 0.5
        yalign 0.5
        padding (30, 30)
        
        vbox:
            spacing 20
            text "원문 글자 색상 선택" size 25 bold True xalign 0.5
            
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
                        action [Function(apply_dual_text_color, picker), Hide("dual_text_color_picker_popup")]
                        
                    textbutton "취소":
                        xalign 0.5
                        action Hide("dual_text_color_picker_popup")

