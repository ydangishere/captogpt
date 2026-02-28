import os
import re
import time
import threading
import ctypes
import shutil
import textwrap
import difflib
import hashlib
from collections import deque

from openai import OpenAI
from pywinauto import Desktop


ANSI_RESET = "\033[0m"
ANSI_BLUE = "\033[94m"
ANSI_ORANGE = "\033[38;2;255;196;140m"  # Pastel orange (~20% lighter).
ANSI_YELLOW = "\033[93m"  # Fallback if orange is not supported.
ANSI_SUPPORTED = False
WIDTH_RATIO = 0.7


def _enable_windows_ansi() -> bool:
    if os.name != "nt":
        return True
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)) == 0:
            return False
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        if kernel32.SetConsoleMode(handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING) == 0:
            return False
        return True
    except Exception:
        return False


def colorize(text: str, color_code: str) -> str:
    if not ANSI_SUPPORTED:
        return text
    return f"{color_code}{text}{ANSI_RESET}"


def _set_console_width_ratio(ratio: float = WIDTH_RATIO):
    try:
        cols, lines = shutil.get_terminal_size((120, 30))
        target_cols = max(80, int(cols * ratio))
        target_lines = max(25, lines)
        if os.name == "nt":
            os.system(f"mode con: cols={target_cols} lines={target_lines} >nul")
    except Exception:
        pass


def _format_for_terminal(text: str) -> str:
    cols, _ = shutil.get_terminal_size((120, 30))
    width = max(60, cols - 2)
    out = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line:
            out.append("")
            continue
        wrapped = textwrap.fill(
            line,
            width=width,
            break_long_words=False,
            break_on_hyphens=False,
        )
        out.append(wrapped)
    return "\n".join(out)


class LiveCaptionReader:
    def __init__(self, title_regex: str = r".*Live captions.*|.*Live Caption.*"):
        self.title_regex = title_regex

    def _find_window(self):
        desktop = Desktop(backend="uia")
        for w in desktop.windows():
            title = (w.window_text() or "").strip()
            if re.match(self.title_regex, title, flags=re.IGNORECASE):
                return w
        return None

    def read_text(self) -> str:
        win = self._find_window()
        if not win:
            return ""

        chunks = []
        try:
            for c in win.descendants(control_type="Text"):
                t = (c.window_text() or "").strip()
                if t:
                    chunks.append(t)
        except Exception:
            return ""

        if not chunks:
            return ""

        # Live Captions often renders one sentence across multiple visible lines.
        # Merge the latest 3 fragments to reduce mid-question splitting.
        normalized_chunks = [re.sub(r"\s+", " ", c).strip() for c in chunks if c.strip()]
        if not normalized_chunks:
            return ""
        tail = normalized_chunks[-3:] if len(normalized_chunks) >= 3 else normalized_chunks
        merged = " ".join(tail).strip()
        return merged


