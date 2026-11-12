# Test driver for Dual Text Mode. Not part of the mod.
#
# tools/run_tests.py starts the test game once per scenario with these environment variables:
#   DTT_SCENARIO  which scenario to play (see SCENARIOS in tools/run_tests.py)
#   DTT_OUT       where to write the JSON result
# The driver plays the game by itself (dismiss / rollback), records what the mod shows for each
# line, writes the JSON and quits. tools/run_tests.py checks the result.

init -10 python:
    import os

    # "migrate": settings saved by older versions of the mod, before the settings dict existed.
    if os.environ.get("DTT_SCENARIO") == "migrate":
        persistent.dual_text_settings = None
        persistent.show_dual_text = True
        persistent.sub_language = "korean"
        persistent.dual_text_size = 24
        persistent.dual_text_xpos = 0.1
        persistent.dual_text_yalign = 0.7
        persistent.dual_text_xmaximum = 960
        persistent.dual_text_width = None
        persistent.dual_text_color = "#FFCC00"
        persistent.dual_text_alpha = 80
        persistent.dual_text_follow_gap = 2
        persistent.dual_text_follow_gap_v2 = None
        persistent.dual_text_dialogue_line_spacing = 12

init 999 python:
    import os, json

    class _T(object):
        scenario = os.environ.get("DTT_SCENARIO", "en_ko")
        out = os.environ.get("DTT_OUT") or os.path.join(config.basedir, "result.json")
        key = None
        n = 0
        idx = 0
        idle = 0
        stage = 0
        done = False
        res = {"lines": [], "track": [], "pause": [], "stages": {}}

    # Settings changed one after another on the first line, each recorded 15 frames later.
    _T_STAGES = {
        "live": [
            ("line1", {"size": 20, "gap": 6}),
            ("shrunk", {"size": 30, "gap": 4}),
            ("restored", {"follow": False}),
            ("manual", {"follow": True}),
            ("auto_again", None),
        ],
        "offset": [
            ("off0", {"offset": -5}),
            ("offm5", None),
        ],
    }

    _t_settings = dual_text_mod.settings()
    if _T.scenario != "migrate":
        _t_settings.clear()
        _t_settings.update(dual_text_mod.DEFAULTS)
        _t_settings["version"] = dual_text_mod.SETTINGS_VERSION
        if _T.scenario.startswith("ko"):
            _preferences.language = "korean"
            _t_settings["language"] = None
        else:
            _preferences.language = None
            _t_settings["language"] = "korean"
    _T.res["settings_at_start"] = dict(_t_settings)
    _T.res["scenario"] = _T.scenario
    _T.res["version"] = renpy.version_only

    def _t_strips():
        """Where the second text was drawn in the last frame: [(x, y, w, h), ...]."""
        import renpy.display.render as R
        stack = [(R.screen_render, 0, 0)]
        while stack:
            r, x, y = stack.pop()
            if not isinstance(r, R.Render):
                continue
            if any(isinstance(d, dual_text_mod.FollowDialogue) for d in r.render_of):
                return [[x + c[1], y + c[2], c[0].width, c[0].height] for c in r.children]
            for c in r.children:
                stack.append((c[0], x + c[1], y + c[2]))
        return None

    def _t_record():
        what = renpy.get_widget("say", "what")
        try:
            measured = list(dual_text_mod._widget_metrics(what)) if what else None
        except Exception as e:
            measured = "error: %s" % e
        return {
            "i": _T.idx,
            "what": "".join(t for t in what.text if isinstance(t, str)) if what else None,
            "sub": dual_text_mod.current_sub_text(),
            "interleaved": dual_text_mod._Interleave.current() is not None,
            "layout": dual_text_mod._Interleave.current(),
            "measured": measured,
            "what_line_spacing": what.style.line_spacing if what else None,
            "dialogue": dual_text_mod.dialogue_rect(),
            "strips": _t_strips(),
        }

    def _t_finish():
        _T.done = True
        with open(_T.out, "w") as f:
            json.dump(_T.res, f, indent=1, default=str, ensure_ascii=False)
        renpy.quit()

    def _t_periodic():
        if _T.done:
            return

        if not renpy.get_screen("say"):
            # A pause or a transition between lines. The second-text screens must be gone too.
            _T.idle += 1
            if _T.res["lines"] and len(_T.res["pause"]) < 5:
                _T.res["pause"].append({
                    "front": renpy.get_screen("dual_text_overlay_front") is not None,
                    "behind": renpy.get_screen("dual_text_overlay_behind") is not None,
                })
            if _T.idle % 20 == 0:
                renpy.queue_event("dismiss")
            if _T.idle > 400:
                _T.res["timeout"] = True
                _t_finish()
            return
        _T.idle = 0

        what = renpy.get_widget("say", "what")
        text = "".join(t for t in what.text if isinstance(t, str)) if what else ""
        key = (renpy.game.context().translate_identifier, text)
        if key != _T.key:
            _T.key = key
            _T.n = 0
        _T.n += 1

        # Where the second text sits in the first frames of each line (it must not move).
        if _T.n <= 6:
            strips = _t_strips()
            if strips:
                _T.res["track"].append([_T.idx, _T.n, strips[0][0], strips[0][1]])

        stages = _T_STAGES.get(_T.scenario)
        if stages:
            if _T.n == 15 * (_T.stage + 1):
                label, changes = stages[_T.stage]
                _T.res["stages"][label] = _t_record()
                _T.stage += 1
                if changes is None:
                    _t_finish()
                    return
                dual_text_mod.settings().update(changes)
                renpy.restart_interaction()
            return

        if _T.n == 15:
            _T.res["lines"].append(_t_record())
            _T.idx += 1
            if text.startswith("After the pause") or text.startswith("잠시 멈춘"):
                _t_finish()
                return
            if _T.scenario == "rollback" and _T.idx == 3:
                renpy.queue_event("rollback")
                return
            if _T.scenario == "rollback" and _T.idx == 4:
                _t_finish()
                return
            renpy.queue_event("dismiss")
        elif _T.n > 15 and _T.n % 20 == 0:
            # Still the same line: the original waits at {w} or {p}. Click again.
            renpy.queue_event("dismiss")

    config.periodic_callbacks.append(_t_periodic)

label main_menu:
    return
