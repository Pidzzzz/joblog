import os
from datetime import date, timedelta
from fpdf import FPDF

from src import storage
from src.ranks import get_rank, get_xp_progress, get_streak_info, format_progress_bar


class JournalPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, "SOLO LEVELING JOURNAL", new_x="LMARGIN", new_y="NEXT", align="C")
        self.set_font("Helvetica", "", 10)
        self.cell(0, 6, "Personal Activity Report", new_x="LMARGIN", new_y="NEXT", align="C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


def generate_pdf(entries=None, start_date=None, end_date=None, output_path=None):
    if entries is None:
        entries = storage.get_all_entries()

    if start_date:
        entries = [e for e in entries if e["date"] >= start_date]
    if end_date:
        entries = [e for e in entries if e["date"] <= end_date]

    if not output_path:
        output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "journal_report.pdf")

    pdf = JournalPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    all_entries = storage.get_all_entries()
    total = len(all_entries)
    stats = storage.get_stats()
    rank = get_rank(total)
    xp = get_xp_progress(total)
    streak = get_streak_info(all_entries)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Hunter Status", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)

    pdf.cell(0, 6, f"Rank: {rank['rank']} - {rank['title']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Total Entries: {total}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Active Days: {stats['days']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Current Streak: {streak['streak']} days", new_x="LMARGIN", new_y="NEXT")

    if xp["next"]:
        bar = format_progress_bar(xp["percent"])
        pdf.cell(0, 6, f"Progress to {xp['next']['rank']}: {bar} {xp['percent']}%", new_x="LMARGIN", new_y="NEXT")

    if streak["milestone"]:
        m = streak["milestone"]
        pdf.cell(0, 6, f"Streak Title: {m['title']} ({m['days']} days)", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(5)

    if start_date or end_date:
        sd = start_date or "Start"
        ed = end_date or "End"
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, f"Report Period: {sd} to {ed}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 6, f"Entries in period: {len(entries)}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Activity Log", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    dates = {}
    for e in entries:
        d = e["date"]
        if d not in dates:
            dates[d] = []
        dates[d].append(e)

    for d in sorted(dates.keys(), reverse=True):
        day_entries = dates[d]

        pdf.set_font("Helvetica", "B", 11)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 8, f"  {d}  ({len(day_entries)} entries)", new_x="LMARGIN", new_y="NEXT", fill=True)
        pdf.ln(2)

        pdf.set_font("Helvetica", "", 9)
        for e in day_entries:
            time_str = e.get("time", "")[:5]
            text = e["text"]

            safe_text = text.encode("latin-1", errors="replace").decode("latin-1")
            pdf.cell(0, 5, f"    [{time_str}]  {safe_text}", new_x="LMARGIN", new_y="NEXT")

        pdf.ln(3)

    if not entries:
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(0, 10, "No entries found for this period.", new_x="LMARGIN", new_y="NEXT")

    pdf.output(output_path)
    return output_path