class GPTProcessor:
    def __init__(self, model: str = "gpt-4o-mini"):
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is missing.")
        self.client = OpenAI(api_key=api_key)
        self.model = model

    @staticmethod
    def detect_domain(text: str) -> str:
        t = re.sub(r"\s+", " ", text.lower()).strip()
        if not t:
            return "general"

        backend_keywords = (
            "spring",
            "spring boot",
            "microservice",
            "redis",
            "kafka",
            "postgres",
            "mysql",
            "transaction",
            "isolation",
            "deadlock",
            "throughput",
            "latency",
            "api",
            "http",
            "retry",
            "circuit breaker",
            "idempotency",
        )
        frontend_tool_keywords = (
            "webflow",
            "figma",
            "react",
            "css",
            "html",
            "ui",
            "ux",
            "frontend",
            "no-code",
            "nocode",
        )
        ai_meta_keywords = (
            "gpt model",
            "model are you using",
            "which model",
            "your model",
            "openai model",
            "chatgpt",
        )

        if any(k in t for k in backend_keywords):
            return "backend_production"
        if any(k in t for k in frontend_tool_keywords):
            return "frontend_tooling"
        if any(k in t for k in ai_meta_keywords):
            return "ai_meta"
        return "general"

    @staticmethod
    def is_followup(text: str) -> bool:
        lower = re.sub(r"\s+", " ", text.lower()).strip()
        followup_markers = (
            "mentioned above",
            "issue above",
            "that issue",
            "this issue",
            "above",
            "as above",
            "nhu tren",
            "van de tren",
            "y tren",
            "truong hop tren",
            "that one",
            "specific actions",
            "specific action",
            "specific list",
            "to do list",
            "todo list",
            "be more specific",
            "dao sau",
            "cu the hon",
            "chi tiet hon",
            "for this issue",
        )
        return any(m in lower for m in followup_markers)

    def process(self, text: str, recent_context: str = "") -> str:
        normalized = re.sub(r"\s+", " ", text).strip()
        lower = normalized.lower()
        word_count = len([w for w in normalized.split(" ") if w])
        has_question_word = bool(
            re.search(r"\b(how|what|why|when|where|which|can|could|should|would|will)\b", lower)
        )
        contains_question_phrase = bool(
            re.search(
                r"\b(do you|does it|did you|is it|are you|are there|is there|can you|could you|should we|would you|will it|how to|what is|why is|when should|where is)\b",
                lower,
            )
        )
        request_phrases = (
            "i need",
            "please",
            "give me",
            "show me",
            "help me",
            "walk me through",
            "tell me",
            "explain",
        )
        contains_request_phrase = any(p in lower for p in request_phrases)
        contains_action_intent = bool(
            re.search(
                r"\b(explain|compare|difference|pros|cons|steps|approach|design|handle|fix|mitigate|improve|optimize|secure|prevent|example|detail|deeper|specific|alternatives?)\b",
                lower,
            )
        )
        has_question_pattern = (
            " is the " in lower
            or " are the " in lower
            or " are there " in lower
            or " is there " in lower
            or " can i " in lower
            or " should i " in lower
            or " would you " in lower
            or " any other " in lower
            or " besides " in lower
            or " alternatives " in lower
        )
        is_followup = self.is_followup(lower)
        looks_like_followup_fragment = bool(recent_context.strip()) and word_count >= 2 and (
            is_followup
            or contains_action_intent
            or word_count <= 12
            or "alternative" in lower
            or "alternatives" in lower
            or "more" in lower
            or "specific" in lower
        )
        looks_like_question = (
            ("?" in lower)
            or has_question_word
            or contains_question_phrase
            or contains_request_phrase
            or contains_action_intent
            or has_question_pattern
            or is_followup
            or looks_like_followup_fragment
        )

        if not looks_like_question:
            return "Chua thay cau hoi ro rang trong caption moi nhat."

        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ban dong vai Senior Java Backend Engineer co kinh nghiem production thuc te "
                        "(high traffic, concurrency, database, performance). "
                        "Chi tra loi bang tieng Viet. "
                        "Truoc khi tra loi, hay phan loai nhanh cau hoi theo domain. "
                        "Neu cau hoi thuoc Java backend/microservice/database/performance thi ap dung mindset production va checklist backend. "
                        "Neu cau hoi thuoc domain khac (vi du Webflow, frontend tool, no-code, model thong tin, general tech) "
                        "thi KHONG ep checklist Java backend; tra loi truc tiep, dung domain do, ngan gon va dung su that. "
                        "Neu cau hoi ve kha nang he thong/model hien tai, tra loi trung thuc ve gioi han va nhung gi biet chac. "
                        "Tra loi ngan gon, ky thuat, dung trong tam phong van. "
                        "Do dai cau tra loi ngan hon khoang 70% so voi cach tra loi thong thuong. "
                        "Uu tien toi da 2-4 cau ngan hoac 3 bullet points. "
                        "Tra loi theo kieu mo ta bang hinh anh cu the, de hieu, thang vao van de. "
                        "Hoi gi tra loi dung cai do, ngan gon, don gian, de hieu. "
                        "Neu phu hop, mo phong nhanh cau tra loi lien he voi cac thanh phan trong fullstack.png. "
                        "Neu can vi du, chi dua 1 vi du sieu ngan de hinh dung nhanh. "
                        "Khong dinh nghia sach giao khoa, khong ly thuyet chung chung. "
                        "Do uu tien cao nhat la DO CHINH XAC KY THUAT. "
                        "Khong chac thi neu ro gia dinh ngan gon, khong duoc khang dinh sai. "
                        "Neu co nhieu phuong an, chon 1 phuong an chinh va neu dieu kien ap dung. "
                        "Bat buoc neu ro cach lam thuc te trong production va cach trien khai trong Spring Boot. "
                        "Bat buoc neu ro trade-off khi ap dung. "
                        "Mindset production that: uu tien on dinh, scale, va recoverability hon la dap an dep tren ly thuyet. "
                        "Khong de xuat mac dinh giai phap qua nang/qua chat (vi du SERIALIZABLE cho toan bo flow) "
                        "neu khong co ly do bat buoc trong context. "
                        "Khi de xuat giai phap, phai neu cach van hanh thuc te: fallback, retry co gioi han, timeout, "
                        "circuit breaker, idempotency key, va cach theo doi su co. "
                        "Kim chi nam production (luon scan truoc khi tra loi): "
                        "1) Failure path va blast radius, "
                        "2) Resilience (timeout/retry/backoff/circuit breaker/fallback), "
                        "3) Data safety (idempotency/transaction/consistency), "
                        "4) HTTP-error contract ro rang, "
                        "5) Observability (log/trace/metric/alert), "
                        "6) Performance bottleneck, "
                        "7) Scalability, "
                        "8) Security can ban, "
                        "9) Van hanh (rollout/rollback/runbook), "
                        "10) Trade-off va tac dong production. "
                        "Ap dung checklist production theo huong DYNAMIC theo ngu canh cau hoi (chi khi cau hoi thuoc backend/production): "
                        "chon 2-4 muc lien quan nhat de dao sau, khong can bao phu tat ca moi muc moi lan. "
                        "Checklist tham chieu: cascading failure, fallback strategy, observability (log/trace/metric), "
                        "distributed tracing, retry/timeout/circuit breaker, idempotency, consistency du lieu, "
                        "gioi han tai nguyen, security, va van hanh. "
                        "Neu mot muc khong lien quan, bo qua de giu cau tra loi gon va dung trong tam. "
                        "Dynamic theo loai cau hoi: "
                        "neu ve DB/transaction thi uu tien isolation anomaly, locking, consistency; "
                        "neu ve microservice thi uu tien resilience, error boundary, observability; "
                        "neu ve API thi uu tien HTTP contract, backward compatibility, idempotency; "
                        "neu ve performance thi uu tien bottleneck, capacity, cache/queue strategy. "
                        "Neu caption co nhieu y/cau hoi, tach nhanh tung y va tra loi lan luot ngan gon. "
                        "Neu caption moi la cau hoi dao sau cung ngu canh, "
                        "chi tra loi phan dao sau moi them vao, khong lap lai toan bo cau tra loi truoc. "
                        "Khong tra loi cut lon, khong duoc chi ghi 1 dong chung chung. "
                        "Neu lien quan den loi hoac HTTP, phai neu ro mapping status code chuan. "
                        "Khong duoc tron khai niem (vi du idempotency khong thay the transaction isolation anomaly). "
                        "Neu lien quan den hieu nang, phai neu ro bottleneck va rui ro. "
                        "Tat ca tu viet tat phai ghi day du nghia day du trong cau tra loi. "
                        "Tranh giong dieu chung chung; giu van phong de hieu, thuc chien, tu nhien. "
                        "Giu giong dieu senior review thuc chien: noi thang, ro, co lap truong ky thuat. "
                        "Uu tien format ngan linh hoat theo cau hoi: "
                        "'Ket luan thang' -> 'Ly do production' -> 'Trien khai Spring Boot' -> 'Trade-off/Risk'. "
                        "Neu cau hien tai la follow-up (vi du: above/that issue/it), "
                        "bat buoc suy luan dua tren ngu canh gan day truoc khi tra loi. "
                        "Khong dich caption. Khong lap lai cau hoi."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Loai cau hoi: {'follow-up dao sau' if is_followup else 'cau hoi moi/doc lap'}\n"
                        f"Yeu cau dac biet: {'Neu la follow-up thi tra loi phan dao sau moi, checklist hanh dong cu the 5-8 buoc, khong lap lai tong quan.' if is_followup else 'Tra loi ngan gon dung trong tam.'}\n\n"
                        f"Luu y: neu caption la mot manh cau hoi ngan (fragment) nhung co ngu canh, hay suy luan no la follow-up hop le va tra loi truc tiep.\n\n"
                        f"Ngu canh gan day:\n{recent_context if recent_context else '(khong co)'}\n\n"
                        f"Caption moi nhat:\n{normalized}"
                    ),
                },
            ],
        )
        answer = (resp.choices[0].message.content or "").strip()
        if not answer:
            return "Chua the tra loi ro rang. Hay noi ro hon 1 chut de toi tra loi chinh xac."
        return answer


