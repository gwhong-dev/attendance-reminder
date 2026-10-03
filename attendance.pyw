import io
import os
import sys
import datetime
import tkinter as tk

# ===== 설정 =====
AUTO_SHUTDOWN = False   # True로 바꾸면 퇴실 후 PC 자동 종료
DEFAULT_START_TIME = "07:00"  # 입실 알림 시작 기본 시각 (config.txt에 "입실"로 적으면 변경)
DEFAULT_END_TIME = "17:40"    # 퇴실 알림 기본 시각 (config.txt에 "퇴실"로 적으면 변경)

# 사진 파일 경로. 비우면 같은 폴더의 in / out (png, jpg, jpeg, webp) 사용
IN_IMAGE = ""
OUT_IMAGE = ""

# 화면 문구
IN_TEXT = "비콘 출석 눌러요"
IN_BUTTON = "출결 체크 완료"
OUT_TEXT = "퇴실을 꼭 누릅시다"
OUT_BUTTON = "퇴실 체크 후에 여기를 눌러주세요"
DONE_TEXT = "오늘도 고생하셨습니다"

TEXT_COLOR = "white"    # 문구 색 (예: "red", "yellow")
FONT = "맑은 고딕"
# ================


def base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def parse_time(value):
    """'15:00' 형식이면 '15:00' 반환, 아니면 None"""
    try:
        return datetime.datetime.strptime(value, "%H:%M").strftime("%H:%M")
    except ValueError:
        return None


def read_config_text():
    """config.txt 읽기 (UTF-8, UTF-8 BOM, 한글 ANSI 저장 모두 지원)"""
    path = os.path.join(base_dir(), "config.txt")
    for enc in ("utf-8-sig", "cp949"):
        try:
            with open(path, encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    return ""


def get_times():
    """(입실 알림 시작 시각, 퇴실 시각) 반환

    config.txt 쓰는 법 (한 줄에 하나씩)
      15:00          -> 퇴실 15:00 (모든 요일)
      퇴실 15:00     -> 위와 같음
      입실 08:00     -> 입실 알림 08:00 이후부터
      수 15:00       -> 수요일만 퇴실 15:00
      수 입실 09:00  -> 수요일만 입실 알림 09:00 이후부터
      수 퇴실 15:00  -> 수요일만 퇴실 15:00
      # 설명         -> 무시
    """
    days = "월화수목금토일"
    today = days[datetime.datetime.now().weekday()]
    found = {}

    try:
        text = read_config_text()
    except Exception:
        text = ""

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        day = None
        kind = "퇴실"
        if len(parts) == 1:
            value = parts[0]
        elif len(parts) == 2:
            if parts[0] in ("입실", "퇴실"):
                kind, value = parts
            else:
                day, value = parts
        elif len(parts) == 3:
            day, kind, value = parts
        else:
            continue

        if kind not in ("입실", "퇴실"):
            continue
        t = parse_time(value)
        if t is None:
            continue
        if day is None:
            found[("all", kind)] = t
        elif day == today:
            found[("today", kind)] = t

    def pick(kind, default):
        return found.get(("today", kind)) or found.get(("all", kind)) or default

    start = pick("입실", DEFAULT_START_TIME)
    end = pick("퇴실", DEFAULT_END_TIME)
    if start >= end:  # 시간이 말이 안 되면 기본값 사용
        return DEFAULT_START_TIME, DEFAULT_END_TIME
    return start, end


def read_image_data(source, name):
    """저장된 사진 파일 읽기. 없으면 None"""
    source = source.strip().strip('"')

    if source:
        if os.path.isabs(source):
            candidates = [source]
        else:
            candidates = [os.path.join(base_dir(), source)]
    else:
        candidates = [os.path.join(base_dir(), name + ext)
                      for ext in (".png", ".jpg", ".jpeg", ".webp")]

    for path in candidates:
        if os.path.exists(path):
            with open(path, "rb") as f:
                return f.read()
    return None


def load_image(name, max_w, max_h):
    """사진을 비율 유지한 채 max 크기 안에 맞춰 불러오기. 없으면 None"""
    try:
        from PIL import Image, ImageTk
    except ImportError:
        return None

    source = IN_IMAGE if name == "in" else OUT_IMAGE
    data = read_image_data(source, name)
    if not data:
        return None

    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
        scale = min(max_w / img.width, max_h / img.height)
        nw = max(1, int(img.width * scale))
        nh = max(1, int(img.height * scale))
        img = img.resize((nw, nh), Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None


def make_screen(root, text, img_name):
    """전체화면: 위 이미지 / 가운데 문구 / (아래 버튼은 각 함수에서)"""
    win = tk.Toplevel(root)
    win.attributes("-fullscreen", True)
    win.attributes("-topmost", True)
    win.configure(bg="black")

    w = root.winfo_screenwidth()
    h = root.winfo_screenheight()
    canvas = tk.Canvas(win, width=w, height=h, bg="black",
                       highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    photo = load_image(img_name, int(w * 0.5), int(h * 0.42))
    if photo:
        canvas.create_image(w // 2, int(h * 0.28), image=photo,
                            anchor="center")
        canvas.photo = photo  # 사진이 사라지지 않게 붙잡아 둠

    text_id = canvas.create_text(w // 2, int(h * 0.60), text=text,
                                 font=(FONT, 60, "bold"), fill=TEXT_COLOR)
    return win, canvas, text_id, w, h


root = tk.Tk()
root.withdraw()
START, END_TIME = get_times()


def show_in():
    win, canvas, text_id, w, h = make_screen(root, IN_TEXT, "in")

    def done():
        win.destroy()
        root.after(1000, check_time)

    btn = tk.Button(canvas, text=IN_BUTTON, font=(FONT, 24), command=done)
    canvas.create_window(w // 2, int(h * 0.78), window=btn)


def check_time():
    now = datetime.datetime.now().strftime("%H:%M")
    if now >= END_TIME:
        show_out()
    else:
        root.after(1000, check_time)


def show_out():
    win, canvas, text_id, w, h = make_screen(root, OUT_TEXT, "out")

    def done():
        btn.destroy()
        canvas.itemconfig(text_id, text=DONE_TEXT)
        win.after(1000, finish)

    btn = tk.Button(canvas, text=OUT_BUTTON, font=(FONT, 24), command=done)
    canvas.create_window(w // 2, int(h * 0.78), window=btn)


def finish():
    root.destroy()
    if AUTO_SHUTDOWN:
        os.system("shutdown /s /t 0")


now = datetime.datetime.now().strftime("%H:%M")
if START <= now < END_TIME:
    show_in()
    root.mainloop()
