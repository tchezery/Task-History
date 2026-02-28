from __future__ import annotations
import json
import os
import re
import shutil
import sys
from datetime import date, datetime as dt
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem,
    QFrame, QMessageBox, QDateEdit, QComboBox, QSplitter,
    QStyledItemDelegate, QStyle, QCompleter, QAbstractItemView,
    QCheckBox, QStyleOptionViewItem, QDialog, QProgressBar, QTabWidget,
    QRadioButton, QButtonGroup, QDoubleSpinBox, QGroupBox, QScrollArea,
    QSpacerItem, QSizePolicy, QFileDialog, QPlainTextEdit,
)
from PyQt6.QtCore import QDate, Qt, pyqtSignal, QEvent, QRect, QSize, QStringListModel
from PyQt6.QtGui import QFont, QColor, QFontMetrics, QPen, QBrush, QPainterPath, QPainter, QShortcut, QKeySequence

# ── data ──────────────────────────────────────────────────────────────────────

# all_data: label ("Feb 20") -> (date_obj, persons_list)
all_data: dict[str, tuple[date, list[dict]]] = {}

TRASH_FILE = "trash.txt"
TRASH_DAYS = 7

CONFIG_FILE = "config.json"

# ── config helpers ────────────────────────────────────────────────────────────

_WEEKDAY_NAMES_PT = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
_WEEKDAY_NAMES_SHORT = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]

_DEFAULT_CONFIG = {
    "hours_mode": "per_weekday",          # "none" | "per_weekday"
    "weekday_hours": {
        "seg": 9.0, "ter": 9.0, "qua": 9.0, "qui": 9.0,
        "sex": 8.0, "sab": 0.0, "dom": 0.0,
    },
    "theme": "dark",                      # "dark" | "light"
    "language": "pt",                     # "pt" | "en"
    "bar_person_colors": False,           # colorize bar segments by person
}


def _load_config() -> dict:
    """Carrega configurações de config.json ou retorna defaults."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                cfg = json.load(f)
            # garante que todas as chaves existam
            for k, v in _DEFAULT_CONFIG.items():
                cfg.setdefault(k, v)
            if isinstance(cfg.get("weekday_hours"), dict):
                for wk, wv in _DEFAULT_CONFIG["weekday_hours"].items():
                    cfg["weekday_hours"].setdefault(wk, wv)
            return cfg
        except Exception:
            pass
    return {k: (v.copy() if isinstance(v, dict) else v) for k, v in _DEFAULT_CONFIG.items()}


def _save_config(cfg: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


_config = _load_config()

# ── i18n ──────────────────────────────────────────────────────────────────────

_STRINGS = {
    # ── Geral / Main Window ──
    "app_title":            {"pt": "Daily Tasks",               "en": "Daily Tasks"},
    "tab_register":         {"pt": "Registro",                  "en": "Register"},
    "tab_summary":          {"pt": "Resumo",                    "en": "Summary"},
    "tab_settings":         {"pt": "Configurações",             "en": "Settings"},
    # ── Formulário ──
    "date":                 {"pt": "Data",                      "en": "Date"},
    "today":                {"pt": "Hoje",                      "en": "Today"},
    "requester":            {"pt": "Solicitante",               "en": "Requester"},
    "channel":              {"pt": "Meio",                      "en": "Channel"},
    "ticket_number":        {"pt": "Nº Chamado",                "en": "Ticket #"},
    "ticket_placeholder":   {"pt": "Digite o número do chamado...", "en": "Enter ticket number..."},
    "task":                 {"pt": "Tarefa",                    "en": "Task"},
    "detail":               {"pt": "Detalhe",                   "en": "Detail"},
    "hours":                {"pt": "Horas",                     "en": "Hours"},
    "done":                 {"pt": "Concluída",                 "en": "Done"},
    "add":                  {"pt": "Adicionar",                 "en": "Add"},
    "clear":                {"pt": "Limpar",                    "en": "Clear"},
    "type_placeholder":     {"pt": "Digite {0}...",             "en": "Enter {0}..."},
    # ── Árvore ──
    "tasks_added":          {"pt": "Tarefas adicionadas",       "en": "Added tasks"},
    # ── Resumo ──
    "search":               {"pt": "Pesquisar",                 "en": "Search"},
    "search_placeholder":   {"pt": "Buscar pessoa, tarefa, detalhe…", "en": "Search person, task, detail…"},
    "hours_done":           {"pt": "realizadas",                "en": "completed"},
    "download_txt":         {"pt": "Baixar .txt",               "en": "Download .txt"},
    "download_title":       {"pt": "Salvar cópia do daily.txt", "en": "Save copy of daily.txt"},
    "download_ok":          {"pt": "Arquivo salvo com sucesso.", "en": "File saved successfully."},
    "download_no_data":     {"pt": "Nenhum dado para exportar.", "en": "No data to export."},
    "raw_txt":              {"pt": "Texto bruto",               "en": "Raw text"},
    "visual":               {"pt": "Visual",                    "en": "Visual"},
    # ── Diálogos ──
    "edit":                 {"pt": "Editar",                    "en": "Edit"},
    "save":                 {"pt": "Salvar",                    "en": "Save"},
    "cancel":               {"pt": "Cancelar",                  "en": "Cancel"},
    "attention":             {"pt": "Atenção",                   "en": "Warning"},
    "fill_task":            {"pt": "Preencha a Tarefa.",        "en": "Please fill in the Task."},
    "mark_day_done_title":  {"pt": "Marcar dia como concluído", "en": "Mark day as done"},
    "mark_day_done_msg":    {"pt": "Marcar todas as tarefas e detalhes de {0} como concluídos?",
                             "en": "Mark all tasks and details of {0} as done?"},
    "confirm_delete_title": {"pt": "Confirmar exclusão",        "en": "Confirm deletion"},
    "confirm_delete_msg":   {"pt": "Os seguintes itens serão excluídos:\n\n{0}\n\nDeseja continuar?",
                             "en": "The following items will be deleted:\n\n{0}\n\nDo you want to continue?"},
    "saved_title":          {"pt": "Salvo",                     "en": "Saved"},
    "saved_msg":            {"pt": "Arquivo atualizado: daily.txt", "en": "File updated: daily.txt"},
    "no_tasks":             {"pt": "Nenhuma tarefa para salvar.", "en": "No tasks to save."},
    "myself":               {"pt": "Eu Mesmo",                   "en": "MySelf"},
    # ── Meios (display) ──
    "meio_none":            {"pt": "—",                         "en": "—"},
    "meio_teams":           {"pt": "Teams",                     "en": "Teams"},
    "meio_email":           {"pt": "Email",                     "en": "Email"},
    "meio_whatsapp":        {"pt": "WhatsApp",                  "en": "WhatsApp"},
    "meio_presencial":      {"pt": "Presencial",                "en": "In-Person"},
    "meio_chamado":         {"pt": "Chamado",                   "en": "Ticket"},
    # ── Configurações ──
    "settings_title":       {"pt": "⚙  Configurações de Horas", "en": "⚙  Hours Settings"},
    "settings_desc":        {"pt": "Defina como o sistema calcula a meta de horas diárias.\n"
                                    "Você pode optar por não ter meta e apenas registrar horas,\n"
                                    "ou informar quantas horas para cada dia da semana.",
                             "en": "Define how the system calculates the daily hours target.\n"
                                    "You can choose to have no target and just log hours,\n"
                                    "or set a fixed number of hours for each weekday."},
    "mode_group":           {"pt": "Modo de meta",              "en": "Target mode"},
    "mode_none":            {"pt": "Sem meta — apenas registrar horas realizadas",
                             "en": "No target — just log completed hours"},
    "mode_weekday":         {"pt": "Meta fixa por dia da semana", "en": "Fixed target per weekday"},
    "weekday_group":        {"pt": "Horas por dia da semana",    "en": "Hours per weekday"},
    "save_settings":        {"pt": "💾  Salvar configurações",   "en": "💾  Save settings"},
    "settings_saved_title": {"pt": "Configurações",             "en": "Settings"},
    "settings_saved_msg":   {"pt": "Configurações salvas com sucesso!", "en": "Settings saved successfully!"},
    "language_label":       {"pt": "Idioma",                    "en": "Language"},
    "theme_label":          {"pt": "Tema",                      "en": "Theme"},
    "theme_dark":           {"pt": "Escuro",                    "en": "Dark"},
    "theme_light":          {"pt": "Claro",                     "en": "Light"},
    "bar_person_colors_label": {"pt": "Colorir barra por pessoa",  "en": "Color bar by person"},
    "bar_person_colors_desc":  {"pt": "Cada solicitante recebe uma cor na barra do dia",
                                "en": "Each requester gets a color segment in the day bar"},
    # ── Dias da semana ──
    "mon": {"pt": "Segunda",  "en": "Monday"},
    "tue": {"pt": "Terça",    "en": "Tuesday"},
    "wed": {"pt": "Quarta",   "en": "Wednesday"},
    "thu": {"pt": "Quinta",   "en": "Thursday"},
    "fri": {"pt": "Sexta",    "en": "Friday"},
    "sat": {"pt": "Sábado",   "en": "Saturday"},
    "sun": {"pt": "Domingo",  "en": "Sunday"},
    # ── Ações em pessoa ──
    "person_action_title":  {"pt": "Ação em {0}",               "en": "Action on {0}"},
    "person_action_msg":    {"pt": "O que deseja fazer com {0}?", "en": "What would you like to do with {0}?"},
    "person_mark_done":     {"pt": "Concluir tudo",             "en": "Mark all done"},
    "person_edit":          {"pt": "Editar nome",               "en": "Edit name"},
    "person_add_task":      {"pt": "Nova Tarefa",               "en": "New Task"},
    # ── Ações em tarefa ──
    "task_action_title":    {"pt": "Ação em {0}",               "en": "Action on {0}"},
    "task_action_msg":      {"pt": "O que deseja fazer com a tarefa {0}?", "en": "What would you like to do with task {0}?"},
    "task_mark_done":       {"pt": "Concluir tarefa",           "en": "Mark task done"},
    "task_edit":            {"pt": "Editar tarefa",             "en": "Edit task"},
    "task_add_detail":      {"pt": "Novo Detalhe",              "en": "New Detail"},
    # ── Diálogos de adição ──
    "add_task_title":       {"pt": "Nova Tarefa para {0}",      "en": "New Task for {0}"},
    "add_detail_title":     {"pt": "Novo Detalhe em {0}",       "en": "New Detail in {0}"},
    # ── Botão Eu Mesmo ──
    "myself_btn":           {"pt": "Eu",                        "en": "Me"},
    # ── Hint do formulário ──
    "hint_detail_mode":     {"pt": "↳ detalhe para",            "en": "↳ detail for"},
}

_WEEKDAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

# Mapeamento interno dos meios (chave interna → chave i18n)
_MEIO_INTERNAL = ["—", "Teams", "Email", "WhatsApp", "Presencial", "Chamado"]
_MEIO_I18N_KEY = {
    "—": "meio_none", "Teams": "meio_teams", "Email": "meio_email",
    "WhatsApp": "meio_whatsapp", "Presencial": "meio_presencial", "Chamado": "meio_chamado",
}


def _t(key: str, *args) -> str:
    """Retorna o texto traduzido para o idioma atual."""
    lang = _config.get("language", "pt")
    entry = _STRINGS.get(key, {})
    text = entry.get(lang, entry.get("pt", key))
    if args:
        text = text.format(*args)
    return text


def _meios_display() -> list[str]:
    """Lista de meios traduzidos para exibição."""
    return [_t(_MEIO_I18N_KEY[m]) for m in _MEIO_INTERNAL]


def _meio_display_to_internal(display: str) -> str:
    """Converte meio exibido para chave interna."""
    lang = _config.get("language", "pt")
    for internal, i18n_key in _MEIO_I18N_KEY.items():
        if _STRINGS[i18n_key].get(lang, "") == display:
            return internal
    return display


def _meio_internal_to_display(internal: str) -> str:
    """Converte chave interna para texto exibido."""
    key = _MEIO_I18N_KEY.get(internal, "")
    return _t(key) if key else internal


# Conjunto de todas as variantes de "eu mesmo" para reconhecimento
_MYSELF_NAMES = {v for v in _STRINGS["myself"].values()}


def _is_myself(name: str) -> bool:
    """Verifica se o nome é uma variação do auto-referência (MySelf / Eu Mesmo)."""
    return name in _MYSELF_NAMES


def _rename_myself_all():
    """Renomeia todas as ocorrências de 'myself' nos dados para o idioma atual."""
    target = _t("myself")
    for _lbl, (_, persons) in all_data.items():
        for p in persons:
            if p["person"] in _MYSELF_NAMES:
                p["person"] = target


# roles extras para QTreeWidgetItem
ROLE_HOURS  = Qt.ItemDataRole.UserRole + 1   # float
ROLE_DONE   = Qt.ItemDataRole.UserRole + 2   # bool
ROLE_USED   = Qt.ItemDataRole.UserRole + 3   # float – horas usadas (nó de data)
ROLE_BUDGET = Qt.ItemDataRole.UserRole + 4   # float – orçamento do dia (nó de data)

# ── helpers ───────────────────────────────────────────────────────────────────

MEIOS = _MEIO_INTERNAL   # referência interna (para parsing do .txt)

_MAX_TEXT_LINES = 2   # máximo de linhas visíveis por item na árvore


def _day_budget(d: date) -> float:
    """Retorna orçamento de horas do dia conforme configuração."""
    if _config["hours_mode"] == "none":
        return 0.0
    wk = _WEEKDAY_NAMES_SHORT[d.weekday()]
    return _config["weekday_hours"].get(wk, 0.0)


_MONTH_ABBR_PT = {
    "Jan": "jan", "Feb": "fev", "Mar": "mar", "Apr": "abr",
    "May": "mai", "Jun": "jun", "Jul": "jul", "Aug": "ago",
    "Sep": "set", "Oct": "out", "Nov": "nov", "Dec": "dez",
}


def _display_label(lbl: str) -> str:
    """Retorna o label localizado para exibição na UI (traduz mês se idioma=pt)."""
    if _config.get("language") == "pt" and len(lbl) >= 3:
        month_en = lbl[:3]
        if month_en in _MONTH_ABBR_PT:
            return _MONTH_ABBR_PT[month_en] + lbl[3:]
    return lbl


def _fmt_hhmm(h: float) -> str:
    """Converte horas decimais para HH:MM (ex: 1.5 → 01:30)."""
    total_min = round(h * 60)
    return f"{total_min // 60:02d}:{total_min % 60:02d}"


def _effective_task_hours(task: dict) -> float:
    """Horas efetivas: próprias da tarefa se > 0, senão soma dos detalhes."""
    if task.get("hours"):
        return task["hours"]
    return sum(d.get("hours", 0.0) for d in task.get("details", []))


def _person_hours(person: dict) -> float:
    """Horas acumuladas de uma pessoa (soma de tarefas efetivas)."""
    return sum(_effective_task_hours(t) for t in person.get("tasks", []))


def _date_hours(persons: list) -> float:
    """Total de horas do dia."""
    return sum(_person_hours(p) for p in persons)


# Paleta de cores para os segmentos de pessoas na barra do dia
_PERSON_COLORS = [
    "#3b82f6",  # blue
    "#f97316",  # orange
    "#a855f7",  # purple
    "#ec4899",  # pink
    "#14b8a6",  # teal
    "#eab308",  # yellow
    "#84cc16",  # lime
    "#f43f5e",  # rose
]


class PersonBar(QWidget):
    """Barra de progresso segmentada por pessoa."""

    def __init__(self, segments: list[tuple[float, str]], budget: float, bg_color: str, parent=None):
        """
        segments: lista de (horas, cor_hex) por pessoa
        budget:   meta de horas do dia
        bg_color: cor de fundo (parte não preenchida)
        """
        super().__init__(parent)
        self._segments = segments
        self._budget = budget
        self._bg_color = bg_color
        self.setFixedHeight(6)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, _event):
        if self._budget <= 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        w = self.width()
        h = self.height()
        radius = 3.0

        # Fundo
        painter.setBrush(QBrush(QColor(self._bg_color)))
        bg_path = QPainterPath()
        bg_path.addRoundedRect(0.0, 0.0, float(w), float(h), radius, radius)
        painter.drawPath(bg_path)

        # Segmentos por pessoa (proporcionais ao budget)
        x = 0.0
        total_fill_w = min(sum(h for h, _ in self._segments), self._budget) / self._budget * w
        for seg_hours, seg_color in self._segments:
            if seg_hours <= 0:
                continue
            seg_w = (seg_hours / self._budget) * w
            seg_w = min(seg_w, total_fill_w - x)
            if seg_w <= 0:
                break
            path = QPainterPath()
            if x == 0.0 and x + seg_w >= total_fill_w - 0.5:
                # único segmento: arredonda dos dois lados
                path.addRoundedRect(x, 0.0, seg_w, float(h), radius, radius)
            elif x == 0.0:
                # primeiro: arredonda só à esquerda
                path.addRoundedRect(x, 0.0, seg_w + radius, float(h), radius, radius)
                clip = QPainterPath()
                clip.addRect(x, 0.0, seg_w, float(h))
                path = path.intersected(clip)
            elif x + seg_w >= total_fill_w - 0.5:
                # último: arredonda só à direita
                path.addRoundedRect(x - radius, 0.0, seg_w + radius, float(h), radius, radius)
                clip = QPainterPath()
                clip.addRect(x, 0.0, seg_w, float(h))
                path = path.intersected(clip)
            else:
                path.addRect(x, 0.0, seg_w, float(h))
            painter.setBrush(QBrush(QColor(seg_color)))
            painter.drawPath(path)
            x += seg_w

        painter.end()


def find_or_create_person(persons: list, name: str) -> dict:
    for p in persons:
        if p["person"].lower() == name.lower():
            return p
    entry = {"person": name, "tasks": []}
    persons.append(entry)
    return entry


def _task_via_suffix(task: dict) -> str:
    via     = task.get("via", "")
    chamado = task.get("chamado", "")
    if via == "Chamado" and chamado:
        return f" | Chamado #{chamado}"
    if via:
        return f" | {via}"
    return ""


def format_block(d: date, persons: list) -> str:
    label = d.strftime("%b %d").lstrip("0")
    lines = [f"**========================= **{label}"]
    for person in persons:
        lines.append(f"/ {person['person']}:")
        for task in person["tasks"]:
            suffix = _task_via_suffix(task)
            if task.get("hours"):
                suffix += f" | {task['hours']:g}h"
            if not task.get("done", True):
                suffix += " | pending"
            lines.append(f"- {task['title']}{suffix}:")
            for det in task["details"]:
                dsuffix = ""
                if det.get("hours"):
                    dsuffix += f" | {det['hours']:g}h"
                if not det.get("done", True):
                    dsuffix += " | pending"
                lines.append(f"  - {det['text']}{dsuffix};")
    return "\n".join(lines)


def parse_label_to_date(lbl: str) -> date:
    today = date.today()
    try:
        parsed = dt.strptime(f"{lbl} {today.year}", "%b %d %Y").date()
        if (parsed - today).days > 180:
            parsed = parsed.replace(year=parsed.year - 1)
        return parsed
    except ValueError:
        return today


# ── palettes ──────────────────────────────────────────────────────────────────

PALETTE_DARK = {
    "DARK":     "#0a0a0a",
    "SURFACE":  "#161616",
    "ACCENT":   "#1A1AFF",
    "ACCENT2":  "#1212CC",
    "TEXT":     "#ffffff",
    "MUTED":    "#888888",
    "BORDER":   "#2a2a2a",
    "RED":      "#ff3b30",
    "AMBER":    "#ffcc00",
    "PERSON":   "#6688ff",
    "DATE_DIM": "#444444",
    "ICON":     "Light",
}

PALETTE_LIGHT = {
    "DARK":     "#f2f2f2",
    "SURFACE":  "#ffffff",
    "ACCENT":   "#1A1AFF",
    "ACCENT2":  "#1212CC",
    "TEXT":     "#0a0a0a",
    "MUTED":    "#555555",
    "BORDER":   "#dedede",
    "RED":      "#ff3b30",
    "AMBER":    "#cc8800",
    "PERSON":   "#1A1AFF",
    "DATE_DIM": "#aaaaaa",
    "ICON":     "Dark",
}


def _ss_root(p: dict) -> str:
    return f"""