class EnterToggleController:
    def __init__(self):
        self.active = False
        self.last_line = ""
        self.lock = threading.Lock()
        self.last_toggle_time = 0.0
        self.toggle_cooldown_seconds = 0.35
        self.last_send_time = 0.0
        self.min_send_interval_seconds = 0.66
        self.last_caption_signature = ""
        self.last_caption_time = 0.0
        self.duplicate_window_seconds = 6.0
        self.answered_signatures = {}
        self.signature_ttl_seconds = 90.0
        self.pending_caption = ""
        self.pending_updated_at = 0.0
        self.pending_stable_ticks = 0
        self.caption_settle_seconds = 0.41
        self.force_send_after_seconds = 2.2
        self.conditional_force_send_after_seconds = 8.0
        self.hard_force_send_after_seconds = 5.0
        self.universal_settle_seconds = 2.07
        self.universal_stable_ticks = 6
        self.end_markers = ("?", ".", "!")
        self.min_words_before_send = 4
        self.min_words_no_punctuation = 12
        self.trailing_incomplete_words = {
            "and",
            "or",
            "to",
            "for",
            "about",
            "with",
            "of",
            "that",
            "this",
            "a",
            "an",
            "the",
            "i",
            "you",
            "we",
            "they",
            "need",
            "want",
            "please",
            "if",
            "when",
            "after",
            "before",
            "while",
            "because",
            "percent",
            "seconds",
            "minutes",
        }
        self.last_sent_caption_normalized = ""
        self.session_start_baseline = ""
        self.capture_restarted = False
        self.recent_payloads_by_domain = {
            "backend_production": deque(maxlen=3),
            "frontend_tooling": deque(maxlen=3),
            "ai_meta": deque(maxlen=3),
            "general": deque(maxlen=3),
        }
        self.last_non_general_domain = "general"
        self.stopwords = {
            "the", "and", "for", "with", "that", "this", "from", "you", "your", "can", "could",
            "would", "should", "what", "how", "why", "when", "where", "which", "who", "are", "is",
            "to", "of", "in", "on", "a", "an", "it", "do", "does", "did", "please", "give", "me",
            "list", "specific",
        }

    def _caption_signature(self, text: str) -> str:
        # Use a normalized full-text hash to avoid false duplicate blocking.
        t = text.lower().strip()
        t = re.sub(r"\s+", " ", t)
        t = re.sub(r"[^a-z0-9 ]", "", t)
        if not t:
            return ""
        return hashlib.md5(t.encode("utf-8")).hexdigest()

    def _normalize_caption(self, text: str) -> str:
        t = text.lower().strip()
        t = re.sub(r"\s+", " ", t)
        return t

    def _split_caption_units(self, text: str):
        # Split into short sentence/question units so we can drop already-answered parts.
        parts = re.split(r"[?!.]+", text)
        units = []
        for p in parts:
            u = p.strip(" ,;:-")
            if len(u) >= 6:
                units.append(u)
        return units

    def _extract_delta_caption(self, caption: str) -> str:
        current = self._normalize_caption(caption)
        last = self.last_sent_caption_normalized
        if not current:
            return ""

        # After OFF/ON, Live Captions may still show old text.
        # Strip baseline captured at session start before extracting delta.
        baseline = self.session_start_baseline
        if baseline and current.startswith(baseline):
            current = current[len(baseline):].strip(" .,!?:;")
            if not current:
                return ""

        if not last:
            units = self._split_caption_units(current)
            return " ".join(units) if units else current
        if current == last:
            return ""

        # Live captions often prepend old text repeatedly; strip all repeated prefixes.
        while last and current.startswith(last):
            current = current[len(last):].strip(" .,!?:;")
            if not current:
                return ""

        # Only perform aggressive delta extraction when old/new captions are
        # strongly related; otherwise keep full new caption (avoid cutting
        # the beginning of a brand-new context).
        same_context = bool(last) and self._overlap_ratio(current, last) >= 0.40

        # Detect "same context + one extra follow-up" by overlapping tail/head.
        # Keep only the appended tail to avoid replaying the whole previous question.
        if same_context and last and current:
            last_tokens = [t for t in re.split(r"\s+", last) if t]
            current_tokens = [t for t in re.split(r"\s+", current) if t]
            if last_tokens and current_tokens:
                best_overlap = 0
                max_k = min(len(last_tokens), len(current_tokens), 40)
                for k in range(6, max_k + 1):
                    if last_tokens[-k:] == current_tokens[:k]:
                        best_overlap = k
                if best_overlap > 0:
                    tail = " ".join(current_tokens[best_overlap:]).strip(" .,!?:;")
                    if len(tail.split()) >= 2:
                        current = tail

        # Fallback: token-level diff so small edits in old text do not cause full resend.
        if same_context and last and current:
            last_tokens = [t for t in re.split(r"\s+", last) if t]
            current_tokens = [t for t in re.split(r"\s+", current) if t]
            if last_tokens and current_tokens:
                matcher = difflib.SequenceMatcher(a=last_tokens, b=current_tokens)
                delta_tokens = []
                for tag, _, _, j1, j2 in matcher.get_opcodes():
                    if tag in ("insert", "replace"):
                        delta_tokens.extend(current_tokens[j1:j2])
                if delta_tokens:
                    candidate = " ".join(delta_tokens).strip(" .,!?:;")
                    # Use delta when it is meaningful enough to avoid replaying full old caption.
                    if len(candidate.split()) >= 2:
                        current = candidate

        units = self._split_caption_units(current)
        if not units:
            units = [current]

        new_units = []
        for u in units:
            sig = self._caption_signature(u)
            if not sig:
                continue
            if sig in self.answered_signatures:
                continue
            if new_units and self._caption_signature(new_units[-1]) == sig:
                continue
            new_units.append(u)

        return " ".join(new_units).strip()

    def _looks_like_intent(self, text: str) -> bool:
        t = text.lower()
        if "?" in t:
            return True
        if re.search(
            r"\b(do you|does it|did you|is it|are you|can you|could you|should we|would you|will it|how to|what is|why is|when should|where is)\b",
            t,
        ):
            return True
        if any(
            p in t
            for p in (
                "i need",
                "please",
                "give me",
                "show me",
                "help me",
                "walk me through",
                "tell me",
                "explain",
                "mentioned above",
                "that issue",
                "this issue",
                "nhu tren",
                "van de tren",
            )
        ):
            return True
        if re.search(
            r"\b(explain|compare|difference|pros|cons|steps|approach|design|handle|fix|mitigate|improve|optimize|secure|prevent|example|detail|deeper|specific|alternatives?)\b",
            t,
        ):
            return True
        return False

    def _is_caption_complete_enough(self, text: str, stable_for: float, stable_ticks: int) -> bool:
        words = [w for w in re.split(r"\s+", text.strip()) if w]
        if len(words) < self.min_words_before_send:
            return False
        last_word = re.sub(r"[^a-zA-Z]", "", words[-1]).lower()
        lower_text = text.lower().strip()
        has_intent = self._looks_like_intent(text)
        has_question_word = bool(re.search(r"\b(how|what|why|when|where|which|can|could|should|would|will)\b", lower_text))
        overlap_with_last = self._overlap_ratio(lower_text, self.last_sent_caption_normalized) if self.last_sent_caption_normalized else 1.0
        is_new_question_transition = has_question_word and overlap_with_last <= 0.22

        # Never get stuck forever, but only force-send when intent is clear.
        # This avoids splitting long conditional setup into separate captions.
        hard_force_threshold = self.hard_force_send_after_seconds + (2.0 if is_new_question_transition else 0.0)
        if has_intent and stable_for >= hard_force_threshold and len(words) >= 6:
            return True

        # Global debounce for most cases: do not rely on punctuation alone.
        if stable_for < self.universal_settle_seconds or stable_ticks < self.universal_stable_ticks:
            return False

        if text.rstrip().endswith("?"):
            return True
        if text.rstrip().endswith((".", "!")) and has_intent:
            return True

        # For brand-new context questions, avoid cutting mid-question.
        # Require stronger evidence before sending without punctuation.
        if is_new_question_transition:
            if stable_ticks < 6:
                return False
            if len(words) < 14:
                return False
            if last_word in self.trailing_incomplete_words:
                return False
            return has_intent and stable_for >= 3.0

        # Without terminal punctuation, require multiple stable polling ticks
        # to avoid sending during short pauses mid-question.
        min_ticks = 6
        if stable_ticks < min_ticks:
            return False

        ends_with_pause = text.rstrip().endswith((",", ";", ":"))
        missing_intent = not self._looks_like_intent(text)
        looks_incomplete = ends_with_pause or missing_intent

        # Without terminal punctuation, be stricter to avoid splitting one long question into two.
        if len(words) < self.min_words_no_punctuation:
            return False
        if last_word in self.trailing_incomplete_words:
            return False
        if is_new_question_transition and len(words) < 14:
            return False
        if looks_incomplete:
            return stable_for >= self.conditional_force_send_after_seconds
        # No terminal punctuation: only send when clearly intentional and stable longer.
        dynamic_force = max(self.force_send_after_seconds, 3.6) if is_new_question_transition else max(
            self.force_send_after_seconds, 2.6
        )
        return has_intent and stable_for >= dynamic_force

    def on_manual_enter(self):
        with self.lock:
            now = time.time()
            if now - self.last_toggle_time < self.toggle_cooldown_seconds:
                return
            self.last_toggle_time = now

            if not self.active:
                self.active = True
                self.last_line = ""
                self.pending_caption = ""
                self.pending_updated_at = 0.0
                self.last_caption_signature = ""
                self.last_caption_time = 0.0
                self.last_sent_caption_normalized = ""
                self.session_start_baseline = ""
                self.capture_restarted = True
                for bucket in self.recent_payloads_by_domain.values():
                    bucket.clear()
                self.last_non_general_domain = "general"
                print("\n[STATE] CAPTURE STARTED (wait caption done, then send)")
            else:
                self.active = False
                print("\n[STATE] CAPTURE STOPPED")

    def get_recent_context_text(self, domain: str) -> str:
        with self.lock:
            bucket = self.recent_payloads_by_domain.get(domain)
            if not bucket:
                return ""
            return "\n".join(bucket)

    def _token_set(self, text: str):
        words = re.findall(r"[a-z0-9]+", text.lower())
        return {w for w in words if len(w) > 2 and w not in self.stopwords}

    def _overlap_ratio(self, text_a: str, text_b: str) -> float:
        set_a = self._token_set(text_a)
        set_b = self._token_set(text_b)
        if not set_a or not set_b:
            return 0.0
        return len(set_a & set_b) / max(1, len(set_a))

    def resolve_domain_for_request(self, detected_domain: str, is_followup: bool, payload: str) -> str:
        with self.lock:
            if detected_domain != "general":
                return detected_domain
            if is_followup and self.last_non_general_domain != "general":
                bucket = self.recent_payloads_by_domain.get(self.last_non_general_domain)
                recent_context = "\n".join(bucket) if bucket else ""
                overlap = self._overlap_ratio(payload, recent_context)
                if overlap >= 0.18:
                    return self.last_non_general_domain
            return detected_domain

    def remember_exchange(self, payload: str, answer: str, domain: str):
        with self.lock:
            p = re.sub(r"\s+", " ", payload).strip()
            a = re.sub(r"\s+", " ", answer).strip()
            if not p:
                return
            bucket = self.recent_payloads_by_domain.get(domain)
            if bucket is None:
                return
            entry = f"Q: {p}\nA: {a[:500] if a else '(khong co)'}"
            if bucket and bucket[-1] == entry:
                return
            bucket.append(entry)
            if domain != "general":
                self.last_non_general_domain = domain

    def allow_retry_for_payload(self, payload: str):
        # If GPT failed or returned unclear, do not "lose" this caption.
        with self.lock:
            p = re.sub(r"\s+", " ", payload).strip()
            if not p:
                return
            sig = self._caption_signature(p)
            if sig in self.answered_signatures:
                del self.answered_signatures[sig]
            if self.last_caption_signature == sig:
                self.last_caption_signature = ""
            self.pending_caption = p
            self.pending_updated_at = time.time() - self.caption_settle_seconds
            self.last_send_time = 0.0

    def get_payload_if_ready(self, text: str) -> str:
        with self.lock:
            if not self.active or not text:
                return ""
            normalized = re.sub(r"\s+", " ", text).strip()
            if not normalized:
                return ""

            now = time.time()
            # Capture immediate baseline right after OFF/ON so old on-screen caption
            # is never treated as a new question.
            if self.capture_restarted and not self.session_start_baseline:
                self.session_start_baseline = self._normalize_caption(normalized)
                self.capture_restarted = False
                self.last_line = normalized
                self.pending_caption = ""
                self.pending_updated_at = now
                self.pending_stable_ticks = 0
                return ""

            if normalized != self.last_line:
                self.last_line = normalized
                self.pending_caption = normalized
                self.pending_updated_at = now
                self.pending_stable_ticks = 0
                return ""

            if not self.pending_caption:
                return ""
            self.pending_stable_ticks += 1

            stable_for = now - self.pending_updated_at
            if stable_for < self.caption_settle_seconds:
                return ""

            # Avoid sending partial caption while question is still unfolding.
            if not self._is_caption_complete_enough(self.pending_caption, stable_for, self.pending_stable_ticks):
                return ""

            if now - self.last_send_time < self.min_send_interval_seconds:
                return ""

            chosen_caption = self._extract_delta_caption(self.pending_caption)
            if not chosen_caption:
                self.pending_caption = ""
                return ""

            chosen_sig = self._caption_signature(chosen_caption)
            if not chosen_sig:
                return ""
            # Prune old signatures so app does not get stuck on long sessions.
            for sig, ts in list(self.answered_signatures.items()):
                if (now - ts) > self.signature_ttl_seconds:
                    del self.answered_signatures[sig]

            if chosen_sig in self.answered_signatures:
                return ""
            if (
                chosen_sig == self.last_caption_signature
                and (now - self.last_caption_time) < self.duplicate_window_seconds
            ):
                return ""

            self.last_send_time = now
            self.last_caption_signature = chosen_sig
            self.last_caption_time = now
            self.last_sent_caption_normalized = self._normalize_caption(self.pending_caption)
            self.answered_signatures[chosen_sig] = now
            if len(self.answered_signatures) > 250:
                self.answered_signatures.clear()
                self.answered_signatures[chosen_sig] = now
            self.pending_caption = ""
            self.pending_stable_ticks = 0
            return chosen_caption


