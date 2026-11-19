import os
import sys
import pypdfium2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdf_generator import generate_student_report_pdf, load_all_students_from_excel

out_dir = "pdf_previews/verification"
os.makedirs(out_dir, exist_ok=True)
os.makedirs("output_reports", exist_ok=True)

per_student, batch_metrics = load_all_students_from_excel()

# 1. Student A: Complete Data (Jayasree A)
jayasree = per_student.get("jayasree a")
print("Generating Student A (Jayasree A)...")
pdf_a = generate_student_report_pdf(jayasree, batch_name="2023", batch_metrics=batch_metrics)
with open("output_reports/Jayasree_A_Report.pdf", "wb") as f:
    f.write(pdf_a)

doc_a = pypdfium2.PdfDocument(pdf_a)
for i, p in enumerate(doc_a):
    p.render(scale=110/72).to_pil().save(f"{out_dir}/student_a_page_{i+1}.png")
print("Student A pages rendered:", len(doc_a))

# 2. Student B: Missing Skills & Placement details (Abinaya M with simulated missing skills/placement)
print("Generating Student B (Abinaya M with missing details)...")
abinaya_rec = dict(per_student.get("abinaya m"))
# Simulate missing skill matrix, college, and placement per test requirement (b)
abinaya_rec["skill_scores"] = {}
abinaya_rec["placement"] = {}
if "profile" in abinaya_rec:
    abinaya_rec["profile"] = dict(abinaya_rec["profile"])
    abinaya_rec["profile"]["College Name"] = None
    abinaya_rec["profile"]["College"] = None

pdf_b = generate_student_report_pdf(abinaya_rec, batch_name="2023", batch_metrics=batch_metrics)
with open("output_reports/Abinaya_M_Missing_Report.pdf", "wb") as f:
    f.write(pdf_b)

doc_b = pypdfium2.PdfDocument(pdf_b)
for i, p in enumerate(doc_b):
    p.render(scale=110/72).to_pil().save(f"{out_dir}/student_b_page_{i+1}.png")
print("Student B pages rendered:", len(doc_b))

# 3. Student C: Very long names / college / designation text
print("Generating Student C (Long text edge case)...")
long_rec = dict(jayasree)
long_rec["display_name"] = "Dr. Karishma Nilofer Arulmozhi Varman"
long_rec["profile"] = dict(long_rec["profile"])
long_rec["profile"]["College Name"] = "Sri Manakula Vinayagar Engineering and Medical Research Institute for Women Autonomous Campus"
long_rec["profile"]["Qualification"] = "Master of Science in Biomedical Engineering & Healthcare Systems"
long_rec["profile"]["District"] = "Tiruchirappalli South District"
long_rec["profile"]["District 2"] = "Thanjavur North District"
long_rec["placement"] = dict(long_rec["placement"])
long_rec["placement"]["Designation"] = "Chief Senior Hospital Outpatient Department (OPD) & Patient Relations Coordinating Executive Trainee"
long_rec["placement"]["Organization"] = "Kauvery Hospital & Research Institute for Super Specialties, Trichy Cantonment"

pdf_c = generate_student_report_pdf(long_rec, batch_name="2023", batch_metrics=batch_metrics)
with open("output_reports/Long_Student_Report.pdf", "wb") as f:
    f.write(pdf_c)

doc_c = pypdfium2.PdfDocument(pdf_c)
for i, p in enumerate(doc_c):
    p.render(scale=110/72).to_pil().save(f"{out_dir}/student_c_page_{i+1}.png")
print("Student C pages rendered:", len(doc_c))
print("Verification generation complete!")