QWidget {{
    background: {p['DARK']}; color: {p['TEXT']};
    font-family: 'SF Pro Text', 'Helvetica Neue', 'Segoe UI', sans-serif;
    font-size: 10pt;
}}
QLineEdit {{
    background: {p['SURFACE']}; color: {p['TEXT']}; border: 1px solid {p['BORDER']};
    border-radius: 8px; padding: 7px 10px;
    transition: border 0.2s;
}}
QLineEdit:hover {{ border: 1px solid {p['ACCENT']}80; }}
QLineEdit:focus {{ border: 1.5px solid {p['ACCENT']}; }}
QTreeWidget {{
    background: {p['SURFACE']}; border: 1px solid {p['BORDER']};
    border-radius: 10px; outline: none;
}}
QTreeWidget::item {{ padding: 2px 2px; }}
QTreeWidget::item:hover {{ background: {p['ACCENT']}18; border-radius: 5px; }}
QTreeWidget::item:selected {{ background: {p['ACCENT']}; color: white; border-radius: 5px; }}
QDateEdit {{
    background: {p['SURFACE']}; color: {p['TEXT']}; border: 1px solid {p['BORDER']};
    border-radius: 8px; padding: 7px 10px;
}}
QDateEdit:hover {{ border: 1px solid {p['ACCENT']}80; }}
QDateEdit:focus {{ border: 1.5px solid {p['ACCENT']}; }}
QDateEdit::drop-down {{ border: none; width: 20px; }}
QDateEdit::down-arrow {{ image: none; width: 0; }}
QCalendarWidget QWidget {{ background: {p['SURFACE']}; color: {p['TEXT']}; }}
QCalendarWidget QToolButton {{ background: {p['SURFACE']}; color: {p['TEXT']}; border: none; font-weight: 600; }}
QCalendarWidget QToolButton:hover {{ background: {p['ACCENT']}30; border-radius: 4px; }}
QCalendarWidget QAbstractItemView:enabled {{ background: {p['DARK']}; color: {p['TEXT']}; selection-background-color: {p['ACCENT']}; }}
QScrollBar:vertical {{ background: transparent; width: 6px; border-radius: 3px; }}
QScrollBar::handle:vertical {{ background: {p['BORDER']}; border-radius: 3px; min-height: 20px; }}
QScrollBar::handle:vertical:hover {{ background: {p['MUTED']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QComboBox {{
    background: {p['SURFACE']}; color: {p['TEXT']}; border: 1px solid {p['BORDER']};
    border-radius: 8px; padding: 7px 10px;
}}
QComboBox:hover {{ border: 1px solid {p['ACCENT']}80; }}
QComboBox:focus {{ border: 1.5px solid {p['ACCENT']}; }}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
    background: {p['SURFACE']}; color: {p['TEXT']}; border: 1px solid {p['BORDER']};
    border-radius: 8px; selection-background-color: {p['ACCENT']};
}}
QSplitter::handle {{ background: {p['BORDER']}; }}
QCheckBox {{ color: {p['TEXT']}; spacing: 6px; }}
QCheckBox:hover {{ color: {p['ACCENT']}; }}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 1px solid {p['BORDER']}; border-radius: 4px;
    background: {p['SURFACE']};
}}
QCheckBox::indicator:hover {{
    border: 1px solid {p['ACCENT']}80;
}}
QCheckBox::indicator:checked {{
    background: {p['ACCENT']}; border: 1px solid {p['ACCENT']};
}}
QTabWidget::pane {{
    border: 1px solid {p['BORDER']}; border-radius: 10px;
    background: {p['DARK']};
}}
QTabBar::tab {{
    background: {p['SURFACE']}; color: {p['MUTED']};
    padding: 6px 18px; border-radius: 6px; margin-right: 4px; font-weight: 600;
}}
QTabBar::tab:selected {{ background: {p['ACCENT']}; color: white; }}
QTabBar::tab:hover:!selected {{ background: {p['BORDER']}; color: {p['TEXT']}; }}
"""


def _ss_btn(p: dict) -> str:
    return f"""
QPushButton {{
    background: {p['ACCENT']}; color: white; border: none;
    border-radius: 8px; padding: 8px 18px; font-weight: 600; font-size: 10pt;
}}
QPushButton:hover {{ background: {p['ACCENT2']}; }}
QPushButton:pressed {{ background: {p['ACCENT2']}; }}
"""


def _ss_btn_red(p: dict) -> str:
    return f"""
QPushButton {{
    background: {p['RED']}; color: white; border: none;
    border-radius: 8px; padding: 8px 18px; font-weight: 600; font-size: 10pt;
}}
QPushButton:hover {{ background: {p['RED']}cc; }}
"""


def _ss_btn_gray(p: dict) -> str:
    return f"""
QPushButton {{
    background: {p['BORDER']}; color: {p['MUTED']}; border: none;
    border-radius: 8px; padding: 8px 18px; font-weight: 600; font-size: 10pt;
}}
QPushButton:hover {{ background: {p['DATE_DIM']}; color: {p['TEXT']}; }}
"""


def _ss_btn_theme(p: dict) -> str:
    return f"""
