# Xeti's Dual Text Mode
#
# 모드의 함수와 상태는 store.dual_text_mod 네임스페이스에 둔다. 게임 코드와 이름이 겹치지 않고,
# 실행 중에 바뀌는 값은 클래스 속성에 두어 세이브·롤백에 섞이지 않게 한다.
# 설정은 persistent.dual_text_settings 하나(버전 번호가 붙은 dict)에 모은다.
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

init python in dual_text_mod:
    import re
    import store

    # --------------------------------------------------------------------------
    # 설정 (persistent.dual_text_settings)
    # --------------------------------------------------------------------------
    #
    # 위치와 너비는 화면 대비 비율(0.0~1.0)로 저장해 해상도가 다른 게임에서도 같은 자리에 온다.
    # 형식을 바꿀 때는 SETTINGS_VERSION을 올리고 _migrate()에 옮기는 코드를 더한다.

    SETTINGS_VERSION = 1

    DEFAULTS = {
        "enabled": True,                # 모드 켜기/끄기
        "language": None,               # 서브텍스트 언어. None은 원문 스크립트
        "size": 30,                     # 서브텍스트 글자 크기
        "line_spacing": 0,              # 서브텍스트 줄 간격 (직접 지정 모드, 남는 줄)
        "color": "#FFFFFF",             # 서브텍스트 글자 색
        "alpha": 100,                   # 서브텍스트 투명도 (%)
        "behind": False,                # True면 대사창 뒤에 그린다
        "follow": True,                 # True면 원문 줄 사이에 엇갈려 자동 배치
        "gap": 4,                       # 자동 배치에서 서브텍스트 줄 위아래 간격 (px)
        "offset": 0,                    # 자동 배치에서 서브텍스트 줄을 칸 안에서 아래(+)/위(-)로 옮기는 값 (px)
        "xpos": 0.2,                    # 직접 지정: 왼쪽 끝 (화면 너비 대비)
        "ypos": 0.8,                    # 직접 지정: 위쪽 끝 (화면 높이 대비)
        "width": 0.7,                   # 직접 지정: 박스 너비 (화면 너비 대비)
        "dialogue_line_spacing": None,  # 원본 대사 줄 간격. None이면 게임 값 그대로
    }

    def _from_old_keys():
        """설정 묶음 이전 버전이 persistent에 흩어 둔 값을 모은다. 없는 값은 기본값."""
        p = store.persistent
        s = dict(DEFAULTS)

        if p.show_dual_text is not None:
            s["enabled"] = bool(p.show_dual_text)
        if p.sub_language not in (None, "None"):
            s["language"] = p.sub_language

        for key, old in (
                ("size", "dual_text_size"),
                ("line_spacing", "dual_text_line_spacing"),
                ("color", "dual_text_color"),
                ("alpha", "dual_text_alpha"),
                ("behind", "dual_text_behind"),
                ("follow", "dual_text_follow"),
                ("xpos", "dual_text_xpos"),
                ("ypos", "dual_text_yalign"),
                ("dialogue_line_spacing", "dual_text_dialogue_line_spacing")):
            value = getattr(p, old)
            if value is not None:
                s[key] = value

        # 자동 배치의 첫 기본 간격 2px은 글꼴에 따라 서브텍스트가 다음 원문 줄에 붙어 보여 4px로 올렸다.
        if p.dual_text_follow_gap is not None:
            if p.dual_text_follow_gap == 2 and not p.dual_text_follow_gap_v2:
                s["gap"] = 4
            else:
                s["gap"] = p.dual_text_follow_gap

        # 너비는 처음에 픽셀(dual_text_xmaximum)로, 그다음 비율(dual_text_width)로 저장했다.
        if p.dual_text_width is not None:
            s["width"] = p.dual_text_width
        elif p.dual_text_xmaximum is not None:
            s["width"] = p.dual_text_xmaximum / float(store.config.screen_width)
        s["width"] = max(0.1, min(1.0, round(s["width"], 2)))

        return s

    def _migrate():
        p = store.persistent
        s = p.dual_text_settings

        if not isinstance(s, dict) or "version" not in s:
            s = _from_old_keys()
            s["version"] = SETTINGS_VERSION
            p.dual_text_settings = s

        # (다음 버전에서 형식이 바뀌면 여기서 s["version"]을 보고 옮긴다.)

        # 새로 생긴 항목은 기본값으로 채운다.
        for key, value in DEFAULTS.items():
            if key not in s:
                s[key] = value

    # _migrate()는 아래 init 999에서 부른다. 예전 픽셀 너비를 비율로 바꾸려면 게임이 화면 크기
    # (config.screen_width)를 정한 뒤여야 한다. 그 전까지 get()은 기본값을 돌려준다.

    def settings():
        """설정 dict. 화면의 SetDict / DictValue / ToggleDict에 그대로 넘긴다."""
        return store.persistent.dual_text_settings

    def get(key):
        s = store.persistent.dual_text_settings
        if s is None:
            return DEFAULTS[key]
        return s.get(key, DEFAULTS[key])

    def box_width():
        """직접 지정 모드의 박스 너비(px). 화면 오른쪽 끝을 넘지 않게 자른다."""
        width = get("width") or 0.7
        room = 1.0 - (get("xpos") or 0.0)
        return max(1, int(store.config.screen_width * max(0.05, min(width, room))))

    # --------------------------------------------------------------------------
    # 서브텍스트 색상
    # --------------------------------------------------------------------------

    def text_color():
        """저장된 색에서 투명도를 뺀 색. 투명도는 dual_text_fade로 글자와 테두리에 함께 준다."""
        try:
            return store.Color(get("color") or "#FFFFFF").replace_opacity(1.0)
        except Exception:
            return store.Color("#FFFFFF")

    def apply_color(picker):
        settings()["color"] = picker.color.hexcode
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
        target = get("dialogue_line_spacing")
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
        settings()["dialogue_line_spacing"] = max(0, min(50, int(current)))
        renpy.restart_interaction()

    # --------------------------------------------------------------------------
    # 서브텍스트 찾기 (대사가 나가는 순간에 한 번)
    # --------------------------------------------------------------------------
    #
    # 대사가 화면에 나가기 직전(config.say_arguments_callback, 아래 _say_arguments)에 그 대사의
    # 서브텍스트를 찾아 _Line에 저장한다. 오버레이는 _Line만 읽는다.
    #
    # - 번역 블록 안의 대사는 모두 합친다. 번역이 한 대사를 여러 줄로 나눠도 전부 보인다.
    # - extend 대사는 앞 대사의 서브텍스트에 이어 붙인다. 원문도 앞 대사에 이어 붙어 보이기 때문이다.

    class _Line(object):
        serial = 0          # 대사가 나갈 때마다 1씩 는다
        identifier = None   # 지금 대사의 translate identifier
        chain = ()          # 서브텍스트를 이루는 identifier들 (extend로 이어진 대사)
        text = ""           # 지금 대사의 서브텍스트
        extending = False   # extend가 다음 호출에서 진짜 화자로 다시 말하는 중

    # 바로 앞 대사의 chain. extend가 이어 붙일 앞부분이다. 클래스 속성이 아니라 store 변수로 두어
    # Ren'Py가 원문 쪽 _last_say_what과 함께 세이브·롤백하게 한다. 그래서 롤백이나 로드로
    # extend 대사에 바로 돌아와도 앞부분이 맞다.
    last_chain = ()

    def wanted_language():
        """서브텍스트로 보여 줄 언어. None은 원문 스크립트."""
        lang = get("language")
        if lang is None or lang == "None":
            return None
        return lang

    def _translation_identifier():
        ctx = renpy.game.context()
        return ctx.translate_identifier or getattr(ctx, "deferred_translate_identifier", None)

    def _block_text(identifier, lang):
        """번역 블록(또는 원문) 안의 대사를 모두 합친 글."""
        try:
            translator = renpy.game.script.translator
            if lang is None:
                node = translator.default_translates.get(identifier)
            else:
                node = translator.language_translates.get((identifier, lang))
            if node is None:
                return ""
            if hasattr(node, "what"):
                return node.what or ""

            text = ""
            for child in getattr(node, "block", ()):
                what = getattr(child, "what", None)
                if not what:
                    continue
                if not text or getattr(child, "who", None) == "extend":
                    text += what
                else:
                    text += " " + what
            return text

        except Exception as e:
            renpy.log("dual_text error: {}".format(e))
            return ""

    # 대사 진행을 다루는 텍스트 태그. 서브텍스트는 진행과 상관없이 한 번에 보여 주므로 뺀다.
    # {p}는 원문에서 "기다렸다 줄바꿈"이라 빈칸으로 바꾸고, 나머지는 지운다.
    _PACING_TAGS = ("w", "p", "nw", "fast", "done", "clear")
    _TAG_RE = re.compile(r"\{\{|\{[^{}]*\}")

    def clean_tags(text):
        """서브텍스트에서 대사 진행 태그({w}, {p}, {nw}, {fast}, {done}, {clear})를 뺀다.

        그대로 두면 {p}가 줄바꿈이 되어 줄 엇갈림 계산이 어긋나고, {fast}나 {done}은 앞부분을
        숨긴다. 글자 모양 태그({i}, {color} 등)와 이스케이프된 {{ 는 그대로 둔다.
        """
        def replace(match):
            token = match.group(0)
            if token == "{{":
                return token
            name = token[1:-1].split("=", 1)[0].strip()
            if name in _PACING_TAGS:
                return " " if name == "p" else ""
            return token

        text = _TAG_RE.sub(replace, text)
        return re.sub(r" {2,}", " ", text).strip()

    def _compose_line():
        """_Line.chain으로 지금 설정의 서브텍스트를 만든다."""
        lang = wanted_language()
        # 게임이 이미 같은 언어로 보여 주고 있으면 같은 대사가 두 번 나오므로 숨긴다.
        if lang == store._preferences.language:
            return ""
        return clean_tags("".join(_block_text(identifier, lang) for identifier in _Line.chain))

    def _start_line(who):
        """대사가 나가는 순간 불린다. 서브텍스트를 찾아 _Line에 저장한다."""
        global last_chain

        identifier = _translation_identifier()

        if _Line.extending and last_chain and identifier is not None:
            _Line.chain = tuple(last_chain) + (identifier,)
        elif identifier is not None:
            _Line.chain = (identifier,)
        else:
            _Line.chain = ()

        last_chain = _Line.chain
        _Line.extending = False
        _Line.identifier = identifier
        _Line.serial += 1
        _Line.text = _compose_line() if identifier is not None else ""

    def current_sub_text():
        """오버레이가 그릴 서브텍스트. 저장해 둔 대사와 지금 대사가 같을 때만 돌려준다."""
        if not get("enabled") or not _Line.text:
            return ""
        if _Line.identifier != _translation_identifier():
            return ""
        return _Line.text

    # --------------------------------------------------------------------------
    # 서브텍스트 표시
    # --------------------------------------------------------------------------

    def _sub_text_properties():
        return dict(
            style="dual_text_text",
            size=get("size"),
            color=text_color(),
            outlines=[(2, "#000000", 0, 0)],
            text_align=0.0,
        )

    # 자동 위치에서 서브텍스트를 줄 단위로 잘라 옮길 때, 잘린 줄에 이웃 줄이 섞이지 않게 두는 여유.
    _STRIP_SPACING = 8

    def _substitute_without_translation(text):
        """[mc] 같은 변수는 바꾸되 문자열 번역은 하지 않는다.

        Text는 기본으로 그릴 때 문자열 번역표(translate <언어> strings)에서 같은 문장을 찾아
        게임 언어로 바꾼다. 그러면 원문 "Hi!"가 번역표에 있을 때 서브텍스트도 "안녕!"이 되어
        원문과 서브텍스트가 같은 언어로 나온다.
        """
        try:
            return renpy.substitute(text, translate=False)
        except Exception:
            return text

    def sub_text_displayable(sub_text):
        properties = _sub_text_properties()
        if get("follow") and _Interleave.current() is not None:
            properties["line_spacing"] = _STRIP_SPACING
        else:
            properties["line_spacing"] = get("line_spacing")
        return store.Text(_substitute_without_translation(sub_text), substitute=False, **properties)

    # --------------------------------------------------------------------------
    # 원문과 서브텍스트를 한 줄씩 엇갈려 놓기 (자동 위치)
    # --------------------------------------------------------------------------
    #
    # 원문 1줄 / 서브 1줄 / 원문 2줄 / 서브 2줄 … 순서가 되도록, 대사가 화면에 나가기 직전에
    # 그 대사의 원문 줄 간격을 서브텍스트 한 줄 + 간격만큼 넓힌다. 서브텍스트는 한 번 그린 뒤
    # 줄 단위로 잘라 원문 줄 사이에 하나씩 놓고, 원문보다 줄이 많으면 남는 줄은 마지막 서브텍스트
    # 줄 아래에 이어 붙인다. 줄 높이는 같은 스타일로 "A"와 "A\nA"를 그려 재므로 글꼴, 크기,
    # line_leading이 달라도 맞는다.

    class _Interleave(object):
        line = None         # 이 값을 계산한 대사 (_Line.serial)
        layout = None       # {"orig_line_height", "orig_pitch0", "pitch", "sub_line_height", "sub_pitch0"}
        who = None          # 지금 대사의 화자 (줄을 엇갈릴 수 있는 Character일 때만)
        settings = None     # layout을 계산할 때 쓴 설정 값

        @staticmethod
        def current():
            if _Interleave.line is not None and _Interleave.line == _Line.serial:
                return _Interleave.layout
            return None

    def _text_height(text, properties):
        return renpy.render(store.Text(text, substitute=False, **properties), 100000, 100000, 0, 0).height

    def _line_metrics(properties):
        """(한 줄 높이, 줄 간격 0일 때 줄과 줄 사이 피치)."""
        flat = dict(properties)
        flat["line_spacing"] = 0
        one = _text_height("A", flat)
        two = _text_height("A\nA", flat)
        return one, two - one

    def _dialogue_text_properties(who):
        """대사 텍스트에 쓰이는 스타일과 속성 (Character의 what_ 인자)."""
        what_args = dict(getattr(who, "what_args", {}) or {})
        properties = {"style": what_args.pop("style", "say_dialogue")}
        for key in ("size", "font", "line_leading", "line_spacing", "outlines", "bold", "italic", "vertical", "language"):
            if key in what_args:
                properties[key] = what_args[key]
        return properties

    def _base_line_spacing(properties):
        if "line_spacing" in properties:
            return properties["line_spacing"] or 0
        try:
            return getattr(store.style, properties["style"]).line_spacing or 0
        except Exception:
            return store.style.say_dialogue.line_spacing or 0

    def _settings_key():
        """서브텍스트 글과 줄 엇갈림 배치에 영향을 주는 설정. 바뀌면 지금 대사를 다시 맞춘다."""
        return (
            get("follow"), get("enabled"), get("size"), get("gap"), get("dialogue_line_spacing"),
            wanted_language(), store._preferences.language,
        )

    class _LiveMetrics(object):
        """실제로 그려진 원문 텍스트에서 잰 (한 줄 높이, 피치). 스타일 서명별로 기억한다.

        게임이 say 화면 안에서 글자 크기나 테두리를 따로 정하면(예: Eternum의
        size persistent.text_size) 스타일과 Character 인자만으로는 실제 줄 높이를 알 수 없다.
        그래서 원문이 한 번 그려지면 그 텍스트의 스타일로 다시 재고, 다음 대사부터 그 값을 쓴다.
        """
        by_style = {}       # 스타일 서명 → 실제 값
        by_styled = {}      # 스타일로 잰 (한 줄 높이, 피치) → 실제 값

    def _style_signature(properties):
        return repr(sorted((k, repr(v)) for k, v in properties.items()))

    def _widget_metrics(what):
        """화면에 그려진 원문 텍스트 위젯의 스타일로 줄 높이를 잰다."""
        try:
            return _line_metrics({"style": what.style})
        except Exception:
            style = what.style
            properties = {"style": "default"}
            for key in ("font", "size", "bold", "italic", "line_leading", "outlines", "vertical", "language"):
                try:
                    properties[key] = getattr(style, key)
                except Exception:
                    pass
            return _line_metrics(properties)

    def _plan(who):
        """(원문 줄 간격, layout). 줄을 엇갈리지 않을 때는 (원래 줄 간격, None)."""
        orig = _dialogue_text_properties(who)
        base = _base_line_spacing(orig)

        if not (get("follow") and current_sub_text()):
            return base, None

        # 스타일로 잰 값이 같은 다른 화자(예: 나레이션의 say_thought)에서 이미 실제 값을 쟀으면 그것을 쓴다.
        # 게임 화면이 글자 크기를 덮어쓰면 화자가 달라도 실제 줄 높이는 같기 때문이다.
        styled = _line_metrics(orig)
        measured = _LiveMetrics.by_style.get(_style_signature(orig)) or _LiveMetrics.by_styled.get(styled)
        orig_line, orig_pitch0 = measured if measured is not None else styled
        sub_line, sub_pitch0 = _line_metrics(_sub_text_properties())
        # 간격은 서브텍스트 줄 위와 아래에 똑같이 둔다. 게임 원래 줄 간격이 0이어도
        # 서브텍스트가 다음 원문 줄에 붙지 않게 한다.
        extra = sub_line + 2 * (get("gap") or 0)

        return base + extra, {
            # 실제로 그려진 원문으로 확인한 값인지. 아니면 확인할 때까지 서브텍스트를 그리지 않는다.
            "verified": measured is not None,
            "orig_line_height": orig_line,
            "orig_pitch0": orig_pitch0,
            "pitch": orig_pitch0 + base + extra,
            "sub_line_height": sub_line,
            "sub_pitch0": sub_pitch0,
        }

    def _apply_to_say_screen(spacing):
        """화면에 떠 있는 say 화면의 원문 텍스트 줄 간격을 바꾼다. 대사를 다시 실행하지 않는다."""
        screen = renpy.get_screen("say")
        if screen is None:
            return False
        what_properties = screen.widget_properties.get("what")
        if what_properties is None:
            return False
        new_what = dict(what_properties)
        new_what["line_spacing"] = spacing
        widget_properties = dict(screen.widget_properties)
        widget_properties["what"] = new_what
        screen.widget_properties = widget_properties
        return True

    class _PendingMetrics(object):
        """그리는 도중에 잰 원문 줄 높이. 고치는 일은 그리기가 끝난 뒤 periodic 콜백에서 한다."""
        line = None         # 잰 대사 (_Line.serial)
        measured = None     # (한 줄 높이, 피치)

    def check_dialogue_metrics(what):
        """그려진 원문으로 잰 줄 높이가 계산에 쓴 값과 다르면 고칠 값을 맡겨 둔다.

        화면을 그리는 도중(render)에 say 화면 속성을 바꾸고 다시 그리게 하면 Ren'Py가 권하는 순서를
        벗어난다. 여기서는 재기만 하고, 실제로 고치는 일은 apply_pending_metrics()가 한다.
        """
        layout = _Interleave.current()
        if layout is None or _Interleave.who is None:
            return
        try:
            measured = _widget_metrics(what)
        except Exception as e:
            renpy.log("dual_text metrics error: {}".format(e))
            layout["verified"] = True   # 잴 수 없으면 계산한 값으로 그린다.
            return
        if (abs(measured[0] - layout["orig_line_height"]) < 0.5
                and abs(measured[1] - layout["orig_pitch0"]) < 0.5):
            layout["verified"] = True
            return
        _PendingMetrics.line = _Line.serial
        _PendingMetrics.measured = measured

    def apply_pending_metrics():
        """맡겨 둔 원문 줄 높이로 지금 대사를 다시 맞춘다. config.periodic_callbacks에서 불린다."""
        if _PendingMetrics.measured is None:
            return
        line, measured = _PendingMetrics.line, _PendingMetrics.measured
        _PendingMetrics.line = None
        _PendingMetrics.measured = None

        who = _Interleave.who
        if line != _Line.serial or who is None:
            return
        try:
            orig = _dialogue_text_properties(who)
            _LiveMetrics.by_style[_style_signature(orig)] = measured
            _LiveMetrics.by_styled[_line_metrics(orig)] = measured
            spacing, new_layout = _plan(who)
            if new_layout is not None and _apply_to_say_screen(spacing):
                _Interleave.layout = new_layout
                _Interleave.line = _Line.serial
                renpy.restart_interaction()
        except Exception as e:
            renpy.log("dual_text metrics apply error: {}".format(e))

    class _PreviousSayArguments(object):
        callback = None

    LINE_SCREENS = ("dual_text_overlay_front", "dual_text_overlay_behind")

    def _show_line_screens():
        """서브텍스트 화면을 say 화면처럼 임시(transient) 화면으로 띄운다.

        Ren'Py는 say 화면을 임시 화면으로 띄워 대사가 끝나면 바로 내린다. 서브텍스트 화면이
        늘 떠 있으면 다음 장면 전환(with dissolve 등)이 찍는 '이전 화면'에 지난 서브텍스트만 남아,
        원문은 곧바로 사라지는데 서브텍스트는 전환 시간 동안 천천히 사라진다. 같은 순간에 뜨고
        같은 순간에 내려가도록 대사가 나갈 때마다 임시 화면으로 다시 띄운다.
        """
        try:
            for name in LINE_SCREENS:
                # 예전 버전이 늘 떠 있는 화면으로 띄워 세이브에 남은 것도 여기서 바꾼다.
                renpy.hide_screen(name)
                renpy.show_screen(name, _transient=True)
        except Exception as e:
            renpy.log("dual_text screen error: {}".format(e))

    def _say_arguments(who, *args, **kwargs):
        if _PreviousSayArguments.callback is not None:
            args, kwargs = _PreviousSayArguments.callback(who, *args, **kwargs)

        # extend 대사는 먼저 extend 객체로 한 번, 이어서 앞 대사의 화자로 한 번 더 말한다.
        # 첫 호출에서는 표시만 해 두고, 두 번째 호출에서 앞 대사에 이어 붙인다.
        if who is getattr(store, "extend", None):
            _Line.extending = True
            return args, kwargs

        try:
            _start_line(who)
        except Exception as e:
            renpy.log("dual_text line error: {}".format(e))
            _Line.text = ""

        _show_line_screens()

        _Interleave.line = None
        _Interleave.layout = None
        _Interleave.who = None
        _Interleave.settings = _settings_key()
        try:
            # 화자가 문자열이면(예: $ mc = "Orion" 뒤의 mc "...") Ren'Py는 name_only를 바탕으로
            # Character를 만들어 말한다. 줄 높이는 그 바탕 Character의 대사 설정으로 잰다.
            speaker = who
            if isinstance(who, str):
                speaker = getattr(store, "name_only", None)

            if (isinstance(speaker, store.ADVCharacter) and not isinstance(speaker, store.NVLCharacter)
                    and "what_line_spacing" not in kwargs):
                _Interleave.who = speaker
                spacing, layout = _plan(speaker)
                if layout is not None:
                    kwargs["what_line_spacing"] = spacing
                    _Interleave.layout = layout
                    _Interleave.line = _Line.serial
        except Exception as e:
            renpy.log("dual_text interleave error: {}".format(e))
            _Interleave.line = None

        return args, kwargs

    def refresh_line():
        """설정(언어, 글자 크기, 간격, 자동 위치 등)이 바뀌면 지금 떠 있는 대사의 서브텍스트와
        원문 줄 간격을 바로 다시 맞춘다. 인터랙션마다 불리며, 설정이 그대로면 비교 한 번으로 끝난다.

        say 화면이 원문 텍스트에 넘기는 속성(widget_properties["what"])의 줄 간격만 바꾸므로
        대사를 다시 실행하지 않는다.
        """
        key = _settings_key()
        if key == _Interleave.settings:
            return
        _Interleave.settings = key

        if _Line.identifier is None or _Line.identifier != _translation_identifier():
            return

        try:
            _Line.text = _compose_line()
            _Line.serial += 1

            who = _Interleave.who
            if who is None:
                _Interleave.line = None
                return
            spacing, layout = _plan(who)
            if not _apply_to_say_screen(spacing):
                return
            _Interleave.layout = layout
            _Interleave.line = _Line.serial if layout is not None else None
        except Exception as e:
            renpy.log("dual_text refresh error: {}".format(e))

    def manual_rect():
        """직접 지정 모드의 위치와 너비 (x, y, width)."""
        x = int(store.config.screen_width * (get("xpos") or 0.0))
        y = int(store.config.screen_height * (get("ypos") or 0.0))
        return x, y, box_width()

    def _screen_rects(*widgets):
        """마지막으로 그린 화면에서 각 위젯의 (x, y, 너비, 높이)를 찾는다. 못 찾으면 None.

        Ren'Py에는 위젯의 화면 좌표를 알려 주는 공개 API가 없어서, Ren'Py 자체 테스트 도구
        (renpy/test/testfocus.py)처럼 렌더 트리를 따라 내려가며 좌표를 더한다.
        """
        rects = [None] * len(widgets)
        try:
            render_module = renpy.display.render
            root = getattr(render_module, "screen_render", None)
            Render = render_module.Render
            stack = [(root, 0, 0)]
            remaining = len([w for w in widgets if w is not None])
            while stack and remaining:
                r, x, y = stack.pop()
                if not isinstance(r, Render):
                    continue
                for i, widget in enumerate(widgets):
                    if rects[i] is None and widget is not None:
                        for d in r.render_of:
                            if d is widget:
                                rects[i] = (x, y, r.width, r.height)
                                remaining -= 1
                                break
                for child in r.children:
                    stack.append((child[0], x + child[1], y + child[2]))
        except Exception as e:
            renpy.log("dual_text follow error: {}".format(e))
        return rects

    def dialogue_rect():
        """원문 대사 텍스트의 (x, y, 너비, 높이). 서브텍스트 줄바꿈 너비는 대사 영역 기준으로 넓힌다."""
        what = renpy.get_widget("say", "what")
        if what is None:
            return None
        what_rect, window_rect = _screen_rects(what, renpy.get_widget("say", "window"))
        if what_rect is None:
            return None

        x, y, w, h = what_rect
        # 대사 텍스트는 글자가 차지한 만큼만 넓을 수 있다. 대사창 안이면 왼쪽 여백만큼
        # 오른쪽도 비운다고 보고 너비를 넓힌다 (기본 GUI: 268 + 744 + 268 = 1280).
        if window_rect is not None:
            wx, wy, ww, wh = window_rect
            if wx <= x < wx + ww:
                w = max(w, (wx + ww) - x - (x - wx))
        w = min(max(w, 1), store.config.screen_width - x)
        return int(x), int(y), int(w), int(h)

    class _Anchor(object):
        """찾아 둔 원문 위치 (x, 맨 윗줄 y, 너비, 높이).

        대사창 모양(화자 이름표가 있는지)마다 따로 기억한다. 새 대사가 뜬 첫 프레임에는
        원문이 아직 렌더 트리에 없으므로 기억해 둔 위치에 바로 그려, 대사를 넘겨도 서브텍스트가
        움직이지 않게 한다. 원문이 실제로 다른 곳에 그려지면(게임 설정 변경 등) 그 위치로 고친다.
        """
        rects = {}
        screen = None

    def reset_anchor():
        _Anchor.rects = {}
        renpy.restart_interaction()

    def _anchor_key():
        return renpy.get_widget("say", "who") is not None

    def remembered_anchor():
        screen = (store.config.screen_width, store.config.screen_height)
        if _Anchor.screen != screen:
            _Anchor.rects = {}
            _Anchor.screen = screen
        return _Anchor.rects.get(_anchor_key())

    def remember_anchor(found):
        # 너비를 알 수 없는 빈 텍스트 프레임은 기억하지 않는다.
        if found[2] >= 50:
            _Anchor.rects[_anchor_key()] = found

    class FollowDialogue(renpy.Displayable):
        """서브텍스트를 원문 대사에 맞춰 놓는다.

        줄 간격 정보가 있으면 원문 줄 사이에 한 줄씩 엇갈려 놓고, 없으면 원문 아래에 놓는다.
        원문을 못 찾으면 직접 지정 위치에 그린다.
        """

        def __init__(self, child, gap=0, offset=0, **properties):
            super(FollowDialogue, self).__init__(**properties)
            self.child = renpy.displayable(child)
            self.gap = gap
            # 글꼴마다 글자가 줄 칸 안에서 놓이는 위치가 달라, 같은 간격이어도 위아래 여백이
            # 다르게 보일 수 있다. 간격 합은 그대로 두고 서브텍스트만 옮겨 눈으로 맞추게 한다.
            self.offset = offset
            self.misses = 0
            self.found_for = None
            self.found = None

        def _find(self):
            """지금 대사 텍스트의 (x, y, 너비, 높이) (앞 프레임 기준). 아직 그려지지 않았으면 None."""
            what = renpy.get_widget("say", "what")
            if what is None:
                return None
            if self.found_for is what:
                return self.found
            if not "".join(t for t in getattr(what, "text", ()) if isinstance(t, str)):
                return None
            found = dialogue_rect()
            if found is None:
                return None
            self.found_for = what
            self.found = found
            remember_anchor(found)
            check_dialogue_metrics(what)
            return found

        def _render_interleaved(self, rv, cr, x, top, layout, orig_height):
            pitch = layout["pitch"]
            orig_line = layout["orig_line_height"]

            sub_line = layout["sub_line_height"]
            strip_pitch = layout["sub_pitch0"] + _STRIP_SPACING
            sub_lines = max(1, int(round((cr.height - sub_line) / float(strip_pitch))) + 1)
            tight_pitch = layout["sub_pitch0"] + max(0, get("line_spacing") or 0)

            if orig_height is None:
                # 새 대사의 원문은 다음 프레임에야 렌더 트리에 생긴다. 그동안은 원문 줄 수가
                # 서브텍스트 이상이라고 보고 그린다(대부분 그대로 맞다). 다음 프레임에 다시 맞춘다.
                orig_lines = sub_lines
            else:
                # 대사 높이는 버전에 따라 마지막 줄 뒤 줄 간격을 포함하기도 해서 내림으로 센다.
                orig_lines = max(1, int((orig_height - orig_line) / float(pitch) + 1e-6) + 1)

            first = top + orig_line + self.gap + self.offset
            y = first
            for i in range(sub_lines):
                if i < orig_lines:
                    y = first + i * pitch
                else:
                    y += tight_pitch
                src = int(i * strip_pitch)
                strip_height = int(min(sub_line, cr.height - src))
                if strip_height <= 0:
                    break
                rv.blit(cr.subsurface((0, src, int(cr.width), strip_height)), (x, int(y)))

        def render(self, width, height, st, at):
            rv = renpy.Render(width, height)

            # 렌더 트리는 앞 프레임 것이라 새 대사가 뜬 첫 프레임에는 원문이 아직 없다.
            # 그동안은 기억해 둔 위치에 그리고, 다음 프레임에 다시 찾는다.
            found = self._find()
            if found is None:
                self.misses += 1
                if self.misses <= 10:
                    renpy.redraw(self, 0)

            rect = found or remembered_anchor()
            if rect is None:
                if self.misses <= 10:
                    return rv
                # 원문을 못 찾는 게임: 직접 지정 위치에 그리고 가끔 다시 찾아 본다.
                x, y, w = manual_rect()
                cr = renpy.render(self.child, w, height, st, at)
                rv.blit(cr, (x, max(0, min(y, height - cr.height))))
                renpy.redraw(self, 0.2)
                return rv

            x, top, w, h = rect
            cr = renpy.render(self.child, w, height, st, at)
            layout = _Interleave.current()

            if layout is not None and not layout.get("verified", True):
                # 이 스타일의 실제 줄 높이를 아직 모른다. 잘못된 자리에 그렸다가 옮기지 않도록,
                # 원문을 재서 확인하거나 고칠 때까지(보통 1~2프레임) 그리지 않는다.
                self.misses += 1
                if self.misses <= 30:
                    renpy.redraw(self, 0)
                    return rv
                layout["verified"] = True

            if layout is not None:
                self._render_interleaved(rv, cr, x, top, layout, found[3] if found else None)
                return rv

            y = min(top + h + self.gap + self.offset, height - cr.height)
            rv.blit(cr, (x, max(0, y)))
            return rv

        def visit(self):
            return [self.child]

    # --------------------------------------------------------------------------
    # 등록
    # --------------------------------------------------------------------------

    # 톱니바퀴 아이콘만 늘 떠 있는 오버레이 화면이다. 서브텍스트 화면은 대사가 나갈 때
    # _show_line_screens()가 임시 화면으로 띄운다.
    if "dual_text_icon" not in store.config.overlay_screens:
        store.config.overlay_screens.append("dual_text_icon")
    for _screen in LINE_SCREENS:
        while _screen in store.config.overlay_screens:
            store.config.overlay_screens.remove(_screen)

    # 인터랙션마다 확인한다. 값이 같으면 아무것도 하지 않으므로 비용은 비교 한 번이다.
    if apply_line_spacing not in store.config.interact_callbacks:
        store.config.interact_callbacks.append(apply_line_spacing)

    # 그리는 도중에 잰 원문 줄 높이를 그리기가 끝난 뒤 반영한다. 맡겨 둔 값이 없으면 비교 한 번이다.
    if apply_pending_metrics not in store.config.periodic_callbacks:
        store.config.periodic_callbacks.append(apply_pending_metrics)

