from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO


def calculate_percentage(marks_obtained: float, max_marks: float) -> float:
    if max_marks is None or max_marks == 0:
        return 0.0
    return round((marks_obtained / max_marks) * 100.0, 2)


def calculate_grade(percentage: float) -> str:
    if percentage >= 90:
        return 'A+'
    if percentage >= 80:
        return 'A'
    if percentage >= 70:
        return 'B'
    if percentage >= 60:
        return 'C'
    return 'F'


def generate_report_pdf(student, subject_rows, total_marks, total_max_marks, overall_percentage, overall_grade, attendance_percentage: float) -> BytesIO:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 1 * inch

    # Header
    c.setFont("Helvetica-Bold", 18)
    c.drawString(1 * inch, y, "Report Card")
    y -= 0.35 * inch

    c.setFont("Helvetica", 11)
    c.drawString(1 * inch, y, f"Name: {student.name}")
    y -= 0.22 * inch
    c.drawString(1 * inch, y, f"Student ID: {student.registration_number or student.id}")
    y -= 0.22 * inch

    # Attendance
    c.drawString(1 * inch, y, f"Attendance: {round(attendance_percentage, 2)}%")
    y -= 0.35 * inch

    # Table header
    c.setFont("Helvetica-Bold", 11)
    c.drawString(1 * inch, y, "Subject")
    c.drawString(3.4 * inch, y, "Exam Type")
    c.drawRightString(5.0 * inch, y, "Marks")
    c.drawRightString(6.2 * inch, y, "Max")
    c.drawRightString(7.2 * inch, y, "%")
    y -= 0.18 * inch
    c.setStrokeColor(colors.black)
    c.line(1 * inch, y, 7.4 * inch, y)
    y -= 0.12 * inch
    c.setFont("Helvetica", 10)

    for row in subject_rows:
        if y < 1 * inch:
            c.showPage()
            y = height - 1 * inch
            c.setFont("Helvetica-Bold", 11)
            c.drawString(1 * inch, y, "Subject")
            c.drawString(3.4 * inch, y, "Exam Type")
            c.drawRightString(5.0 * inch, y, "Marks")
            c.drawRightString(6.2 * inch, y, "Max")
            c.drawRightString(7.2 * inch, y, "%")
            y -= 0.18 * inch
            c.line(1 * inch, y, 7.4 * inch, y)
            y -= 0.12 * inch
            c.setFont("Helvetica", 10)

        c.drawString(1 * inch, y, row['subject_name'][:25])
        c.drawString(3.4 * inch, y, row['exam_type'][:16])
        c.drawRightString(5.0 * inch, y, f"{row['marks_obtained']}")
        c.drawRightString(6.2 * inch, y, f"{row['max_marks']}")
        c.drawRightString(7.2 * inch, y, f"{row['percentage']}")
        y -= 0.18 * inch

        if row.get('remarks'):
            c.setFillColor(colors.grey)
            c.setFont("Helvetica-Oblique", 9)
            c.drawString(1 * inch, y, f"Remarks: {row['remarks'][:80]}")
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 10)
            y -= 0.15 * inch

    y -= 0.2 * inch
    c.line(1 * inch, y, 7.4 * inch, y)
    y -= 0.25 * inch

    # Totals
    c.setFont("Helvetica-Bold", 11)
    c.drawString(1 * inch, y, "Totals")
    c.drawRightString(5.0 * inch, y, f"{total_marks}")
    c.drawRightString(6.2 * inch, y, f"{total_max_marks}")
    c.drawRightString(7.2 * inch, y, f"{overall_percentage}")
    y -= 0.35 * inch

    # Grade
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, y, f"Overall Grade: {overall_grade}")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