QPushButton {{
    background: {p['BORDER']}; color: {p['TEXT']}; border: none;
    border-radius: 6px; padding: 3px 8px; font-size: 14px; font-weight: 600;
}}
QPushButton:hover {{ background: {p['ACCENT']}; color: white; }}
"""


def _ss_label(p: dict) -> str:
    return (f"QLabel {{ color: {p['MUTED']}; font-size: 9pt;"
            f" font-weight: 500; letter-spacing: 0.2px; border: none; }}")


def _ss_card(p: dict) -> str:
    return (f"QFrame {{ background: {p['SURFACE']}; border: 1px solid {p['BORDER']};"
            f" border-radius: 14px; }}")


# ── inline delete + 2-line truncation ─────────────────────────────────────────

ACTION_BTN_W = 56  # px reservado à direita para botões + e ×
DELETE_BTN_W = ACTION_BTN_W  # alias para compatibilidade


class DeleteDelegate(QStyledItemDelegate):
    def __init__(self, tree: "TaskTree"):
        super().__init__(tree)
        self._tree = tree

    @staticmethod
    def _word_wrap(fm: QFontMetrics, text: str, width: int) -> list[str]:
        """Quebra `text` em linhas que cabem em `width` pixels."""
        lines: list[str] = []
        cur = ""
        for word in text.split():
            candidate = (cur + " " + word).strip() if cur else word
            if fm.horizontalAdvance(candidate) <= width:
                cur = candidate
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return lines or [""]

    def _avail_w(self, index) -> int:
        """Largura disponível para texto, descontando indentação do nível do item."""
        item   = self._tree.itemFromIndex(index)
        level  = TaskTree._item_level(item) if item else 0
        indent = self._tree.indentation() * level
        return max(self._tree.viewport().width() - indent - DELETE_BTN_W - 8, 80)

    def sizeHint(self, option, index):
        font    = index.data(Qt.ItemDataRole.FontRole) or option.font
        fm      = QFontMetrics(font)
        lh      = fm.lineSpacing()
        text    = index.data(Qt.ItemDataRole.DisplayRole) or ""
        n       = min(len(self._word_wrap(fm, text, self._avail_w(index))), _MAX_TEXT_LINES)
        pad     = 4 if n <= 1 else 8   # espaçamento auto-ajustável
        return QSize(super().sizeHint(option, index).width(), n * lh + pad)

    def paint(self, painter, option, index):
        # 1. Desenha fundo/seleção sem texto
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.text = ""
        style = opt.widget.style() if opt.widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, opt.widget)

        # 2. Desenha texto com limite de 2 linhas
        font = index.data(Qt.ItemDataRole.FontRole) or option.font
        fg   = index.data(Qt.ItemDataRole.ForegroundRole)
        fm   = QFontMetrics(font)
        lh   = fm.lineSpacing()
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""

        text_x  = option.rect.left() + 4
        avail_w = self._avail_w(index)

        lines = self._word_wrap(fm, text, avail_w)
        if len(lines) > _MAX_TEXT_LINES:
            lines = lines[:_MAX_TEXT_LINES]
            last = lines[-1]
            while last and fm.horizontalAdvance(last + "…") > avail_w:
                last = last[:-1]
            lines[-1] = last + "…"

        total_h = len(lines) * lh
        y0 = option.rect.top() + max(0, (option.rect.height() - total_h) // 2)

        painter.save()
        painter.setFont(font)
        if option.state & QStyle.StateFlag.State_Selected:
            painter.setPen(QColor("white"))
        elif isinstance(fg, QColor):
            painter.setPen(fg)
        for i, line in enumerate(lines):
            painter.drawText(text_x, y0 + i * lh + fm.ascent(), line)
        painter.restore()

        # 2b. Barra de progresso inline para itens de data (nível 0)
        used   = index.data(ROLE_USED)
        budget = index.data(ROLE_BUDGET)
        if used is not None and budget is not None:
            from PyQt6.QtGui import QPen as _P  # noqa – já importado no topo
            pct = min(used / budget, 1.0) if budget > 0 else 0.0
            # cores da barra
            if pct >= 1.0:
                bar_color = QColor("#22c55e")
            elif pct >= 0.8:
                bar_color = QColor("#ccaa00")
            else:
                bar_color = QColor(self._tree.palette().color(
                    self._tree.foregroundRole())) if not fg else QColor("#3b82f6")

            # posiciona após o texto da data
            text_end_x = text_x + fm.horizontalAdvance(text) + 10
            bar_h  = 5
            bar_y  = option.rect.top() + (option.rect.height() - bar_h) // 2
            bar_max_w = max(avail_w - fm.horizontalAdvance(text) - 80, 40)

            hours_str = f"{_fmt_hhmm(used)} / {_fmt_hhmm(budget)}"
            hours_w   = fm.horizontalAdvance(hours_str) + 8
            bar_w     = max(bar_max_w - hours_w, 30)

            # fundo da barra
            painter.save()
            painter.setRenderHint(painter.RenderHint.Antialiasing)
            painter.setPen(Qt.PenStyle.NoPen)
            bg_path = QPainterPath()
            bg_path.addRoundedRect(float(text_end_x), float(bar_y),
                                   float(bar_w), float(bar_h), 2.5, 2.5)
            _pal = PALETTE_LIGHT if _config.get("theme") == "light" else PALETTE_DARK
            painter.setBrush(QBrush(QColor(_pal["BORDER"])))
            painter.drawPath(bg_path)

            # preenchimento da barra
            fill_w = max(int(bar_w * pct), 0)
            if fill_w > 0:
                fill_path = QPainterPath()
                fill_path.addRoundedRect(float(text_end_x), float(bar_y),
                                         float(fill_w), float(bar_h), 2.5, 2.5)
                painter.setBrush(QBrush(bar_color))
                painter.drawPath(fill_path)
            painter.restore()

            # texto de horas após a barra
            painter.save()
            small_font = QFont(font)
            small_font.setPointSize(max(font.pointSize() - 1, 7))
            painter.setFont(small_font)
            if option.state & QStyle.StateFlag.State_Selected:
                painter.setPen(QColor("white"))
            elif isinstance(fg, QColor):
                painter.setPen(fg)
            hours_x = text_end_x + bar_w + 6
            painter.drawText(int(hours_x), y0 + fm.ascent(), hours_str)
            painter.restore()

        # 3. Botões de ação inline: + (adicionar) e × (excluir) em hover / seleção / foco
        item        = self._tree.itemFromIndex(index)
        is_selected = bool(option.state & QStyle.StateFlag.State_Selected)
        is_hovered  = item is not None and item is getattr(self._tree, '_hovered_item', None)
        is_focused  = (item is not None
                       and item is self._tree.currentItem()
                       and self._tree.hasFocus())
        if is_selected or is_hovered or is_focused:
            vp_w  = self._tree.viewport().width()
            level = TaskTree._item_level(item) if item else 0
            half  = ACTION_BTN_W // 2

            # Botão + (somente para pessoa e tarefa — nível 1 e 2)
            show_add = level in (1, 2)
            if show_add:
                add_rect = QRect(vp_w - ACTION_BTN_W, option.rect.top(),
                                 half, option.rect.height())
                painter.save()
                painter.setPen(QColor("#ffffff" if is_selected else "#22c55e"))
                f = QFont("Segoe UI", 14, QFont.Weight.Bold)
                painter.setFont(f)
                painter.drawText(add_rect, Qt.AlignmentFlag.AlignCenter, "+")
                painter.restore()

            # Botão × (sempre visível)
            del_x = vp_w - half if show_add else vp_w - ACTION_BTN_W
            del_w = half if show_add else ACTION_BTN_W
            btn_rect = QRect(del_x, option.rect.top(), del_w, option.rect.height())
            painter.save()
            painter.setPen(QColor("#ffffff" if is_selected else "#ef4444"))
            f = QFont("Segoe UI", 13, QFont.Weight.Bold)
            painter.setFont(f)
            painter.drawText(btn_rect, Qt.AlignmentFlag.AlignCenter, "×")
            painter.restore()


class TaskTree(QTreeWidget):
    delete_requested = pyqtSignal(QTreeWidgetItem)
    add_requested    = pyqtSignal(QTreeWidgetItem)       # + inline → adicionar sub-item
    sync_requested   = pyqtSignal()                      # drag-drop → reconstruir all_data
    move_requested   = pyqtSignal(QTreeWidgetItem, int)  # Ctrl+↑↓ → item, direção

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.viewport().installEventFilter(self)
        self._hovered_item = None
        self._drag_level   = -1
        self._last_vp_w    = 0
        self.currentItemChanged.connect(lambda *_: self.viewport().update())
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        vp_w = self.viewport().width()
        if vp_w != self._last_vp_w:
            self._last_vp_w = vp_w
            self.scheduleDelayedItemsLayout()

    @staticmethod
    def _item_level(item: QTreeWidgetItem) -> int:
        level, p = 0, item.parent()
        while p:
            level += 1
            p = p.parent()
        return level

    def startDrag(self, actions):
        item = self.currentItem()
        if item is None or item.parent() is None:
            return  # nós de data não são arrastáveis
        self._drag_level = self._item_level(item)
        super().startDrag(actions)

    def dragMoveEvent(self, event):
        target = self.itemAt(event.position().toPoint())
        indicator = self.dropIndicatorPosition()
        OnItem = QAbstractItemView.DropIndicatorPosition.OnItem
        if target is None or indicator == OnItem:
            event.ignore()
            return
        if self._item_level(target) != self._drag_level:
            event.ignore()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        super().dropEvent(event)
        self.sync_requested.emit()

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            item = self.currentItem()
            if item and event.key() == Qt.Key.Key_Up:
                self.move_requested.emit(item, -1)
                return
            if item and event.key() == Qt.Key.Key_Down:
                self.move_requested.emit(item, 1)
                return
        super().keyPressEvent(event)

    def eventFilter(self, obj, event):
        if obj is self.viewport():
            t = event.type()
            if t == QEvent.Type.MouseMove:
                item = self.itemAt(event.pos())
                if item is not self._hovered_item:
                    self._hovered_item = item
                    self.viewport().update()
            elif t == QEvent.Type.Leave:
                if self._hovered_item is not None:
                    self._hovered_item = None
                    self.viewport().update()
            elif t == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    pos  = event.pos()
                    item = self.itemAt(pos)
                    if item and pos.x() >= self.viewport().width() - ACTION_BTN_W:
                        level = self._item_level(item)
                        half  = ACTION_BTN_W // 2
                        show_add = level in (1, 2)
                        if show_add and pos.x() < self.viewport().width() - half:
                            # Clicou no botão + (metade esquerda)
                            self.add_requested.emit(item)
                        else:
                            # Clicou no botão × (metade direita, ou item sem +)
                            self.delete_requested.emit(item)
                        return True
        return super().eventFilter(obj, event)


# ── modal de edição ───────────────────────────────────────────────────────────

class EditDialog(QDialog):
    """Modal para editar um item existente (pessoa / tarefa / detalhe)."""

    def __init__(self, parent: QWidget, palette: dict, mode: str, values: dict):
        super().__init__(parent)
        self.setWindowTitle(_t("edit"))
        self.setMinimumWidth(380)
        self.setStyleSheet(_ss_root(palette))
        self._palette = palette
        self._mode = mode

        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.setContentsMargins(20, 20, 20, 20)

        self._fields: dict[str, QLineEdit] = {}

        if mode == "person":
            self._add_line(lay, _t("requester"), "person", values.get("person", ""))

        elif mode == "task":
            self._add_line(lay, _t("task"), "title", values.get("title", ""))

            lbl_meio = QLabel(_t("channel"))
            lbl_meio.setStyleSheet(_ss_label(palette))
            lay.addWidget(lbl_meio)
            self._combo_meio = QComboBox()
            self._combo_meio.addItems(_meios_display())
            # Converte valor interno para display
            display_via = _meio_internal_to_display(values.get("via", ""))
            idx = self._combo_meio.findText(display_via)
            self._combo_meio.setCurrentIndex(max(idx, 0))
            lay.addWidget(self._combo_meio)

            self._lbl_chamado   = QLabel(_t("ticket_number"))
            self._lbl_chamado.setStyleSheet(_ss_label(palette))
            self._entry_chamado = QLineEdit()
            self._entry_chamado.setText(values.get("chamado", ""))
            lay.addWidget(self._lbl_chamado)
            lay.addWidget(self._entry_chamado)
            via_init = values.get("via", "")
            self._lbl_chamado.setVisible(via_init == "Chamado")
            self._entry_chamado.setVisible(via_init == "Chamado")
            self._combo_meio.currentTextChanged.connect(self._on_meio_changed)

            self._add_line(lay, _t("hours"), "hours", values.get("hours_str", ""))
            self._check_done = QCheckBox(_t("done"))
            self._check_done.setChecked(values.get("done", False))
            lay.addWidget(self._check_done)

        elif mode == "detail":
            self._add_line(lay, _t("detail"), "text", values.get("text", ""))
            self._add_line(lay, _t("hours"), "hours", values.get("hours_str", ""))
            self._check_done = QCheckBox(_t("done"))
            self._check_done.setChecked(values.get("done", False))
            lay.addWidget(self._check_done)

        # botões
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_save   = QPushButton(_t("save"))
        btn_cancel = QPushButton(_t("cancel"))
        btn_save.setStyleSheet(_ss_btn(palette))
        btn_cancel.setStyleSheet(_ss_btn_gray(palette))
        btn_save.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_save)
        btn_row.addWidget(btn_cancel)
        lay.addLayout(btn_row)

    def _add_line(self, lay: QVBoxLayout, label: str, key: str, value: str):
        lbl = QLabel(label)
        lbl.setStyleSheet(_ss_label(self._palette))
        lay.addWidget(lbl)
        entry = QLineEdit()
        if key == "hours":
            entry.setInputMask("99:99;0")
        entry.setText(value)
        entry.returnPressed.connect(self.accept)
        lay.addWidget(entry)
        self._fields[key] = entry

    def _on_meio_changed(self, text: str):
        is_chamado = (_meio_display_to_internal(text) == "Chamado")
        self._lbl_chamado.setVisible(is_chamado)
        self._entry_chamado.setVisible(is_chamado)

    def get_values(self) -> dict:
        # campos com máscara: displayText() inclui separadores (ex: "01:30");
        # text() pode omitir o separador devolvendo "0130" em certas versões do Qt.
        result = {
            k: (e.displayText() if e.inputMask() else e.text()).strip()
            for k, e in self._fields.items()
        }
        if self._mode == "task":
            result["via"]     = _meio_display_to_internal(self._combo_meio.currentText())
            result["chamado"] = self._entry_chamado.text().strip()
            result["done"]    = self._check_done.isChecked()
        elif self._mode == "detail":
            result["done"] = self._check_done.isChecked()
        return result


# ── modal para adicionar tarefa rapidamente ───────────────────────────────────

class AddTaskDialog(QDialog):
    """Modal para adicionar uma nova tarefa a uma pessoa existente."""

    def __init__(self, parent: QWidget, palette: dict, person_name: str):
        super().__init__(parent)
        self.setWindowTitle(_t("add_task_title", person_name))
        self.setMinimumWidth(380)
        self.setStyleSheet(_ss_root(palette))
        self._palette = palette

        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.setContentsMargins(20, 20, 20, 20)

        self._fields: dict[str, QLineEdit] = {}

        # Tarefa
        self._add_line(lay, _t("task"), "title", "")

        # Meio
        lbl_meio = QLabel(_t("channel"))
        lbl_meio.setStyleSheet(_ss_label(palette))
        lay.addWidget(lbl_meio)
        self._combo_meio = QComboBox()
        self._combo_meio.addItems(_meios_display())
        lay.addWidget(self._combo_meio)

        # Nº chamado
        self._lbl_chamado = QLabel(_t("ticket_number"))
        self._lbl_chamado.setStyleSheet(_ss_label(palette))
        self._entry_chamado = QLineEdit()
        lay.addWidget(self._lbl_chamado)
        lay.addWidget(self._entry_chamado)
        self._lbl_chamado.setVisible(False)
        self._entry_chamado.setVisible(False)
        self._combo_meio.currentTextChanged.connect(self._on_meio_changed)

        # Detalhe (opcional)
        self._add_line(lay, _t("detail"), "detail", "")

        # Horas
        self._add_line(lay, _t("hours"), "hours", "")

        # Concluída
        self._check_done = QCheckBox(_t("done"))
        self._check_done.setChecked(True)
        lay.addWidget(self._check_done)

        # botões
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_save = QPushButton(_t("add"))
        btn_cancel = QPushButton(_t("cancel"))
        btn_save.setStyleSheet(_ss_btn(palette))
        btn_cancel.setStyleSheet(_ss_btn_gray(palette))
        btn_save.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_save)
        btn_row.addWidget(btn_cancel)
        lay.addLayout(btn_row)

    def _add_line(self, lay: QVBoxLayout, label: str, key: str, value: str):
        lbl = QLabel(label)
        lbl.setStyleSheet(_ss_label(self._palette))
        lay.addWidget(lbl)
        entry = QLineEdit()
        if key == "hours":
            entry.setInputMask("99:99;0")
        entry.setText(value)
        entry.returnPressed.connect(self.accept)
        lay.addWidget(entry)
        self._fields[key] = entry

    def _on_meio_changed(self, text: str):
        is_chamado = (_meio_display_to_internal(text) == "Chamado")
        self._lbl_chamado.setVisible(is_chamado)
        self._entry_chamado.setVisible(is_chamado)

    def get_values(self) -> dict:
        result = {
            k: (e.displayText() if e.inputMask() else e.text()).strip()
            for k, e in self._fields.items()
        }
        result["via"] = _meio_display_to_internal(self._combo_meio.currentText())
        result["chamado"] = self._entry_chamado.text().strip()
        result["done"] = self._check_done.isChecked()
        return result


# ── modal para adicionar detalhe rapidamente ──────────────────────────────────

class AddDetailDialog(QDialog):
    """Modal para adicionar um novo detalhe a uma tarefa existente."""

    def __init__(self, parent: QWidget, palette: dict, task_title: str):
        super().__init__(parent)
        self.setWindowTitle(_t("add_detail_title", task_title))
        self.setMinimumWidth(380)
        self.setStyleSheet(_ss_root(palette))
        self._palette = palette

        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.setContentsMargins(20, 20, 20, 20)

        self._fields: dict[str, QLineEdit] = {}

        # Detalhe
        self._add_line(lay, _t("detail"), "text", "")

        # Horas
        self._add_line(lay, _t("hours"), "hours", "")

        # Concluída
        self._check_done = QCheckBox(_t("done"))
        self._check_done.setChecked(True)
        lay.addWidget(self._check_done)

        # botões
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_save = QPushButton(_t("add"))
        btn_cancel = QPushButton(_t("cancel"))
        btn_save.setStyleSheet(_ss_btn(palette))
        btn_cancel.setStyleSheet(_ss_btn_gray(palette))
        btn_save.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_save)
        btn_row.addWidget(btn_cancel)
        lay.addLayout(btn_row)

    def _add_line(self, lay: QVBoxLayout, label: str, key: str, value: str):
        lbl = QLabel(label)
        lbl.setStyleSheet(_ss_label(self._palette))
        lay.addWidget(lbl)
        entry = QLineEdit()
        if key == "hours":
            entry.setInputMask("99:99;0")
        entry.setText(value)
        entry.returnPressed.connect(self.accept)
        lay.addWidget(entry)
        self._fields[key] = entry

    def get_values(self) -> dict:
        result = {
            k: (e.displayText() if e.inputMask() else e.text()).strip()
            for k, e in self._fields.items()
        }
        result["done"] = self._check_done.isChecked()
        return result


# ── main window ───────────────────────────────────────────────────────────────

class DailyApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(_t("app_title"))
        self.setMinimumSize(360, 500)
        # Load theme from config
        self._palette = PALETTE_LIGHT if _config.get("theme") == "light" else PALETTE_DARK
        self._themed_labels: list = []
        self._build_ui()
        self._apply_theme(self._palette)
        QShortcut(QKeySequence("Ctrl+Q"), self, activated=self.close)
        self._load_all()

    # ── ui ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(0)

        self._tabs = QTabWidget()

        self._splitter = QSplitter()
        self._splitter.setHandleWidth(2)
        self._layout_mode = None
        self._splitter.addWidget(self._build_form())
        self._splitter.addWidget(self._build_tree_panel())
        self._tabs.addTab(self._splitter, _t("tab_register"))

        self._tabs.addTab(self._build_summary_panel(), _t("tab_summary"))
        self._tabs.addTab(self._build_settings_panel(), _t("tab_settings"))
        self._tabs.currentChanged.connect(self._on_tab_changed)

        root.addWidget(self._tabs)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = event.size().width(), event.size().height()
        mode = "h" if w >= h else "v"
        if mode != self._layout_mode:
            self._layout_mode = mode
            if mode == "h":
                self._splitter.setOrientation(Qt.Orientation.Horizontal)
                self._splitter.setSizes([w // 2, w // 2])
            else:
                self._splitter.setOrientation(Qt.Orientation.Vertical)
                self._splitter.setSizes([h // 2, h // 2])

    def _build_form(self) -> QWidget:
        wrap = QWidget()
        lay  = QVBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 8, 0)
        lay.setSpacing(8)

        self._card = QFrame()
        card_lay = QVBoxLayout(self._card)
        card_lay.setContentsMargins(16, 16, 16, 16)
        card_lay.setSpacing(10)

        # data
        lbl_date = QLabel(_t("date"))
        card_lay.addWidget(lbl_date)
        self._themed_labels.append(lbl_date)
        date_row = QHBoxLayout()
        date_row.setSpacing(6)
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        self.date_edit.dateChanged.connect(lambda _: self._refresh_tree())
        date_row.addWidget(self.date_edit)
        self._btn_today = QPushButton(_t("today"))
        self._btn_today.clicked.connect(lambda: self.date_edit.setDate(QDate.currentDate()))
        date_row.addWidget(self._btn_today)
        card_lay.addLayout(date_row)

        # pessoa com botão "Eu Mesmo" ao lado
        lbl_person = QLabel(_t("requester"))
        self._themed_labels.append(lbl_person)
        card_lay.addWidget(lbl_person)
        person_row = QHBoxLayout()
        person_row.setSpacing(6)
        self.entry_person = QLineEdit()
        self.entry_person.setPlaceholderText(_t("type_placeholder", _t("requester").lower()))
        person_row.addWidget(self.entry_person)
        self._btn_myself = QPushButton(_t("myself_btn"))
        self._btn_myself.setFixedWidth(42)
        self._btn_myself.setToolTip(_t("myself"))
        self._btn_myself.clicked.connect(lambda: self.entry_person.setText(_t("myself")))
        person_row.addWidget(self._btn_myself)
        card_lay.addLayout(person_row)
        self._person_model = QStringListModel()
        _completer = QCompleter(self._person_model, self)
        _completer.setCompletionMode(QCompleter.CompletionMode.InlineCompletion)
        _completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.entry_person.setCompleter(_completer)

        # meio
        lbl_meio = QLabel(_t("channel"))
        card_lay.addWidget(lbl_meio)
        self._themed_labels.append(lbl_meio)
        self.combo_meio = QComboBox()
        self.combo_meio.addItems(_meios_display())
        card_lay.addWidget(self.combo_meio)

        # nº chamado (visível só quando Chamado selecionado)
        self.lbl_chamado   = QLabel(_t("ticket_number"))
        self.entry_chamado = QLineEdit()
        self.entry_chamado.setPlaceholderText(_t("ticket_placeholder"))
        self._themed_labels.append(self.lbl_chamado)
        card_lay.addWidget(self.lbl_chamado)
        card_lay.addWidget(self.entry_chamado)
        self.lbl_chamado.hide()
        self.entry_chamado.hide()
        self.combo_meio.currentTextChanged.connect(self._on_meio_changed)

        # tarefa e detalhe lado a lado
        td_row = QHBoxLayout()
        td_row.setSpacing(8)
        task_col = QVBoxLayout()
        task_col.setSpacing(2)
        self._lbl_task = QLabel(_t("task"))
        self._themed_labels.append(self._lbl_task)
        task_col.addWidget(self._lbl_task)
        self.entry_task = QLineEdit()
        self.entry_task.setPlaceholderText(_t("type_placeholder", _t("task").lower()))
        task_col.addWidget(self.entry_task)
        td_row.addLayout(task_col, stretch=3)

        detail_col = QVBoxLayout()
        detail_col.setSpacing(2)
        self._lbl_detail = QLabel(_t("detail"))
        self._themed_labels.append(self._lbl_detail)
        detail_col.addWidget(self._lbl_detail)
        self.entry_detail = QLineEdit()
        self.entry_detail.setPlaceholderText(_t("type_placeholder", _t("detail").lower()))
        detail_col.addWidget(self.entry_detail)
        td_row.addLayout(detail_col, stretch=2)
        card_lay.addLayout(td_row)

        # horas e concluída lado a lado
        hd_row = QHBoxLayout()
        hd_row.setSpacing(8)
        hours_col = QVBoxLayout()
        hours_col.setSpacing(2)
        lbl_hours = QLabel(_t("hours"))
        self._themed_labels.append(lbl_hours)
        hours_col.addWidget(lbl_hours)
        self.entry_hours = QLineEdit()
        self.entry_hours.setInputMask("99:99;0")
        hours_col.addWidget(self.entry_hours)
        hd_row.addLayout(hours_col, stretch=1)

        done_col = QVBoxLayout()
        done_col.setSpacing(2)
        lbl_done_spacer = QLabel("")
        self._themed_labels.append(lbl_done_spacer)
        done_col.addWidget(lbl_done_spacer)  # espaçador para alinhar verticalmente
        self.check_done = QCheckBox(_t("done"))
        self.check_done.setChecked(True)
        done_col.addWidget(self.check_done)
        hd_row.addLayout(done_col, stretch=1)
        card_lay.addLayout(hd_row)

        self.entry_person.returnPressed.connect(lambda: self.entry_task.setFocus())
        self.entry_task.returnPressed.connect(self._add)
        self.entry_detail.returnPressed.connect(self._add)
        self.entry_hours.returnPressed.connect(self._add)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self._btn_add   = QPushButton(_t("add"))
        self._btn_clear = QPushButton(_t("clear"))
        self._btn_add.clicked.connect(self._add)
        self._btn_clear.clicked.connect(self._clear_form)
        btn_row.addWidget(self._btn_add)
        btn_row.addStretch()
        btn_row.addWidget(self._btn_clear)
        card_lay.addLayout(btn_row)

        self._lbl_hint = QLabel("")
        self._lbl_hint.setStyleSheet("font-size: 9pt; border: none;")
        card_lay.addWidget(self._lbl_hint)

        self.entry_person.textChanged.connect(self._update_form_hint)
        self.entry_task.textChanged.connect(self._update_form_hint)
        self.date_edit.dateChanged.connect(lambda _: self._update_form_hint())

        lay.addWidget(self._card)
        lay.addStretch()
        return wrap

    def _build_tree_panel(self) -> QWidget:
        wrap = QWidget()
        lay  = QVBoxLayout(wrap)
        lay.setContentsMargins(6, 0, 0, 0)
        lay.setSpacing(8)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        lbl_tree = QLabel(_t("tasks_added"))
        self._themed_labels.append(lbl_tree)
        self._btn_theme = QPushButton()
        self._btn_theme.setFixedHeight(24)
        self._btn_theme.clicked.connect(self._toggle_theme)
        header_row.addWidget(lbl_tree)
        header_row.addStretch()
        header_row.addWidget(self._btn_theme)
        lay.addLayout(header_row)

        self.tree = TaskTree()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(16)
        self.tree.setWordWrap(True)
        self.tree.setUniformRowHeights(False)
        self.tree.setItemDelegate(DeleteDelegate(self.tree))
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree.delete_requested.connect(self._delete_item)
        self.tree.add_requested.connect(self._add_inline)
        self.tree.sync_requested.connect(self._sync_from_tree)
        self.tree.move_requested.connect(self._move_item)
        lay.addWidget(self.tree)

        self._summary_frame  = QFrame()
        self._summary_layout = QVBoxLayout(self._summary_frame)
        self._summary_layout.setContentsMargins(0, 4, 0, 0)
        self._summary_layout.setSpacing(3)
        lay.addWidget(self._summary_frame)

        return wrap

    def _build_summary_panel(self) -> QWidget:
        wrap = QWidget()
        lay  = QVBoxLayout(wrap)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        search_row = QHBoxLayout()
        search_row.setSpacing(8)
        lbl_s = QLabel(_t("search"))
        self._themed_labels.append(lbl_s)
        self._sum_search = QLineEdit()
        self._sum_search.setPlaceholderText(_t("search_placeholder"))
        self._sum_search.textChanged.connect(self._filter_summary)
        search_row.addWidget(lbl_s)
        search_row.addWidget(self._sum_search)
        search_row.addStretch()
        self._btn_raw = QPushButton(_t("raw_txt"))
        self._btn_raw.setCheckable(True)
        self._btn_raw.clicked.connect(self._toggle_raw_view)
        search_row.addWidget(self._btn_raw)
        self._btn_download = QPushButton(_t("download_txt"))
        self._btn_download.clicked.connect(self._download_txt)
        search_row.addWidget(self._btn_download)
        lay.addLayout(search_row)

        self._sum_tree = QTreeWidget()
        self._sum_tree.setHeaderHidden(True)
        self._sum_tree.setIndentation(18)
        self._sum_tree.setWordWrap(True)
        self._sum_tree.setUniformRowHeights(False)
        self._sum_tree.setMouseTracking(True)
        self._sum_tree.viewport().setMouseTracking(True)
        self._sum_delegate = DeleteDelegate(self._sum_tree)
        self._sum_tree.setItemDelegate(self._sum_delegate)
        lay.addWidget(self._sum_tree)

        self._sum_raw = QPlainTextEdit()
        self._sum_raw.setReadOnly(True)
        self._sum_raw.setFont(QFont("Monospace", 9))
        self._sum_raw.hide()
        lay.addWidget(self._sum_raw)

        return wrap

    def _build_settings_panel(self) -> QWidget:
        """Constrói a aba Configurações com opções de meta de horas."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        main_lay = QVBoxLayout(container)
        main_lay.setContentsMargins(16, 16, 16, 16)
        main_lay.setSpacing(16)

        # ── Título ────────────────────────────────────────────────────────
        self._settings_title = QLabel(_t("settings_title"))
        self._settings_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self._themed_labels.append(self._settings_title)
        main_lay.addWidget(self._settings_title)

        self._settings_desc = QLabel(_t("settings_desc"))
        self._settings_desc.setWordWrap(True)
        self._themed_labels.append(self._settings_desc)
        main_lay.addWidget(self._settings_desc)

        # ── Idioma e Tema ───────────────────────────────────────────────
        appearance_row = QHBoxLayout()
        appearance_row.setSpacing(16)

        # Idioma
        lang_col = QVBoxLayout()
        self._lbl_language = QLabel(_t("language_label"))
        self._themed_labels.append(self._lbl_language)
        lang_col.addWidget(self._lbl_language)
        self._combo_language = QComboBox()
        self._combo_language.addItems(["Português", "English"])
        self._combo_language.setCurrentIndex(0 if _config.get("language") == "pt" else 1)
        lang_col.addWidget(self._combo_language)
        appearance_row.addLayout(lang_col)

        # Tema
        theme_col = QVBoxLayout()
        self._lbl_theme = QLabel(_t("theme_label"))
        self._themed_labels.append(self._lbl_theme)
        theme_col.addWidget(self._lbl_theme)
        self._combo_theme = QComboBox()
        self._combo_theme.addItems([_t("theme_dark"), _t("theme_light")])
        self._combo_theme.setCurrentIndex(0 if _config.get("theme") == "dark" else 1)
        theme_col.addWidget(self._combo_theme)
        appearance_row.addLayout(theme_col)
        appearance_row.addStretch()

        main_lay.addLayout(appearance_row)

        # ── Opções visuais ────────────────────────────────────────────────
        visual_group = QGroupBox("Visual")
        visual_lay = QVBoxLayout(visual_group)
        visual_lay.setSpacing(4)
        self._settings_visual_group_box = visual_group

        self._chk_person_colors = QCheckBox(_t("bar_person_colors_label"))
        self._chk_person_colors.setChecked(bool(_config.get("bar_person_colors", False)))
        self._lbl_person_colors_desc = QLabel(_t("bar_person_colors_desc"))
        self._lbl_person_colors_desc.setStyleSheet("font-size: 8pt; padding-left: 22px;")
        self._themed_labels.append(self._lbl_person_colors_desc)
        visual_lay.addWidget(self._chk_person_colors)
        visual_lay.addWidget(self._lbl_person_colors_desc)
        main_lay.addWidget(visual_group)

        # ── Grupo de seleção de modo ──────────────────────────────────────
        mode_group = QGroupBox(_t("mode_group"))
        mode_lay = QVBoxLayout(mode_group)
        mode_lay.setSpacing(12)
        self._settings_mode_group_box = mode_group

        self._radio_none = QRadioButton(_t("mode_none"))
        self._radio_weekday = QRadioButton(_t("mode_weekday"))

        self._radio_btn_group = QButtonGroup(self)
        self._radio_btn_group.addButton(self._radio_none, 0)
        self._radio_btn_group.addButton(self._radio_weekday, 1)

        mode_lay.addWidget(self._radio_none)
        mode_lay.addWidget(self._radio_weekday)
        main_lay.addWidget(mode_group)

        # ── Painel de horas por dia da semana ─────────────────────────────
        self._weekday_group = QGroupBox(_t("weekday_group"))
        wk_lay = QVBoxLayout(self._weekday_group)
        wk_lay.setSpacing(8)
        self._settings_weekday_group_box = self._weekday_group

        self._weekday_spins: dict[str, QDoubleSpinBox] = {}
        self._weekday_labels: list[QLabel] = []
        for i, (short, wk_key) in enumerate(zip(_WEEKDAY_NAMES_SHORT, _WEEKDAY_KEYS)):
            row = QHBoxLayout()
            row.setSpacing(10)
            lbl = QLabel(_t(wk_key))
            lbl.setFixedWidth(90)
            lbl.setFont(QFont("Segoe UI", 10))
            self._themed_labels.append(lbl)
            self._weekday_labels.append(lbl)
            row.addWidget(lbl)

            spin = QDoubleSpinBox()
            spin.setRange(0, 24)
            spin.setSingleStep(0.5)
            spin.setDecimals(1)
            spin.setSuffix(" h")
            spin.setValue(_config["weekday_hours"].get(short, 0.0))
            spin.setFixedWidth(100)
            row.addWidget(spin)
            row.addStretch()
            self._weekday_spins[short] = spin
            wk_lay.addLayout(row)

        main_lay.addWidget(self._weekday_group)

        # ── Botão salvar ──────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self._btn_save_settings = QPushButton(_t("save_settings"))
        self._btn_save_settings.setFixedHeight(36)
        btn_row.addStretch()
        btn_row.addWidget(self._btn_save_settings)
        btn_row.addStretch()
        main_lay.addLayout(btn_row)

        main_lay.addStretch()

        # ── Conexões ──────────────────────────────────────────────────────
        self._radio_none.toggled.connect(self._on_settings_mode_toggled)
        self._btn_save_settings.clicked.connect(self._save_settings)

        # estado inicial
        if _config["hours_mode"] == "none":
            self._radio_none.setChecked(True)
        else:
            self._radio_weekday.setChecked(True)
        self._on_settings_mode_toggled()

        scroll.setWidget(container)
        return scroll

    def _on_settings_mode_toggled(self, _checked=None):
        """Habilita/desabilita painel de dias conforme o modo selecionado."""
        enabled = self._radio_weekday.isChecked()
        self._weekday_group.setEnabled(enabled)
        for spin in self._weekday_spins.values():
            spin.setEnabled(enabled)

    def _save_settings(self):
        """Salva as configurações no config.json e atualiza o app."""
        global _config
        if self._radio_none.isChecked():
            _config["hours_mode"] = "none"
        else:
            _config["hours_mode"] = "per_weekday"

        for short, spin in self._weekday_spins.items():
            _config["weekday_hours"][short] = spin.value()

        # Tema
        new_theme = "dark" if self._combo_theme.currentIndex() == 0 else "light"
        _config["theme"] = new_theme

        # Idioma
        new_lang = "pt" if self._combo_language.currentIndex() == 0 else "en"
        lang_changed = (new_lang != _config.get("language"))
        _config["language"] = new_lang

        # Barra colorida por pessoa
        _config["bar_person_colors"] = self._chk_person_colors.isChecked()

        _save_config(_config)

        # Aplica tema
        target_palette = PALETTE_LIGHT if new_theme == "light" else PALETTE_DARK
        if target_palette is not self._palette:
            self._apply_theme(target_palette)
        else:
            self._refresh_tree()

        self._refresh_hours_summary()

        # Se idioma mudou, atualiza todos os textos
        if lang_changed:
            self._refresh_ui_texts()

        QMessageBox.information(self, _t("settings_saved_title"), _t("settings_saved_msg"))

    def _refresh_ui_texts(self):
        """Atualiza todos os textos da UI após mudança de idioma."""
        self.setWindowTitle(_t("app_title"))
        self._tabs.setTabText(0, _t("tab_register"))
        self._tabs.setTabText(1, _t("tab_summary"))
        self._tabs.setTabText(2, _t("tab_settings"))

        # Settings panel texts
        self._settings_title.setText(_t("settings_title"))
        self._settings_desc.setText(_t("settings_desc"))
        self._lbl_language.setText(_t("language_label"))
        self._lbl_theme.setText(_t("theme_label"))
        self._combo_theme.setItemText(0, _t("theme_dark"))
        self._combo_theme.setItemText(1, _t("theme_light"))
        self._settings_mode_group_box.setTitle(_t("mode_group"))
        self._radio_none.setText(_t("mode_none"))
        self._radio_weekday.setText(_t("mode_weekday"))
        self._weekday_group.setTitle(_t("weekday_group"))
        for lbl, wk_key in zip(self._weekday_labels, _WEEKDAY_KEYS):
            lbl.setText(_t(wk_key))
        self._btn_save_settings.setText(_t("save_settings"))
        self._chk_person_colors.setText(_t("bar_person_colors_label"))
        self._lbl_person_colors_desc.setText(_t("bar_person_colors_desc"))

        # Refresh combo_meio items
        current_meio_idx = self.combo_meio.currentIndex()
        self.combo_meio.clear()
        self.combo_meio.addItems(_meios_display())
        self.combo_meio.setCurrentIndex(current_meio_idx)

        # Refresh form labels and placeholders
        self._lbl_task.setText(_t("task"))
        self._lbl_detail.setText(_t("detail"))
        self._btn_myself.setText(_t("myself_btn"))
        self._btn_myself.setToolTip(_t("myself"))
        self.entry_person.setPlaceholderText(_t("type_placeholder", _t("requester").lower()))
        self.entry_task.setPlaceholderText(_t("type_placeholder", _t("task").lower()))
        self.entry_detail.setPlaceholderText(_t("type_placeholder", _t("detail").lower()))

        # Renomeia "MySelf" ↔ "Eu Mesmo" nos dados conforme idioma
        _rename_myself_all()
        self._save_file(silent=True)
        self._refresh_tree()

    def _on_meio_changed(self, text: str):
        is_chamado = (_meio_display_to_internal(text) == "Chamado")
        self.lbl_chamado.setVisible(is_chamado)
        self.entry_chamado.setVisible(is_chamado)
        if not is_chamado:
            self.entry_chamado.clear()

    def _update_form_hint(self):
        """Atualiza o hint abaixo do formulário indicando se a tarefa já existe."""
        title  = self.entry_task.text().strip()
        if not title:
            self._lbl_hint.setText("")
            return
        person = self.entry_person.text().strip() or _t("myself")
        lbl    = self._current_label()
        p      = self._palette
        if lbl in all_data:
            _, persons = all_data[lbl]
            person_entry = next(
                (x for x in persons if x["person"].lower() == person.lower()), None
            )
            if person_entry:
                task_match = next(
                    (t for t in person_entry["tasks"]
                     if t["title"].lower() == title.lower()),
                    None,
                )
                if task_match:
                    self._lbl_hint.setText(
                        f'{_t("hint_detail_mode")} "{task_match["title"]}"'
                    )
                    self._lbl_hint.setStyleSheet(
                        f"font-size: 9pt; color: {p['ACCENT']}; border: none;"
                    )
                    return
        self._lbl_hint.setText("")

    def _on_item_double_clicked(self, item: QTreeWidgetItem, _col: int):
        parent      = item.parent()
        grandparent = parent.parent() if parent else None
        great       = grandparent.parent() if grandparent else None

        if parent is None:
            # clique na data: oferece marcar tudo como concluído
            lbl = item.data(0, Qt.ItemDataRole.UserRole)
            if lbl not in all_data:
                return
            reply = QMessageBox.question(
                self, _t("mark_day_done_title"),
                _t("mark_day_done_msg", lbl),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            for person in all_data[lbl][1]:
                for t in person["tasks"]:
                    t["done"] = True
                    for d in t["details"]:
                        d["done"] = True
            self._refresh_tree()
            self._save_file(silent=True)
            return

        top = item
        while top.parent():
            top = top.parent()
        lbl = top.data(0, Qt.ItemDataRole.UserRole)
        if lbl not in all_data:
            return

        _, persons = all_data[lbl]

        # ── pessoa ──────────────────────────────────────────────────────────
        if grandparent is None:
            pname = item.data(0, Qt.ItemDataRole.UserRole)
            # Mostrar opções: Editar nome, Concluir tudo, ou Nova Tarefa
            msg = QMessageBox(self)
            msg.setWindowTitle(_t("person_action_title", pname))
            msg.setText(_t("person_action_msg", pname))
            msg.setStyleSheet(_ss_root(self._palette))
            btn_add_task = msg.addButton(_t("person_add_task"), QMessageBox.ButtonRole.AcceptRole)
            btn_done = msg.addButton(_t("person_mark_done"), QMessageBox.ButtonRole.AcceptRole)
            btn_edit = msg.addButton(_t("person_edit"), QMessageBox.ButtonRole.ActionRole)
            btn_cancel = msg.addButton(_t("cancel"), QMessageBox.ButtonRole.RejectRole)
            msg.exec()

            clicked = msg.clickedButton()
            if clicked == btn_add_task:
                # Abrir diálogo para adicionar nova tarefa à pessoa
                dlg = AddTaskDialog(self, self._palette, pname)
                if dlg.exec() != QDialog.DialogCode.Accepted:
                    return
                vals = dlg.get_values()
                title = vals.get("title", "").strip()
                if not title:
                    return
                p = find_or_create_person(persons, pname)
                via_val = vals.get("via", "")
                via_val = via_val if via_val != "—" else ""
                chamado = vals.get("chamado", "")
                hours = self._parse_hours(vals.get("hours", ""))
                done = vals.get("done", True)
                detail_text = vals.get("detail", "").strip()
                if detail_text:
                    det_dict = {"text": detail_text, "hours": hours, "done": done}
                    p["tasks"].append({
                        "title": title, "via": via_val, "chamado": chamado,
                        "hours": 0.0, "done": False, "details": [det_dict],
                    })
                else:
                    p["tasks"].append({
                        "title": title, "via": via_val, "chamado": chamado,
                        "hours": hours, "done": done, "details": [],
                    })
            elif clicked == btn_done:
                # Marcar todas as tarefas e detalhes desta pessoa como concluídas
                for p in persons:
                    if p["person"] == pname:
                        for t in p["tasks"]:
                            t["done"] = True
                            for d in t["details"]:
                                d["done"] = True
                        break
            elif clicked == btn_edit:
                dlg = EditDialog(self, self._palette, "person", {"person": pname})
                if dlg.exec() != QDialog.DialogCode.Accepted:
                    return
                new_name = dlg.get_values().get("person", "").strip()
                if new_name and new_name != pname:
                    for p in persons:
                        if p["person"] == pname:
                            p["person"] = new_name
                            break
            else:
                return  # cancelou

        # ── tarefa ────────────────────────────────────────────────────────────
        elif great is None:
            pname  = parent.data(0, Qt.ItemDataRole.UserRole)
            ttitle = item.data(0, Qt.ItemDataRole.UserRole)
            task   = next(
                (t for p in persons if p["person"] == pname
                 for t in p["tasks"] if t["title"] == ttitle),
                None,
            )
            if task is None:
                return

            # Mostrar opções: Editar, Concluir, ou Novo Detalhe
            msg = QMessageBox(self)
            msg.setWindowTitle(_t("task_action_title", ttitle))
            msg.setText(_t("task_action_msg", ttitle))
            msg.setStyleSheet(_ss_root(self._palette))
            btn_add_detail = msg.addButton(_t("task_add_detail"), QMessageBox.ButtonRole.AcceptRole)
            btn_done = msg.addButton(_t("task_mark_done"), QMessageBox.ButtonRole.AcceptRole)
            btn_edit = msg.addButton(_t("task_edit"), QMessageBox.ButtonRole.ActionRole)
            btn_cancel = msg.addButton(_t("cancel"), QMessageBox.ButtonRole.RejectRole)
            msg.exec()

            clicked = msg.clickedButton()
            if clicked == btn_add_detail:
                # Abrir diálogo para adicionar novo detalhe à tarefa
                dlg = AddDetailDialog(self, self._palette, ttitle)
                if dlg.exec() != QDialog.DialogCode.Accepted:
                    return
                vals = dlg.get_values()
                det_text = vals.get("text", "").strip()
                if not det_text:
                    return
                hours = self._parse_hours(vals.get("hours", ""))
                done = vals.get("done", True)
                task["details"].append({"text": det_text, "hours": hours, "done": done})
            elif clicked == btn_done:
                task["done"] = True
                for d in task["details"]:
                    d["done"] = True
            elif clicked == btn_edit:
                dlg = EditDialog(self, self._palette, "task", {
                    "title":     task["title"],
                    "via":       task.get("via", ""),
                    "chamado":   task.get("chamado", ""),
                    "hours_str": _fmt_hhmm(task["hours"]),
                    "done":      task.get("done", True),
                })
                if dlg.exec() != QDialog.DialogCode.Accepted:
                    return
                vals = dlg.get_values()
                new_title = vals.get("title", "").strip() or task["title"]
                via_val   = vals.get("via", "")
                task["title"]   = new_title
                task["via"]     = via_val if via_val != "—" else ""
                task["chamado"] = vals.get("chamado", "") if via_val == "Chamado" else ""
                task["hours"]   = self._parse_hours(vals.get("hours", ""))
                task["done"]    = vals.get("done", False)
            else:
                return  # cancelou

        # ── detalhe ───────────────────────────────────────────────────────────
        else:
            pname   = grandparent.data(0, Qt.ItemDataRole.UserRole)
            ttitle  = parent.data(0, Qt.ItemDataRole.UserRole)
            det_idx = parent.indexOfChild(item)
            det     = next(
                (t["details"][det_idx]
                 for p in persons if p["person"] == pname
                 for t in p["tasks"] if t["title"] == ttitle
                 if 0 <= det_idx < len(t["details"])),
                None,
            )
            if det is None:
                return
            dlg = EditDialog(self, self._palette, "detail", {
                "text":      det["text"],
                "hours_str": _fmt_hhmm(det["hours"]),
                "done":      det.get("done", True),
            })
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            vals = dlg.get_values()
            new_text = vals.get("text", "").strip() or det["text"]
            det["text"]  = new_text
            det["hours"] = self._parse_hours(vals.get("hours", ""))
            det["done"]  = vals.get("done", False)

        self._refresh_tree()
        self._save_file(silent=True)
        self._update_person_completer()

    def _add_inline(self, item: QTreeWidgetItem):
        """Chamado pelo botão + inline na árvore. Abre diálogo para adicionar sub-item."""
        level = TaskTree._item_level(item)

        # Navegar até o nó de data (top)
        top = item
        while top.parent():
            top = top.parent()
        lbl = top.data(0, Qt.ItemDataRole.UserRole)
        if lbl not in all_data:
            return
        _, persons = all_data[lbl]

        if level == 1:
            # Item é uma pessoa → adicionar nova tarefa
            pname = item.data(0, Qt.ItemDataRole.UserRole)
            dlg = AddTaskDialog(self, self._palette, pname)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            vals = dlg.get_values()
            title = vals.get("title", "").strip()
            if not title:
                return
            p = find_or_create_person(persons, pname)
            via_val = vals.get("via", "")
            via_val = via_val if via_val != "—" else ""
            chamado = vals.get("chamado", "")
            hours = self._parse_hours(vals.get("hours", ""))
            done = vals.get("done", True)
            detail_text = vals.get("detail", "").strip()
            if detail_text:
                det_dict = {"text": detail_text, "hours": hours, "done": done}
                p["tasks"].append({
                    "title": title, "via": via_val, "chamado": chamado,
                    "hours": 0.0, "done": True, "details": [det_dict],
                })
            else:
                p["tasks"].append({
                    "title": title, "via": via_val, "chamado": chamado,
                    "hours": hours, "done": done, "details": [],
                })

        elif level == 2:
            # Item é uma tarefa → adicionar novo detalhe
            pname  = item.parent().data(0, Qt.ItemDataRole.UserRole)
            ttitle = item.data(0, Qt.ItemDataRole.UserRole)
            task = next(
                (t for p in persons if p["person"] == pname
                 for t in p["tasks"] if t["title"] == ttitle),
                None,
            )
            if task is None:
                return
            dlg = AddDetailDialog(self, self._palette, ttitle)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            vals = dlg.get_values()
            det_text = vals.get("text", "").strip()
            if not det_text:
                return
            hours = self._parse_hours(vals.get("hours", ""))
            done = vals.get("done", True)
            task["details"].append({"text": det_text, "hours": hours, "done": done})
        else:
            return

        self._refresh_tree()
        self._save_file(silent=True)
        self._update_person_completer()

    def _field(self, layout: QVBoxLayout, label: str) -> QLineEdit:
        lbl = QLabel(label)
        self._themed_labels.append(lbl)
        layout.addWidget(lbl)
        entry = QLineEdit()
        entry.setPlaceholderText(_t("type_placeholder", label.lower()))
        layout.addWidget(entry)
        return entry

    # ── load ──────────────────────────────────────────────────────────────────

    def _load_all(self):
        all_data.clear()
        filename = "daily.txt"
        if not os.path.exists(filename):
            self._refresh_tree()
            return

        raw = open(filename, encoding="utf-8").read().strip()
        if not raw:
            self._refresh_tree()
            return

        for part in re.split(r'(?=\*\*=)', raw):
            part = part.strip()
            if not part:
                continue
            m = re.match(r'\*\*=+\s*\*\*(.+)', part.split("\n")[0])
            if not m:
                continue
            lbl = m.group(1).strip()
            persons: list[dict] = []
            current_person = None
            current_task   = None
            for line in part.split("\n")[1:]:
                if line.startswith("/ "):
                    current_person = find_or_create_person(persons, line[2:].rstrip(":").strip())
                    current_task   = None
                elif line.startswith("- ") and current_person:
                    raw_task  = line[2:].rstrip(":")
                    parts     = raw_task.split(" | ")
                    ttitle    = parts[0].strip()
                    via = chamado = ""
                    task_hours = 0.0
                    task_done  = True   # padrão: concluída
                    for part_s in parts[1:]:
                        part_s = part_s.strip()
                        if part_s.startswith("Chamado #"):
                            via = "Chamado"
                            chamado = part_s[len("Chamado #"):]
                        elif re.match(r'^\d+(\.\d+)?h$', part_s):
                            task_hours = float(part_s[:-1])
                        elif part_s == "pending":
                            task_done = False
                        elif part_s == "done":
                            task_done = True   # compatibilidade retroativa
                        elif part_s in MEIOS:
                            via = part_s
                    current_task = {
                        "title": ttitle, "via": via, "chamado": chamado,
                        "hours": task_hours, "done": task_done, "details": [],
                    }
                    current_person["tasks"].append(current_task)
                elif line.startswith("  - ") and current_task:
                    detail_raw = line[4:].rstrip(";")
                    dparts     = detail_raw.split(" | ")
                    dtext      = dparts[0].strip()
                    dhours     = 0.0
                    ddone      = True   # padrão: concluído
                    for dp in dparts[1:]:
                        dp = dp.strip()
                        if re.match(r'^\d+(\.\d+)?h$', dp):
                            dhours = float(dp[:-1])
                        elif dp == "pending":
                            ddone = False
                        elif dp == "done":
                            ddone = True   # compatibilidade retroativa
                    current_task["details"].append({"text": dtext, "hours": dhours, "done": ddone})
            all_data[lbl] = (parse_label_to_date(lbl), persons)

        # Renomeia "MySelf" ↔ "Eu Mesmo" conforme idioma atual
        _rename_myself_all()
        self._refresh_tree()
        self._update_person_completer()
        self._purge_old_trash()

    def _update_person_completer(self):
        names = sorted({p["person"] for _, persons in all_data.values() for p in persons})
        self._person_model.setStringList(names)

    # ── theme ─────────────────────────────────────────────────────────────────

    def _toggle_theme(self):
        new_palette = PALETTE_LIGHT if self._palette is PALETTE_DARK else PALETTE_DARK
        _config["theme"] = "light" if new_palette is PALETTE_LIGHT else "dark"
        _save_config(_config)
        self._apply_theme(new_palette)
        # Atualiza combo de tema na aba configurações
        if hasattr(self, "_combo_theme"):
            self._combo_theme.setCurrentIndex(0 if _config["theme"] == "dark" else 1)

    def _apply_theme(self, palette: dict):
        self._palette = palette
        self.setStyleSheet(_ss_root(palette))
        self._card.setStyleSheet(_ss_card(palette))
        ss_lbl = _ss_label(palette)
        for lbl in self._themed_labels:
            lbl.setStyleSheet(ss_lbl)
        self._btn_add.setStyleSheet(_ss_btn(palette))
        self._btn_clear.setStyleSheet(_ss_btn_gray(palette))
        self._btn_today.setStyleSheet(_ss_btn(palette))
        self._btn_myself.setStyleSheet(_ss_btn_theme(palette))
        self._btn_theme.setText(palette["ICON"])
        self._btn_theme.setStyleSheet(_ss_btn_theme(palette))
        self._btn_save_settings.setStyleSheet(_ss_btn(palette))
        self._btn_download.setStyleSheet(_ss_btn_gray(palette))
        raw_checked = self._btn_raw.isChecked()
        self._btn_raw.setStyleSheet(
            _ss_btn(palette) if raw_checked else _ss_btn_gray(palette)
        )
        # GroupBox styling
        gb_ss = (f"QGroupBox {{ color: {palette['TEXT']}; border: 1px solid {palette['BORDER']};"
                 f" border-radius: 10px; padding: 16px 12px 12px 12px; margin-top: 10px;"
                 f" font-weight: 600; font-size: 10pt; }}"
                 f" QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; }}")
        self._settings_mode_group_box.setStyleSheet(gb_ss)
        self._settings_weekday_group_box.setStyleSheet(gb_ss)
        # SpinBox styling
        spin_ss = (f"QDoubleSpinBox {{ background: {palette['SURFACE']}; color: {palette['TEXT']};"
                   f" border: 1px solid {palette['BORDER']}; border-radius: 8px;"
                   f" padding: 5px 8px; font-size: 10pt; }}"
                   f" QDoubleSpinBox:focus {{ border: 1.5px solid {palette['ACCENT']}; }}")
        for spin in self._weekday_spins.values():
            spin.setStyleSheet(spin_ss)
        # RadioButton styling
        radio_ss = (f"QRadioButton {{ color: {palette['TEXT']}; spacing: 8px; font-size: 10pt; }}"
                    f" QRadioButton::indicator {{ width: 16px; height: 16px;"
                    f" border: 1px solid {palette['BORDER']}; border-radius: 8px;"
                    f" background: {palette['SURFACE']}; }}"
                    f" QRadioButton::indicator:checked {{ background: {palette['ACCENT']};"
                    f" border: 1px solid {palette['ACCENT']}; }}")
        self._radio_none.setStyleSheet(radio_ss)
        self._radio_weekday.setStyleSheet(radio_ss)
        self._refresh_tree()
        self._refresh_hours_summary()

    # ── refresh ───────────────────────────────────────────────────────────────

    def _selected_date(self) -> date:
        q = self.date_edit.date()
        return date(q.year(), q.month(), q.day())

    def _current_label(self) -> str:
        return self._selected_date().strftime("%b %d").lstrip("0")

    def _refresh_tree(self):
        self.tree.clear()
        current_lbl = self._current_label()

        for lbl, (d_obj, persons) in sorted(all_data.items(), key=lambda x: x[1][0]):
            is_current = (lbl == current_lbl)

            # nível: data (não arrastável; recebe drops para reordenar pessoas)
            used   = _date_hours(persons)
            budget = _day_budget(d_obj)
            d_item = QTreeWidgetItem([_display_label(lbl)])
            d_item.setData(0, ROLE_USED, used)
            d_item.setData(0, ROLE_BUDGET, budget)
            d_item.setData(0, Qt.ItemDataRole.UserRole, lbl)
            d_item.setFlags(
                (d_item.flags() & ~Qt.ItemFlag.ItemIsDragEnabled)
                | Qt.ItemFlag.ItemIsDropEnabled
            )
            p = self._palette
            d_item.setForeground(0, QColor(p["AMBER"] if is_current else p["DATE_DIM"]))
            d_item.setFont(0, QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.tree.addTopLevelItem(d_item)
            d_item.setExpanded(is_current)

            for person in persons:
                # nível: pessoa (arrastável; recebe drops para reordenar tarefas)
                is_myself   = _is_myself(person["person"])
                p_hours     = _person_hours(person)
                p_hours_suf = f"  ·  {_fmt_hhmm(p_hours)}" if p_hours > 0 else ""
                has_pending = any(
                    not t.get("done", True) or any(not d.get("done", True) for d in t.get("details", []))
                    for t in person.get("tasks", [])
                )
                if is_myself:
                    p_prefix = "★"
                elif has_pending:
                    p_prefix = "●"
                else:
                    p_prefix = "✓"
                p_label     = f"{p_prefix} {person['person']}{p_hours_suf}"
                p_item    = QTreeWidgetItem([p_label])
                p_item.setData(0, Qt.ItemDataRole.UserRole, person["person"])
                p_item.setFlags(
                    p_item.flags()
                    | Qt.ItemFlag.ItemIsDragEnabled
                    | Qt.ItemFlag.ItemIsDropEnabled
                )
                if not has_pending and not is_myself:
                    p_item.setForeground(0, QColor(p["MUTED"]))
                else:
                    p_item.setForeground(0, QColor(p["PERSON"]))
                p_item.setFont(0, QFont("Segoe UI", 10, QFont.Weight.Bold))
                d_item.addChild(p_item)
                p_item.setExpanded(is_current)

                for task in person["tasks"]:
                    # nível: tarefa (arrastável; recebe drops para reordenar detalhes)
                    via_suf     = _task_via_suffix(task)
                    via_display = f"  ·  {via_suf.lstrip(' | ')}" if via_suf else ""
                    eff_hours   = _effective_task_hours(task)
                    hours_suf   = f"  ·  {_fmt_hhmm(eff_hours)}" if eff_hours else ""
                    is_done = task.get("done", True)
                    prefix  = "✓ " if is_done else "● "

                    t_item = QTreeWidgetItem([f"{prefix}{task['title']}{via_display}{hours_suf}"])
                    t_item.setData(0, Qt.ItemDataRole.UserRole, task["title"])
                    t_item.setData(0, ROLE_HOURS, task.get("hours", 0.0))
                    t_item.setData(0, ROLE_DONE,  is_done)
                    t_item.setFlags(
                        t_item.flags()
                        | Qt.ItemFlag.ItemIsDragEnabled
                        | Qt.ItemFlag.ItemIsDropEnabled
                    )
                    if not is_done:
                        t_item.setForeground(0, QColor(p["AMBER"]))
                    else:
                        t_item.setForeground(0, QColor(p["MUTED"]))
                    p_item.addChild(t_item)
                    t_item.setExpanded(is_current)

                    for det in task["details"]:
                        # nível: detalhe (arrastável; sem filhos)
                        det_hours_suf = f"  ·  {_fmt_hhmm(det['hours'])}" if det.get("hours") else ""
                        det_done   = det.get("done", True)
                        det_prefix = "✓ " if det_done else "● "

                        det_item = QTreeWidgetItem(
                            [f"  {det_prefix}{det['text']}{det_hours_suf}"]
                        )
                        det_item.setData(0, Qt.ItemDataRole.UserRole, det["text"])
                        det_item.setData(0, ROLE_HOURS, det.get("hours", 0.0))
                        det_item.setData(0, ROLE_DONE,  det_done)
                        det_item.setFlags(
                            (det_item.flags() | Qt.ItemFlag.ItemIsDragEnabled)
                            & ~Qt.ItemFlag.ItemIsDropEnabled
                        )
                        if det_done:
                            det_item.setForeground(0, QColor(p["MUTED"]))
                        else:
                            det_item.setForeground(0, QColor(p["AMBER"]))
                        t_item.addChild(det_item)

        self._refresh_hours_summary()
        if hasattr(self, "_tabs") and self._tabs.currentIndex() == 1:
            self._refresh_summary()

    # ── actions ───────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_hours(text: str) -> float:
        """Aceita: HH:MM (máscara), 1.5, 1,5, 1h, 1h30, 1h30min, 30min, 30m → horas decimais."""
        t = text.strip().replace(",", ".")
        if not t:
            return 0.0
        # formato HH:MM com separador (displayText da máscara)
        m = re.fullmatch(r'(\d{1,2}):(\d{2})', t)
        if m:
            h_val, mm_val = int(m.group(1)), int(m.group(2))
            return max(0.0, h_val + mm_val / 60)
        # formato HHMM sem separador (text() sem separador em algumas versões Qt)
        m = re.fullmatch(r'(\d{2})(\d{2})', t)
        if m:
            h_val, mm_val = int(m.group(1)), int(m.group(2))
            if mm_val < 60:
                return max(0.0, h_val + mm_val / 60)
        # formato "Xh Ymin" ou "XhY" ou "Xh"
        m = re.fullmatch(r'(\d+(?:\.\d+)?)\s*h(?:ours?)?\s*(\d+)?\s*(?:min(?:utos?)?|m)?', t, re.IGNORECASE)
        if m:
            h   = float(m.group(1))
            mn  = float(m.group(2)) if m.group(2) else 0.0
            return max(0.0, h + mn / 60)
        # formato "Xmin" ou "Xm"
        m = re.fullmatch(r'(\d+(?:\.\d+)?)\s*(?:min(?:utos?)?|m)', t, re.IGNORECASE)
        if m:
            return max(0.0, float(m.group(1)) / 60)
        # formato numérico puro ou "Xh" simples
        try:
            return max(0.0, float(t.rstrip("h")))
        except ValueError:
            return 0.0

    def _add(self):
        person = self.entry_person.text().strip()
        title  = self.entry_task.text().strip()
        detail = self.entry_detail.text().strip()
        if not title:
            QMessageBox.warning(self, _t("attention"), _t("fill_task"))
            return
        if not person:
            person = _t("myself")

        d   = self._selected_date()
        lbl = d.strftime("%b %d").lstrip("0")
        if lbl not in all_data:
            all_data[lbl] = (d, [])

        _, persons = all_data[lbl]
        via     = _meio_display_to_internal(self.combo_meio.currentText())
        chamado = self.entry_chamado.text().strip()
        hours   = self._parse_hours(self.entry_hours.displayText())
        done    = self.check_done.isChecked()
        p = find_or_create_person(persons, person)
        matched = [t for t in p["tasks"] if t["title"].lower() == title.lower()]

        via_val = via if via != "—" else ""
        if detail:
            det_dict = {"text": detail, "hours": hours, "done": done}
            if not matched:
                p["tasks"].append({
                    "title": title, "via": via_val, "chamado": chamado,
                    "hours": 0.0, "done": True, "details": [det_dict],
                })
            else:
                if via_val:
                    matched[-1]["via"]     = via_val
                    matched[-1]["chamado"] = chamado
                matched[-1]["details"].append(det_dict)
            self.entry_detail.clear()
            self.entry_hours.clear()
            self.entry_detail.setFocus()
            self._refresh_tree()
            self._save_file(silent=True)
            self._update_person_completer()
            self._update_form_hint()
            return
        else:
            if not matched:
                p["tasks"].append({
                    "title": title, "via": via_val, "chamado": chamado,
                    "hours": hours, "done": done, "details": [],
                })
            else:
                if via_val:
                    matched[-1]["via"]     = via_val
                    matched[-1]["chamado"] = chamado
                matched[-1]["hours"] = hours
                matched[-1]["done"]  = done
            # Limpa tarefa/meio/chamado/horas → pronto para próxima tarefa da mesma pessoa
            self.entry_task.clear()
            self.combo_meio.setCurrentIndex(0)
            self.entry_chamado.clear()
            self.entry_hours.clear()
            self.entry_task.setFocus()

        self._refresh_tree()
        self._save_file(silent=True)
        self._update_person_completer()
        self._update_form_hint()

    def _clear_form(self):
        self.entry_person.clear()
        self.entry_task.clear()
        self.entry_detail.clear()
        self.entry_chamado.clear()
        self.entry_hours.clear()
        self.check_done.setChecked(True)
        self.combo_meio.setCurrentIndex(0)
        self.entry_person.setFocus()

    def _delete_selected(self):
        item = self.tree.currentItem()
        if item:
            self._delete_item(item)

    def _confirm_delete(self, item: QTreeWidgetItem) -> bool:
        parent      = item.parent()
        grandparent = parent.parent() if parent else None
        great       = grandparent.parent() if grandparent else None

        lines: list[str] = []

        if parent is None:
            lbl = item.data(0, Qt.ItemDataRole.UserRole)
            if lbl in all_data:
                _, persons = all_data[lbl]
                lines.append(f"Data: {lbl}")
                for p in persons:
                    lines.append(f"  / {p['person']}")
                    for t in p["tasks"]:
                        lines.append(f"    - {t['title']}{_task_via_suffix(t)}")
                        for det in t["details"]:
                            lines.append(f"        · {det['text']}")

        elif grandparent is None:
            lbl   = parent.data(0, Qt.ItemDataRole.UserRole)
            pname = item.data(0, Qt.ItemDataRole.UserRole)
            if lbl in all_data:
                for p in all_data[lbl][1]:
                    if p["person"] == pname and p["tasks"]:
                        lines.append(f"/ {pname}")
                        for t in p["tasks"]:
                            lines.append(f"  - {t['title']}{_task_via_suffix(t)}")
                            for det in t["details"]:
                                lines.append(f"      · {det['text']}")

        elif great is None:
            lbl    = grandparent.data(0, Qt.ItemDataRole.UserRole)
            pname  = parent.data(0, Qt.ItemDataRole.UserRole)
            ttitle = item.data(0, Qt.ItemDataRole.UserRole)
            if lbl in all_data:
                for p in all_data[lbl][1]:
                    if p["person"] == pname:
                        for t in p["tasks"]:
                            if t["title"] == ttitle and t["details"]:
                                lines.append(f"- {ttitle}")
                                for det in t["details"]:
                                    lines.append(f"  · {det['text']}")

        if not lines:
            return True

        reply = QMessageBox.question(
            self,
            _t("confirm_delete_title"),
            _t("confirm_delete_msg", "\n".join(lines)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    # ── trash ─────────────────────────────────────────────────────────────────

    def _trash_lines_for_item(self, item: QTreeWidgetItem) -> list[str]:
        parent      = item.parent()
        grandparent = parent.parent() if parent else None
        great       = grandparent.parent() if grandparent else None
        lines: list[str] = []

        if parent is None:
            lbl = item.data(0, Qt.ItemDataRole.UserRole)
            if lbl in all_data:
                _, persons = all_data[lbl]
                lines.append(f"Data: {lbl}")
                for p in persons:
                    lines.append(f"  / {p['person']}:")
                    for t in p["tasks"]:
                        lines.append(f"    - {t['title']}{_task_via_suffix(t)}:")
                        for det in t["details"]:
                            lines.append(f"      - {det['text']};")

        elif grandparent is None:
            lbl   = parent.data(0, Qt.ItemDataRole.UserRole)
            pname = item.data(0, Qt.ItemDataRole.UserRole)
            lines.append(f"Data: {lbl}")
            if lbl in all_data:
                for p in all_data[lbl][1]:
                    if p["person"] == pname:
                        lines.append(f"  / {pname}:")
                        for t in p["tasks"]:
                            lines.append(f"    - {t['title']}{_task_via_suffix(t)}:")
                            for det in t["details"]:
                                lines.append(f"      - {det['text']};")

        elif great is None:
            lbl    = grandparent.data(0, Qt.ItemDataRole.UserRole)
            pname  = parent.data(0, Qt.ItemDataRole.UserRole)
            ttitle = item.data(0, Qt.ItemDataRole.UserRole)
            lines.append(f"Data: {lbl}  /  {pname}")
            if lbl in all_data:
                for p in all_data[lbl][1]:
                    if p["person"] == pname:
                        for t in p["tasks"]:
                            if t["title"] == ttitle:
                                lines.append(f"  - {ttitle}{_task_via_suffix(t)}:")
                                for det in t["details"]:
                                    lines.append(f"    - {det['text']};")

        else:
            lbl    = great.data(0, Qt.ItemDataRole.UserRole)
            pname  = grandparent.data(0, Qt.ItemDataRole.UserRole)
            ttitle = parent.data(0, Qt.ItemDataRole.UserRole)
            dtext  = item.data(0, Qt.ItemDataRole.UserRole)
            lines.append(f"Data: {lbl}  /  {pname}  /  {ttitle}")
            lines.append(f"  - {dtext};")

        return lines

    def _write_trash(self, item: QTreeWidgetItem):
        content = self._trash_lines_for_item(item)
        if not content:
            return
        timestamp = dt.now().strftime("%Y-%m-%d %H:%M:%S")
        block = f"**TRASH {timestamp}**\n" + "\n".join(content)
        existing = ""
        if os.path.exists(TRASH_FILE):
            existing = open(TRASH_FILE, encoding="utf-8").read()
        with open(TRASH_FILE, "w", encoding="utf-8") as f:
            if existing.strip():
                f.write(existing.rstrip() + "\n\n" + block + "\n")
            else:
                f.write(block + "\n")

    def _purge_old_trash(self):
        if not os.path.exists(TRASH_FILE):
            return
        raw = open(TRASH_FILE, encoding="utf-8").read().strip()
        if not raw:
            return
        today = date.today()
        kept: list[str] = []
        for block in re.split(r'(?=\*\*TRASH )', raw):
            block = block.strip()
            if not block:
                continue
            m = re.match(r'\*\*TRASH (\d{4}-\d{2}-\d{2})', block)
            if not m:
                continue
            try:
                d = dt.strptime(m.group(1), "%Y-%m-%d").date()
                if (today - d).days <= TRASH_DAYS:
                    kept.append(block)
            except ValueError:
                pass
        with open(TRASH_FILE, "w", encoding="utf-8") as f:
            f.write(("\n\n".join(kept) + "\n") if kept else "")

    def _delete_item(self, item: QTreeWidgetItem):
        if not self._confirm_delete(item):
            return

        self._write_trash(item)

        parent      = item.parent()
        grandparent = parent.parent() if parent else None
        great       = grandparent.parent() if grandparent else None

        if parent is None:
            lbl = item.data(0, Qt.ItemDataRole.UserRole)
            all_data.pop(lbl, None)

        elif grandparent is None:
            lbl   = parent.data(0, Qt.ItemDataRole.UserRole)
            pname = item.data(0, Qt.ItemDataRole.UserRole)
            if lbl in all_data:
                d_obj, persons = all_data[lbl]
                all_data[lbl]  = (d_obj, [p for p in persons if p["person"] != pname])

        elif great is None:
            lbl    = grandparent.data(0, Qt.ItemDataRole.UserRole)
            pname  = parent.data(0, Qt.ItemDataRole.UserRole)
            ttitle = item.data(0, Qt.ItemDataRole.UserRole)
            if lbl in all_data:
                for p in all_data[lbl][1]:
                    if p["person"] == pname:
                        p["tasks"] = [t for t in p["tasks"] if t["title"] != ttitle]

        else:
            lbl    = great.data(0, Qt.ItemDataRole.UserRole)
            pname  = grandparent.data(0, Qt.ItemDataRole.UserRole)
            ttitle = parent.data(0, Qt.ItemDataRole.UserRole)
            dtext  = item.data(0, Qt.ItemDataRole.UserRole)
            if lbl in all_data:
                for p in all_data[lbl][1]:
                    if p["person"] == pname:
                        for t in p["tasks"]:
                            if t["title"] == ttitle:
                                t["details"] = [d for d in t["details"] if d["text"] != dtext]

        self._refresh_tree()
        self._save_file(silent=True)

    def _sync_from_tree(self):
        """Reconstrói all_data a partir do estado atual da árvore (após drag-drop)."""
        new_data: dict = {}
        for i in range(self.tree.topLevelItemCount()):
            d_item = self.tree.topLevelItem(i)
            lbl    = d_item.data(0, Qt.ItemDataRole.UserRole)
            if lbl not in all_data:
                continue
            d_obj        = all_data[lbl][0]
            orig_persons = {p["person"]: p for p in all_data[lbl][1]}
            persons      = []
            for j in range(d_item.childCount()):
                p_item     = d_item.child(j)
                pname      = p_item.data(0, Qt.ItemDataRole.UserRole)
                orig_p     = orig_persons.get(pname, {})
                orig_tasks = {t["title"]: t for t in orig_p.get("tasks", [])}
                tasks      = []
                for k in range(p_item.childCount()):
                    t_item = p_item.child(k)
                    ttitle = t_item.data(0, Qt.ItemDataRole.UserRole)
                    orig_t = orig_tasks.get(ttitle, {})
                    details = [
                        {
                            "text":  t_item.child(l).data(0, Qt.ItemDataRole.UserRole),
                            "hours": t_item.child(l).data(0, ROLE_HOURS) or 0.0,
                            "done":  t_item.child(l).data(0, ROLE_DONE)  or False,
                        }
                        for l in range(t_item.childCount())
                    ]
                    tasks.append({
                        "title":   ttitle,
                        "via":     orig_t.get("via", ""),
                        "chamado": orig_t.get("chamado", ""),
                        "hours":   t_item.data(0, ROLE_HOURS) or 0.0,
                        "done":    t_item.data(0, ROLE_DONE)  or False,
                        "details": details,
                    })
                persons.append({"person": pname, "tasks": tasks})
            new_data[lbl] = (d_obj, persons)
        all_data.clear()
        all_data.update(new_data)
        self._save_file(silent=True)

    # ── reordenar (Ctrl+↑↓) ───────────────────────────────────────────────────

    def _move_item(self, item: QTreeWidgetItem, direction: int):
        parent      = item.parent()
        grandparent = parent.parent() if parent else None
        great       = grandparent.parent() if grandparent else None

        if parent is None:
            return  # datas são sempre ordenadas por data

        top = item
        while top.parent():
            top = top.parent()
        lbl = top.data(0, Qt.ItemDataRole.UserRole)
        if lbl not in all_data:
            return

        _, persons = all_data[lbl]
        pname = ttitle = dtext = None

        if grandparent is None:           # pessoa
            pname = item.data(0, Qt.ItemDataRole.UserRole)
            idx   = next((i for i, p in enumerate(persons) if p["person"] == pname), -1)
            if idx < 0:
                return
            new_idx = idx + direction
            if not (0 <= new_idx < len(persons)):
                return
            persons[idx], persons[new_idx] = persons[new_idx], persons[idx]

        elif great is None:               # tarefa
            pname  = parent.data(0, Qt.ItemDataRole.UserRole)
            ttitle = item.data(0, Qt.ItemDataRole.UserRole)
            for p in persons:
                if p["person"] == pname:
                    idx = next((i for i, t in enumerate(p["tasks"]) if t["title"] == ttitle), -1)
                    if idx < 0:
                        return
                    new_idx = idx + direction
                    if not (0 <= new_idx < len(p["tasks"])):
                        return
                    p["tasks"][idx], p["tasks"][new_idx] = p["tasks"][new_idx], p["tasks"][idx]
                    break

        else:                             # detalhe
            pname  = grandparent.data(0, Qt.ItemDataRole.UserRole)
            ttitle = parent.data(0, Qt.ItemDataRole.UserRole)
            dtext  = item.data(0, Qt.ItemDataRole.UserRole)
            for p in persons:
                if p["person"] == pname:
                    for t in p["tasks"]:
                        if t["title"] == ttitle:
                            idx = next(
                                (i for i, d in enumerate(t["details"]) if d["text"] == dtext), -1
                            )
                            if idx < 0:
                                return
                            new_idx = idx + direction
                            if not (0 <= new_idx < len(t["details"])):
                                return
                            t["details"][idx], t["details"][new_idx] = (
                                t["details"][new_idx], t["details"][idx]
                            )
                            break
                    break

        self._refresh_tree()
        self._save_file(silent=True)
        self._reselect(lbl, pname, ttitle, dtext)

    def _reselect(self, lbl: str, pname: str | None, ttitle: str | None, dtext: str | None):
        """Após um refresh, reposiciona o foco no item equivalente."""
        for i in range(self.tree.topLevelItemCount()):
            d_item = self.tree.topLevelItem(i)
            if d_item.data(0, Qt.ItemDataRole.UserRole) != lbl:
                continue
            if pname is None:
                self.tree.setCurrentItem(d_item)
                return
            for j in range(d_item.childCount()):
                p_item = d_item.child(j)
                if p_item.data(0, Qt.ItemDataRole.UserRole) != pname:
                    continue
                if ttitle is None:
                    self.tree.setCurrentItem(p_item)
                    return
                for k in range(p_item.childCount()):
                    t_item = p_item.child(k)
                    if t_item.data(0, Qt.ItemDataRole.UserRole) != ttitle:
                        continue
                    if dtext is None:
                        self.tree.setCurrentItem(t_item)
                        return
                    for l in range(t_item.childCount()):
                        det_item = t_item.child(l)
                        if det_item.data(0, Qt.ItemDataRole.UserRole) == dtext:
                            self.tree.setCurrentItem(det_item)
                            return

    def _on_tab_changed(self, index: int):
        if index == 1:
            self._refresh_summary()
        elif index == 2:
            # atualizar estado dos controles ao entrar na aba
            self._on_settings_mode_toggled()

    def _refresh_summary(self):
        """Reconstrói a árvore de resumo (aba Resumo)."""
        self._sum_tree.clear()
        p = self._palette

        for lbl, (d_obj, persons) in sorted(all_data.items(), key=lambda x: x[1][0]):
            used   = _date_hours(persons)
            budget = _day_budget(d_obj)
            d_item = QTreeWidgetItem([_display_label(lbl)])
            d_item.setData(0, ROLE_USED, used)
            d_item.setData(0, ROLE_BUDGET, budget)
            d_item.setData(0, Qt.ItemDataRole.UserRole, lbl)
            d_item.setForeground(0, QColor(p["AMBER"]))
            d_item.setFont(0, QFont("Segoe UI", 11, QFont.Weight.Bold))
            self._sum_tree.addTopLevelItem(d_item)
            d_item.setExpanded(True)

            for person in persons:
                ph     = _person_hours(person)
                ph_str = f"   {_fmt_hhmm(ph)}" if ph > 0 else ""
                is_myself = _is_myself(person["person"])
                has_pending = any(
                    not t.get("done", True) or any(not d.get("done", True) for d in t.get("details", []))
                    for t in person.get("tasks", [])
                )
                if is_myself:
                    pfx = "★"
                elif has_pending:
                    pfx = "●"
                else:
                    pfx = "/"
                p_item = QTreeWidgetItem([f"{pfx} {person['person']}{ph_str}"])
                p_item.setData(0, Qt.ItemDataRole.UserRole, person["person"])
                p_item.setForeground(0, QColor(p["PERSON"]))
                p_item.setFont(0, QFont("Segoe UI", 10, QFont.Weight.DemiBold))
                d_item.addChild(p_item)
                p_item.setExpanded(False)

                for task in person["tasks"]:
                    is_done = task.get("done", True)
                    eff_h   = _effective_task_hours(task)
                    via_suf = _task_via_suffix(task)
                    via_str = f"  ·  {via_suf.lstrip(' | ')}" if via_suf else ""
                    h_str   = f"  ·  {_fmt_hhmm(eff_h)}" if eff_h else ""
                    prefix  = "" if is_done else "● "
                    t_item  = QTreeWidgetItem([f"{prefix}{task['title']}{via_str}{h_str}"])
                    t_item.setData(0, Qt.ItemDataRole.UserRole, task["title"])
                    t_item.setForeground(0, QColor(p["MUTED"] if is_done else p["AMBER"]))
                    p_item.addChild(t_item)
                    t_item.setExpanded(True)

                    for det in task["details"]:
                        det_done = det.get("done", True)
                        dh       = det.get("hours", 0.0)
                        dh_str   = f"  ·  {_fmt_hhmm(dh)}" if dh else ""
                        dpfx     = "" if det_done else "● "
                        det_item = QTreeWidgetItem([f"  {dpfx}{det['text']}{dh_str}"])
                        det_item.setData(0, Qt.ItemDataRole.UserRole, det["text"])
                        f_det = QFont("Segoe UI", 9)
                        f_det.setItalic(True)
                        det_item.setFont(0, f_det)
                        det_item.setForeground(0, QColor(p["MUTED"] if det_done else p["AMBER"]))
                        t_item.addChild(det_item)

        if self._sum_search.text().strip():
            self._filter_summary(self._sum_search.text())

    def _filter_summary(self, query: str):
        q = query.strip().lower()
        for i in range(self._sum_tree.topLevelItemCount()):
            self._filter_item(self._sum_tree.topLevelItem(i), q)

    def _filter_item(self, item: QTreeWidgetItem, q: str) -> bool:
        """Retorna True se item ou algum descendente bate com q."""
        text       = (item.data(0, Qt.ItemDataRole.UserRole) or "").lower()
        self_match = not q or q in text
        child_vis  = False
        for i in range(item.childCount()):
            if self._filter_item(item.child(i), q):
                child_vis = True
        visible = self_match or child_vis
        item.setHidden(not visible)
        if visible and q:
            item.setExpanded(True)
        return visible

    def _refresh_hours_summary(self):
        """Reconstrói o painel de progresso do dia atual."""
        while self._summary_layout.count():
            child = self._summary_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        p = self._palette
        current_lbl = self._current_label()

        if current_lbl not in all_data:
            return

        # apenas o dia selecionado
        for lbl, (d_obj, persons) in [(current_lbl, all_data[current_lbl])]:
            used   = _date_hours(persons)
            budget = _day_budget(d_obj)

            # Modo "sem meta": mostra apenas horas realizadas, sem barra de %
            if _config["hours_mode"] == "none" or budget <= 0:
                row = QWidget()
                row.setStyleSheet("background: transparent;")
                row_lay = QHBoxLayout(row)
                row_lay.setContentsMargins(0, 0, 0, 0)
                row_lay.setSpacing(8)

                date_lbl = QLabel(_display_label(lbl))
                date_lbl.setFixedWidth(46)
                date_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                date_lbl.setStyleSheet(
                    f"color: {p['AMBER']}; border: none;"
                )
                row_lay.addWidget(date_lbl)

                hours_lbl = QLabel(f"{_fmt_hhmm(used)} {_t('hours_done')}")
                hours_lbl.setStyleSheet(
                    f"color: {p['MUTED']}; font-size: 9pt; border: none;"
                )
                hours_lbl.setAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
                row_lay.addStretch()
                row_lay.addWidget(hours_lbl)

                self._summary_layout.addWidget(row)
                continue

            pct    = min(used / budget, 1.0) if budget > 0 else 0.0
            is_cur = (lbl == current_lbl)

            row = QWidget()
            row.setStyleSheet("background: transparent;")
            row_lay = QHBoxLayout(row)
            row_lay.setContentsMargins(0, 0, 0, 0)
            row_lay.setSpacing(8)

            date_lbl = QLabel(lbl)
            date_lbl.setFixedWidth(46)
            date_lbl.setFont(QFont("Segoe UI", 9,
                                   QFont.Weight.Bold if is_cur else QFont.Weight.Normal))
            date_lbl.setStyleSheet(
                f"color: {p['AMBER'] if is_cur else p['MUTED']}; border: none;"
            )
            row_lay.addWidget(date_lbl)

            if _config.get("bar_person_colors") and persons:
                segments = [
                    (_person_hours(person), _PERSON_COLORS[i % len(_PERSON_COLORS)])
                    for i, person in enumerate(persons)
                    if _person_hours(person) > 0
                ]
                bar = PersonBar(segments, budget, p["BORDER"])
            else:
                bar = QProgressBar()
                bar.setMaximum(1000)
                bar.setValue(int(pct * 1000))
                bar.setTextVisible(False)
                bar.setFixedHeight(6)
                if pct >= 1.0:
                    bar_color = "#22c55e"
                elif pct >= 0.8:
                    bar_color = p["AMBER"]
                else:
                    bar_color = p["ACCENT"]
                bar.setStyleSheet(f"""
                    QProgressBar {{
                        background: {p['BORDER']}; border-radius: 3px; border: none;
                    }}
                    QProgressBar::chunk {{
                        background: {bar_color}; border-radius: 3px;
                    }}
                """)
            row_lay.addWidget(bar, stretch=1)

            hours_lbl = QLabel(f"{_fmt_hhmm(used)} / {_fmt_hhmm(budget)}")
            hours_lbl.setStyleSheet(
                f"color: {p['MUTED']}; font-size: 9pt; border: none;"
            )
            hours_lbl.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            row_lay.addWidget(hours_lbl)

            self._summary_layout.addWidget(row)

    def _save_file(self, silent: bool = False):
        if not all_data:
            if not silent:
                QMessageBox.warning(self, _t("attention"), _t("no_tasks"))
            return

        sorted_blocks = sorted(all_data.values(), key=lambda x: x[0])
        content = "\n\n".join(format_block(d_obj, persons) for d_obj, persons in sorted_blocks)
        with open("daily.txt", "w", encoding="utf-8") as f:
            f.write(content + "\n")
        if not silent:
            QMessageBox.information(self, _t("saved_title"), _t("saved_msg"))

    def _download_txt(self):
        if not all_data:
            QMessageBox.warning(self, _t("attention"), _t("download_no_data"))
            return
        dest, _ = QFileDialog.getSaveFileName(
            self, _t("download_title"), "daily.txt", "Text files (*.txt)"
        )
        if not dest:
            return
        src = "daily.txt"
        if os.path.exists(src):
            shutil.copy2(src, dest)
        else:
            # arquivo ainda não foi salvo em disco — gera o conteúdo agora
            sorted_blocks = sorted(all_data.values(), key=lambda x: x[0])
            content = "\n\n".join(format_block(d, p) for d, p in sorted_blocks)
            with open(dest, "w", encoding="utf-8") as f:
                f.write(content + "\n")
        QMessageBox.information(self, _t("saved_title"), _t("download_ok"))

    def _toggle_raw_view(self):
        raw_on = self._btn_raw.isChecked()
        self._btn_raw.setStyleSheet(
            _ss_btn(self._palette) if raw_on else _ss_btn_gray(self._palette)
        )
        if raw_on:
            self._sum_search.setEnabled(False)
            self._sum_tree.hide()
            sorted_blocks = sorted(all_data.values(), key=lambda x: x[0])
            content = "\n\n".join(
                format_block(d, p) for d, p in sorted_blocks
            ) if all_data else ""
            self._sum_raw.setPlainText(content)
            self._sum_raw.show()
        else:
            self._sum_search.setEnabled(True)
            self._sum_raw.hide()
            self._sum_tree.show()


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = DailyApp()
    win.show()
    sys.exit(app.exec())