init 999 python in dual_text_mod:
    _migrate()

    # 게임이 정한 say_arguments_callback이 있으면 먼저 부르고 이어서 처리한다.
    # (게임은 보통 init 0에서 정하므로 그 뒤인 999에서 감싼다)
    if store.config.say_arguments_callback is not _say_arguments:
        _PreviousSayArguments.callback = store.config.say_arguments_callback
        store.config.say_arguments_callback = _say_arguments

    # 원본 줄 간격(apply_line_spacing)을 먼저 맞춘 뒤 서브텍스트와 줄 엇갈림을 다시 맞춘다.
    if refresh_line not in store.config.interact_callbacks:
        store.config.interact_callbacks.append(refresh_line)

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

    $ s = dual_text_mod.settings()

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

                        $ current_status = "켜짐" if s["enabled"] else "꺼짐"

                        textbutton "모드 켜기/끄기 (현재: [current_status])":
                            action ToggleDict(s, "enabled", True, False)
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
                                    action SetDict(s, "language", None)
                                    selected (dual_text_mod.wanted_language() is None)
                                for lang in sorted(renpy.known_languages()):
                                    textbutton str(lang).capitalize():
                                        action SetDict(s, "language", lang)
                                        selected (s["language"] == lang)

                            text "게임이 지금 보여 주는 언어와 같으면 서브텍스트는 표시되지 않습니다." size 18 color "#BBBBBB" xalign 0.5

                        null height 5

                        hbox:
                            spacing 60
                            xalign 0.5

                            vbox:
                                spacing 20

                                vbox:
                                    spacing 5
                                    $ dialogue_line_spacing = s["dialogue_line_spacing"]
                                    if dialogue_line_spacing is None:
                                        text "원본 대사 줄 간격: 게임 기본값" size 20 color "#FFD700"
                                    else:
                                        text "원본 대사 줄 간격: [dialogue_line_spacing]px" size 20 color "#FFD700"
                                    hbox:
                                        spacing 15
                                        textbutton "게임 기본값":
                                            action SetDict(s, "dialogue_line_spacing", None)
                                            selected (dialogue_line_spacing is None)
                                        textbutton "직접 조절":
                                            action Function(dual_text_mod.start_custom_line_spacing)
                                            selected (dialogue_line_spacing is not None)
                                    if dialogue_line_spacing is not None:
                                        bar value DictValue(s, "dialogue_line_spacing", range=50, offset=0, step=1) xmaximum 350

                                vbox:
                                    spacing 5
                                    $ sub_size = s["size"]
                                    text "서브텍스트 글자 크기: [sub_size]" size 20
                                    bar value DictValue(s, "size", range=30, offset=10, step=1) xmaximum 350

                                # 자동 위치에서는 서브텍스트 줄 간격을 원문 줄에 맞추므로 직접 지정일 때만 보인다.
                                if not s["follow"]:
                                    vbox:
                                        spacing 5
                                        $ sub_line_spacing = s["line_spacing"]
                                        text "서브텍스트 줄 간격: [sub_line_spacing]px" size 20
                                        bar value DictValue(s, "line_spacing", range=110, offset=-10, step=1) xmaximum 350

                                vbox:
                                    spacing 5
                                    $ sub_alpha = s["alpha"]
                                    text "서브텍스트 투명도: [sub_alpha]%" size 20
                                    bar value DictValue(s, "alpha", range=90, offset=10, step=10) xmaximum 350

                                vbox:
                                    spacing 5
                                    $ sub_color = s["color"]
                                    text "서브텍스트 글자 색상: [sub_color]" size 20
                                    textbutton "색상 고르기":
                                        action Show("dual_text_color_picker_popup")

                            vbox:
                                spacing 20

                                vbox:
                                    spacing 5
                                    text "서브텍스트 위치:" size 20
                                    hbox:
                                        spacing 15
                                        textbutton "원문 사이 (자동)":
                                            action [SetDict(s, "follow", True), Function(dual_text_mod.reset_anchor)]
                                            selected s["follow"]
                                        textbutton "직접 지정":
                                            action SetDict(s, "follow", False)
                                            selected (not s["follow"])

                                if s["follow"]:
                                    vbox:
                                        spacing 5
                                        $ sub_gap = s["gap"]
                                        text "서브텍스트 줄 위아래 간격: [sub_gap]px" size 20 xmaximum 350
                                        bar value DictValue(s, "gap", range=40, offset=-10, step=1) xmaximum 350
                                        text "원문 한 줄 아래에 서브텍스트 한 줄씩 엇갈려 놓습니다. 글자 크기나 간격을 바꾸면 지금 대사에 바로 맞춥니다." size 16 color "#BBBBBB" xmaximum 350

                                    vbox:
                                        spacing 5
                                        $ sub_offset = s["offset"]
                                        $ sub_offset_label = ("+%d" % sub_offset) if sub_offset > 0 else str(sub_offset)
                                        text "서브텍스트 높이 미세 조정: [sub_offset_label]px" size 20 xmaximum 350
                                        bar value DictValue(s, "offset", range=40, offset=-20, step=1) xmaximum 350
                                        hbox:
                                            spacing 15
                                            text "- 위로 / + 아래로" size 16 color "#BBBBBB"
                                            textbutton "0으로" text_size 16:
                                                action SetDict(s, "offset", 0)

                                    vbox:
                                        spacing 5
                                        textbutton "위치 다시 잡기":
                                            action Function(dual_text_mod.reset_anchor)
                                        text "위치는 처음 찾은 곳에 고정됩니다. 어긋나면 눌러 주세요. 원문을 찾지 못하는 게임에서는 직접 지정 위치에 표시됩니다." size 16 color "#BBBBBB" xmaximum 350

                                else:
                                    vbox:
                                        spacing 5
                                        text "서브텍스트 박스 상하 위치 (위 <-> 아래)" size 20
                                        bar value DictValue(s, "ypos", range=1.0, offset=0.0, step=0.05) xmaximum 350

                                    vbox:
                                        spacing 5
                                        text "서브텍스트 박스 좌우 시작 위치 (좌 <-> 우)" size 20
                                        bar value DictValue(s, "xpos", range=1.0, offset=0.0) xmaximum 350

                                    vbox:
                                        spacing 5
                                        $ width_pct = int(round((s["width"] or 0.7) * 100))
                                        text "서브텍스트 박스 너비: 화면의 [width_pct]%" size 20
                                        bar value DictValue(s, "width", range=0.9, offset=0.1, step=0.05) xmaximum 350

                                vbox:
                                    spacing 5
                                    text "서브텍스트 박스 레이어 순서 (대사창 기준):" size 20
                                    hbox:
                                        spacing 15
                                        textbutton "앞으로 (기본)":
                                            action SetDict(s, "behind", False)
                                            selected (not s["behind"])
                                        textbutton "뒤로 (숨기기)":
                                            action SetDict(s, "behind", True)
                                            selected s["behind"]

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
    $ sub_text = dual_text_mod.current_sub_text()
    $ sub_alpha = dual_text_mod.get("alpha") / 100.0

    if sub_text and dual_text_mod.get("follow"):
        add dual_text_mod.FollowDialogue(dual_text_mod.sub_text_displayable(sub_text), gap=dual_text_mod.get("gap"), offset=dual_text_mod.get("offset")) at dual_text_fade(sub_alpha)

    elif sub_text:
        vbox:
            xpos dual_text_mod.get("xpos")
            ypos dual_text_mod.get("ypos")
            yanchor 0.0
            xmaximum dual_text_mod.box_width()
            at dual_text_fade(sub_alpha)

            add dual_text_mod.sub_text_displayable(sub_text)

screen dual_text_overlay_front():
    zorder 50
    if renpy.get_screen("say") and dual_text_mod.get("enabled") and not dual_text_mod.get("behind"):
        use dual_text_content

screen dual_text_overlay_behind():
    zorder -1
    if renpy.get_screen("say") and dual_text_mod.get("enabled") and dual_text_mod.get("behind"):
        use dual_text_content

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

    default picker = DualTextColorPicker(300, 300, dual_text_mod.get("color"))

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
