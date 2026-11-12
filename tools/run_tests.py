"""Play the test game in tests/project with the mod and check what it shows.

    python tools/run_tests.py --renpy "C:/path/to/renpy.exe" [--renpy another.exe ...]

Each scenario runs in a fresh copy of tests/project with dual_text_mod.rpa (or --rpa) in its game
folder, with sound off. The test driver (tests/project/game/zz_test_driver.rpy) plays the game by
itself and writes a JSON result; this script checks it. The game window opens briefly for each run.
Any Ren'Py 8 SDK or game executable works; run it with every version you support.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT = os.path.join(REPO, "tests", "project")
SAVE_DIRECTORY = "dual-text-mode-tests"

KO = [
    "안녕하세요.",
    "안녕하세요. 오늘 어떠세요?",
    "이 대사는 번역에서 두 줄로 나뉩니다.",
    "문자열 화자가 말합니다, [hero].",
    "기다려 봐. 다음 부분이야.",
    "이 대사는 대사창에서 두 줄로 넘어갈 만큼 길어서, 두 번째 텍스트도 원문 줄 사이에 한 줄씩 엇갈려 들어가야 합니다. 줄이 넘어가는지 확인하려고 조금 더 길게 씁니다.",
    "나레이션이 장면을 닫습니다.",
    "잠시 멈춘 뒤의 대사.",
]

EN = [
    "Hello there.",
    "Hello there. How are you today?",
    "This line is split in the translation.",
    "This line is split in the translation.",
    "A string speaker talks, [hero].",
    "This translation carries pacing tags.",
    "This is a long line that wraps onto a second line of the dialogue box, so the second text has to be interleaved with it line by line.",
    "A narrator line closes the scene.",
    "After the pause.",
]

MIGRATED = {
    "enabled": True, "language": "korean", "size": 24, "line_spacing": 0, "color": "#FFCC00",
    "alpha": 80, "behind": False, "follow": True, "gap": 4, "offset": 0, "xpos": 0.1, "ypos": 0.7,
    "width": 0.75, "dialogue_line_spacing": 12, "version": 1,
}


def near(a, b, tolerance=0.5):
    return abs(a - b) <= tolerance


def check_lines(result, expected, problems):
    lines = result["lines"]
    subs = [line["sub"] for line in lines]
    if subs != expected:
        problems.append("second texts differ:\n      got      %r\n      expected %r" % (subs, expected))

    for line in lines:
        label = "line %d" % line["i"]
        if not line["interleaved"]:
            problems.append("%s: not interleaved with the dialogue" % label)
            continue
        if any(tag in line["sub"] for tag in ("{w", "{p", "{nw", "{fast", "{done", "{clear")):
            problems.append("%s: pacing tag left in the second text: %r" % (label, line["sub"]))

        # The say screen sets the dialogue size itself, so the layout must use the measured height.
        layout, measured = line["layout"], line["measured"]
        if not (isinstance(measured, list) and near(layout["orig_line_height"], measured[0])
                and near(layout["orig_pitch0"], measured[1])):
            problems.append("%s: layout %s does not match the drawn dialogue %s"
                            % (label, (layout["orig_line_height"], layout["orig_pitch0"]), measured))

        strips = line["strips"] or []
        dialogue = line["dialogue"]
        if not strips or not dialogue:
            problems.append("%s: second text or dialogue not found on screen" % label)
            continue
        first_y = dialogue[1] + layout["orig_line_height"] + result["settings_at_start"]["gap"]
        if not near(strips[0][1], first_y, 1):
            problems.append("%s: second text at y=%s, expected %s" % (label, strips[0][1], first_y))

        # A dialogue of several lines: second-text lines follow at the dialogue's line pitch.
        dialogue_lines = int((dialogue[3] - layout["orig_line_height"]) / layout["pitch"] + 1e-6) + 1
        for k in range(1, min(len(strips), dialogue_lines)):
            if not near(strips[k][1] - strips[k - 1][1], layout["pitch"], 1):
                problems.append("%s: second-text line %d is %s below the previous one, expected %s"
                                % (label, k, strips[k][1] - strips[k - 1][1], layout["pitch"]))

    if not any(len(line["strips"] or []) >= 2 for line in lines):
        problems.append("no line was split across dialogue lines; the long line did not wrap")

    # The second text must appear in its final place on the first frame it is drawn, also on the
    # first line and on the first line of a new dialogue style (the narrator uses say_thought).
    places = set((x, y) for i, n, x, y in result["track"])
    if len(places) > 1:
        problems.append("second text moved while advancing: %s" % sorted(places))

    # During the pause the dialogue is gone; the second text must be gone with it.
    if not result["pause"]:
        problems.append("the pause was not observed")
    for state in result["pause"]:
        if state["front"] or state["behind"]:
            problems.append("second-text screen still shown during the pause: %s" % state)
            break


def check_en_ko(result, problems):
    check_lines(result, KO, problems)


def check_ko_en(result, problems):
    check_lines(result, EN, problems)


def check_rollback(result, problems):
    subs = [line["sub"] for line in result["lines"]]
    expected = KO[:3] + [KO[1]]
    if subs != expected:
        problems.append("after rolling back to the extend line:\n      got      %r\n      expected %r" % (subs, expected))


def check_migrate(result, problems):
    if result["settings_at_start"] != MIGRATED:
        problems.append("migrated settings:\n      got      %r\n      expected %r" % (result["settings_at_start"], MIGRATED))
    if not result["lines"] or result["lines"][0]["sub"] != KO[0]:
        problems.append("migrated settings did not show the Korean second text")


def check_live(result, problems):
    stages = result["stages"]
    try:
        line1, shrunk, restored, manual, again = (stages[k] for k in ("line1", "shrunk", "restored", "manual", "auto_again"))
    except KeyError as e:
        problems.append("missing stage %s" % e)
        return
    if shrunk["what_line_spacing"] == line1["what_line_spacing"]:
        problems.append("changing size and gap did not re-fit the dialogue line spacing")
    if not (shrunk["strips"] and restored["strips"]) or shrunk["strips"][0][1] - restored["strips"][0][1] != 2:
        problems.append("gap 6 vs 4 should move the second text by 2px: %s / %s" % (shrunk["strips"], restored["strips"]))
    if restored["what_line_spacing"] != line1["what_line_spacing"]:
        problems.append("restoring the settings did not restore the line spacing")
    if manual["interleaved"] or manual["what_line_spacing"] == line1["what_line_spacing"]:
        problems.append("switching to manual position did not give the dialogue its own line spacing back")
    if again["what_line_spacing"] != line1["what_line_spacing"]:
        problems.append("switching back to automatic did not interleave again")


def check_offset(result, problems):
    stages = result["stages"]
    try:
        y0, y1 = stages["off0"]["strips"][0][1], stages["offm5"]["strips"][0][1]
    except (KeyError, TypeError, IndexError):
        problems.append("offset stages missing: %s" % list(stages))
        return
    if y1 - y0 != -5:
        problems.append("offset -5 moved the second text by %s" % (y1 - y0))
    if stages["off0"]["what_line_spacing"] != stages["offm5"]["what_line_spacing"]:
        problems.append("the height offset must not change the dialogue line spacing")


SCENARIOS = {
    "en_ko": check_en_ko,        # game in English, second text in Korean
    "ko_en": check_ko_en,        # game in Korean, second text from the original script
    "rollback": check_rollback,  # roll back onto an extend line
    "migrate": check_migrate,    # settings saved by older versions
    "live": check_live,          # change size, gap and position mode while a line is shown
    "offset": check_offset,      # fine height adjustment
}


def save_dirs():
    dirs = [os.path.join(os.path.expanduser("~"), ".renpy", SAVE_DIRECTORY),
            os.path.join(os.path.expanduser("~"), "Library", "RenPy", SAVE_DIRECTORY)]
    if os.environ.get("APPDATA"):
        dirs.append(os.path.join(os.environ["APPDATA"], "RenPy", SAVE_DIRECTORY))
    return dirs


def run(exe, rpa_path, scenario, keep):
    workdir = tempfile.mkdtemp(prefix="dual-text-test-")
    project = os.path.join(workdir, "project")
    shutil.copytree(PROJECT, project)
    shutil.copy2(rpa_path, os.path.join(project, "game", "dual_text_mod.rpa"))
    for d in save_dirs():
        shutil.rmtree(d, ignore_errors=True)

    out = os.path.join(workdir, "result.json")
    env = dict(os.environ, SDL_AUDIODRIVER="dummy", DTT_SCENARIO=scenario, DTT_OUT=out)
    try:
        subprocess.run([exe, project], env=env, timeout=180, check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        pass

    problems = []
    for report in ("traceback.txt", "errors.txt"):
        path = os.path.join(project, report)
        if os.path.exists(path):
            with open(path, encoding="utf-8-sig", errors="replace") as f:
                problems.append("Ren'Py %s:\n%s" % (report, f.read()[:2000]))
    if not problems:
        if not os.path.exists(out):
            problems.append("no result (the game did not finish within the time limit)")
        else:
            with open(out, encoding="utf-8") as f:
                result = json.load(f)
            if result.get("timeout"):
                problems.append("the driver gave up waiting for the next line")
            SCENARIOS[scenario](result, problems)

    if keep:
        print("    kept %s" % workdir)
    else:
        shutil.rmtree(workdir, ignore_errors=True)
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--renpy", action="append", required=True, help="Ren'Py executable (repeat for several versions)")
    parser.add_argument("--rpa", default=os.path.join(REPO, "dual_text_mod.rpa"), help="archive to test")
    parser.add_argument("--scenario", action="append", choices=sorted(SCENARIOS), help="run only these scenarios")
    parser.add_argument("--keep", action="store_true", help="keep each run's project folder and result")
    args = parser.parse_args()

    failed = 0
    for exe in args.renpy:
        print(exe)
        for scenario in args.scenario or list(SCENARIOS):
            problems = run(exe, args.rpa, scenario, args.keep)
            print("  %-9s %s" % (scenario, "FAIL" if problems else "ok"))
            for problem in problems:
                print("    - " + problem.replace("\n", "\n      "))
            failed += bool(problems)

    print("%d failed" % failed if failed else "all passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