def main():
    global ANSI_SUPPORTED
    _set_console_width_ratio(WIDTH_RATIO)
    ANSI_SUPPORTED = _enable_windows_ansi()

    reader = LiveCaptionReader()
    gpt = GPTProcessor(model="gpt-4o-mini")
    ctrl = EnterToggleController()

    print("Ready.")
    print("Press Enter to START capture.")
    print("While ON, app waits caption complete, then sends to GPT.")
    print("Press Enter again to STOP sending.")
    print("Press Ctrl+C to exit.\n")

    def input_toggle_loop():
        while True:
            try:
                input()
                ctrl.on_manual_enter()
            except EOFError:
                break
            except Exception as e:
                print(f"\n[WARN] Input error (auto-retry): {e}")
                time.sleep(0.2)

    input_thread = threading.Thread(target=input_toggle_loop, daemon=True)
    input_thread.start()

    try:
        while True:
            try:
                text = reader.read_text()
                payload = ctrl.get_payload_if_ready(text)
                if payload:
                    print(colorize("\n[CAPTION]", ANSI_BLUE))
                    caption_text = payload[:900] + ("..." if len(payload) > 900 else "")
                    print(colorize(_format_for_terminal(caption_text), ANSI_BLUE))

                    try:
                        detected_domain = gpt.detect_domain(payload)
                        is_followup = gpt.is_followup(payload)
                        domain = ctrl.resolve_domain_for_request(detected_domain, is_followup, payload)
                        context_text = ctrl.get_recent_context_text(domain)
                        result = gpt.process(payload, recent_context=context_text)
                        gpt_color = ANSI_ORANGE if ANSI_SUPPORTED else ANSI_YELLOW
                        print(colorize("\n[GPT RESULT]", gpt_color))
                        print(colorize(_format_for_terminal(result), gpt_color))
                        lower_result = result.lower()
                        is_unclear = (
                            "chua thay cau hoi ro rang" in lower_result
                            or "chua the tra loi ro rang" in lower_result
                        )
                        if is_unclear:
                            ctrl.allow_retry_for_payload(payload)
                        else:
                            ctrl.remember_exchange(payload, result, domain)
                    except Exception as e:
                        ctrl.allow_retry_for_payload(payload)
                        print(f"\n[GPT ERROR] {e}")
            except Exception as e:
                print(f"\n[WARN] Runtime read error (auto-retry): {e}")

            time.sleep(0.37)
    except KeyboardInterrupt:
        print("\nExiting...")


if __name__ == "__main__":
    main()
