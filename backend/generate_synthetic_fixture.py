"""
Generate synthetic 30-student fixture for CCDP testing.
All student names, roll numbers, phone numbers, and details are 100% fictional.
"""
import os
import json
import openpyxl

INVENTED_STUDENTS = [
    {"name": "Aarav Sharma", "enrolment": "CCDP-2024-001", "college": "Apex Institute of Arts & Science", "placed": True, "company": "Kauvery Hospital - Tennur", "role": "Patient Care Coordinator", "salary": "Rs. 18,000 / month", "salary_num": 18000, "typing": 35, "shirt": "38", "trouser": "32", "tie": "Yes", "shoe": 8},
    {"name": "Diya Patel", "enrolment": "CCDP-2024-002", "college": "City College of Health Sciences", "placed": True, "company": "Kauvery Hospital - Cantonment", "role": "Front Office Executive", "salary": "Rs. 16,500 / month", "salary_num": 16500, "typing": 32, "shirt": "M", "trouser": "30", "tie": "Yes", "shoe": 6},
    {"name": "Rohan Iyer", "enrolment": "CCDP-2024-003", "college": "St. Joseph Arts College", "placed": True, "company": "Kauvery Hospital - Heart City", "role": "Billing & TPA Executive", "salary": "Rs. 19,000 / month", "salary_num": 19000, "typing": 42, "shirt": "40", "trouser": "34", "tie": "Yes", "shoe": 9},
    {"name": "Ananya Verma", "enrolment": "CCDP-2024-004", "college": "National College", "placed": True, "company": "Kauvery Hospital - Chennai", "role": "Patient Care Coordinator", "salary": "Rs. 17,500 / month", "salary_num": 17500, "typing": 28, "shirt": "S", "trouser": "28", "tie": "Yes", "shoe": 5},
    {"name": "Vikram Malhotra", "enrolment": "CCDP-2024-005", "college": "Bishop Heber College", "placed": True, "company": "Kauvery Hospital - Salem", "role": "Hospital Operations Trainee", "salary": "Rs. 20,000 / month", "salary_num": 20000, "typing": 38, "shirt": "42", "trouser": "36", "tie": "Yes", "shoe": 10},
    {"name": "Pooja Sundaram", "enrolment": "CCDP-2024-006", "college": "Holy Cross College", "placed": True, "company": "Kauvery Hospital - Hosur", "role": "Front Office Executive", "salary": "Rs. 16,000 / month", "salary_num": 16000, "typing": 30, "shirt": "M", "trouser": "30", "tie": "Yes", "shoe": 6},
    {"name": "Karthik Raja", "enrolment": "CCDP-2024-007", "college": "Jamal Mohamed College", "placed": True, "company": "Joy Alukkas Healthcare", "role": "Customer Experience Executive", "salary": "Rs. 15,000 / month", "salary_num": 15000, "typing": 26, "shirt": "38", "trouser": "32", "tie": "Yes", "shoe": 8},
    {"name": "Meera Krishnan", "enrolment": "CCDP-2024-008", "college": "Cauvery College for Women", "placed": True, "company": "Kauvery Hospital - Tennur", "role": "Medical Records Assistant", "salary": "Rs. 17,000 / month", "salary_num": 17000, "typing": 34, "shirt": "M", "trouser": "30", "tie": "Yes", "shoe": 6},
    {"name": "Siddharth Nair", "enrolment": "CCDP-2024-009", "college": "Urumu Dhanalakshmi College", "placed": True, "company": "Hamsa Rehabilitation Center", "role": "Healthcare IT Assistant", "salary": "Rs. 18,500 / month", "salary_num": 18500, "typing": 40, "shirt": "40", "trouser": "34", "tie": "Yes", "shoe": 9},
    {"name": "Sneha Ranganathan", "enrolment": "CCDP-2024-010", "college": "Seethalakshmi Ramaswami College", "placed": True, "company": "Kauvery Hospital - Cantonment", "role": "Patient Care Coordinator", "salary": "Rs. 16,500 / month", "salary_num": 16500, "typing": 29, "shirt": "S", "trouser": "28", "tie": "Yes", "shoe": 5},
    {"name": "Aditya Menon", "enrolment": "CCDP-2024-011", "college": "National College", "placed": True, "company": "Kauvery Hospital - Heart City", "role": "Hospital Operations Trainee", "salary": "Rs. 19,500 / month", "salary_num": 19500, "typing": 36, "shirt": "40", "trouser": "34", "tie": "Yes", "shoe": 9},
    {"name": "Lavanya Balan", "enrolment": "CCDP-2024-012", "college": "Holy Cross College", "placed": True, "company": "Kauvery Hospital - Chennai", "role": "Front Office Executive", "salary": "Rs. 17,000 / month", "salary_num": 17000, "typing": 33, "shirt": "M", "trouser": "30", "tie": "Yes", "shoe": 6},
    {"name": "Harish Venkatesh", "enrolment": "CCDP-2024-013", "college": "Bishop Heber College", "placed": True, "company": "Kauvery Hospital - Tennur", "role": "Billing & TPA Executive", "salary": "Rs. 18,000 / month", "salary_num": 18000, "typing": 37, "shirt": "42", "trouser": "36", "tie": "Yes", "shoe": 10},
    {"name": "Divya Nambiar", "enrolment": "CCDP-2024-014", "college": "Cauvery College for Women", "placed": True, "company": "Kauvery Hospital - Salem", "role": "Pharmacy Supply Assistant", "salary": "Rs. 15,500 / month", "salary_num": 15500, "typing": 25, "shirt": "S", "trouser": "28", "tie": "Yes", "shoe": 5},
    {"name": "Pranav Deshmukh", "enrolment": "CCDP-2024-015", "college": "St. Joseph College", "placed": True, "company": "Kauvery Hospital - Hosur", "role": "Patient Care Coordinator", "salary": "Rs. 17,000 / month", "salary_num": 17000, "typing": 31, "shirt": "38", "trouser": "32", "tie": "Yes", "shoe": 8},
    {"name": "Kavitha Murugan", "enrolment": "CCDP-2024-016", "college": "Seethalakshmi Ramaswami College", "placed": True, "company": "Joy Alukkas Healthcare", "role": "Customer Experience Executive", "salary": "Rs. 14,500 / month", "salary_num": 14500, "typing": 24, "shirt": "M", "trouser": "30", "tie": "Yes", "shoe": 6},
    {"name": "Gautam Pillai", "enrolment": "CCDP-2024-017", "college": "Jamal Mohamed College", "placed": True, "company": "Hamsa Rehabilitation Center", "role": "Healthcare IT Assistant", "salary": "Rs. 18,000 / month", "salary_num": 18000, "typing": 39, "shirt": "40", "trouser": "34", "tie": "Yes", "shoe": 9},
    {"name": "Shreya Chawla", "enrolment": "CCDP-2024-018", "college": "Holy Cross College", "placed": True, "company": "Kauvery Hospital - Tennur", "role": "Front Office Executive", "salary": "Rs. 16,500 / month", "salary_num": 16500, "typing": 32, "shirt": "S", "trouser": "28", "tie": "Yes", "shoe": 5},
    {"name": "Naveen Raghavan", "enrolment": "CCDP-2024-019", "college": "Apex Institute of Arts & Science", "placed": True, "company": "Kauvery Hospital - Cantonment", "role": "Hospital Operations Trainee", "salary": "Rs. 19,000 / month", "salary_num": 19000, "typing": 35, "shirt": "40", "trouser": "34", "tie": "Yes", "shoe": 9},
    {"name": "Rithika Selvam", "enrolment": "CCDP-2024-020", "college": "Cauvery College for Women", "placed": True, "company": "Kauvery Hospital - Chennai", "role": "Patient Care Coordinator", "salary": "Rs. 17,500 / month", "salary_num": 17500, "typing": 30, "shirt": "M", "trouser": "30", "tie": "Yes", "shoe": 6},
    {"name": "Manoj Kumar", "enrolment": "CCDP-2024-021", "college": "Bishop Heber College", "placed": True, "company": "Kauvery Hospital - Heart City", "role": "Billing & TPA Executive", "salary": "Rs. 17,500 / month", "salary_num": 17500, "typing": 33, "shirt": "38", "trouser": "32", "tie": "Yes", "shoe": 8},
    {"name": "Priyanka Chandran", "enrolment": "CCDP-2024-022", "college": "Holy Cross College", "placed": True, "company": "Kauvery Hospital - Salem", "role": "Medical Records Assistant", "salary": "Rs. 16,000 / month", "salary_num": 16000, "typing": 28, "shirt": "S", "trouser": "28", "tie": "Yes", "shoe": 5},
    {"name": "Abhishek Natarajan", "enrolment": "CCDP-2024-023", "college": "National College", "placed": True, "company": "Kauvery Hospital - Hosur", "role": "Patient Care Coordinator", "salary": "Rs. 16,500 / month", "salary_num": 16500, "typing": 29, "shirt": "42", "trouser": "36", "tie": "Yes", "shoe": 10},
    {"name": "Swetha Rajan", "enrolment": "CCDP-2024-024", "college": "Seethalakshmi Ramaswami College", "placed": True, "company": "Joy Alukkas Healthcare", "role": "Customer Experience Executive", "salary": "Rs. 15,000 / month", "salary_num": 15000, "typing": 27, "shirt": "M", "trouser": "30", "tie": "Yes", "shoe": 6},
    {"name": "Arjun Swaminathan", "enrolment": "CCDP-2024-025", "college": "St. Joseph College", "placed": True, "company": "Kauvery Hospital - Tennur", "role": "Hospital Operations Trainee", "salary": "Rs. 18,500 / month", "salary_num": 18500, "typing": 34, "shirt": "40", "trouser": "34", "tie": "Yes", "shoe": 9},
    {"name": "Deepika Ganesan", "enrolment": "CCDP-2024-026", "college": "Cauvery College for Women", "placed": True, "company": "Kauvery Hospital - Cantonment", "role": "Front Office Executive", "salary": "Rs. 16,000 / month", "salary_num": 16000, "typing": 26, "shirt": "S", "trouser": "28", "tie": "Yes", "shoe": 5},
    {"name": "Vishal Sundar", "enrolment": "CCDP-2024-027", "college": "Jamal Mohamed College", "placed": True, "company": "Hamsa Rehabilitation Center", "role": "Healthcare IT Assistant", "salary": "Rs. 17,500 / month", "salary_num": 17500, "typing": 31, "shirt": "38", "trouser": "32", "tie": "Yes", "shoe": 8},
    {"name": "Tara Madhavan", "enrolment": "CCDP-2024-028", "college": "Holy Cross College", "placed": False, "company": None, "role": None, "salary": None, "salary_num": 0, "typing": 22, "shirt": "M", "trouser": "30", "tie": "Yes", "shoe": 6},
    {"name": "Dinesh Karthik", "enrolment": "CCDP-2024-029", "college": "National College", "placed": False, "company": None, "role": None, "salary": None, "salary_num": 0, "typing": 20, "shirt": "38", "trouser": "32", "tie": "Yes", "shoe": 8},
    {"name": "Bhavani Shankar", "enrolment": "CCDP-2024-030", "college": "Seethalakshmi Ramaswami College", "placed": False, "company": None, "role": None, "salary": None, "salary_num": 0, "typing": 19, "shirt": "S", "trouser": "28", "tie": "Yes", "shoe": 5},
]

def generate_fixtures(out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    xlsx_path = os.path.join(out_dir, "synthetic_ccdp_30.xlsx")
    json_path = os.path.join(out_dir, "synthetic_ccdp_30.json")

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    # 1. Profile Sheet
    ws_profile = wb.create_sheet(title="Profile")
    profile_headers = ["S.No", "Student Name", "Enrolment No.", "Gender", "Date of Birth", "Qualification", "College", "Mobile No", "Email ID"]
    ws_profile.append(profile_headers)
    for idx, s in enumerate(INVENTED_STUDENTS, 1):
        gender = "Female" if idx % 2 == 0 else "Male"
        ws_profile.append([idx, s["name"], s["enrolment"], gender, "2002-05-15", "B.Sc", s["college"], f"98765432{idx:02d}", f"student{idx}@example.com"])

    # 2. Assessment Sheet (2-row header: subject name then Out of N)
    ws_assess = wb.create_sheet(title="Assessment")
    row1 = ["S.No", "Student Name", "Basic English", "MS Word", "MS Excel", "Hospital Administration", "Healthcare Operations", "Total"]
    row2 = ["", "", "Out of 50", "Out of 30", "Out of 45", "Out of 70", "Out of 70", "Out of 265"]
    ws_assess.append(row1)
    ws_assess.append(row2)

    # 30 students:
    # 1-5: top distinction
    # 6-18: placement ready
    # 19-24: placement ready
    # 25-27: moderate prep
    # 28-30: critical remediation / needs prep
    for idx, s in enumerate(INVENTED_STUDENTS, 1):
        if idx <= 5:
            eng, word, excel, hosp, ops = 46, 28, 42, 64, 65
        elif idx <= 15:
            eng, word, excel, hosp, ops = 40, 24, 36, 54, 55
        elif idx <= 24:
            eng, word, excel, hosp, ops = 34, 20, 30, 44, 45
        elif idx <= 27:
            eng, word, excel, hosp, ops = 26, 15, 23, 36, 35
        else:
            eng, word, excel, hosp, ops = 18, 10, 15, 25, 24
        total = eng + word + excel + hosp + ops
        ws_assess.append([idx, s["name"], eng, word, excel, hosp, ops, total])

    # 3. Skill Matrix Sheet
    ws_skill = wb.create_sheet(title="Skill")
    skill_headers = ["S.No", "Student Name", "Communication Skills (Out of 10)", "Analytical Skills (Out of 10)", "Problem Solving (Out of 10)", "Leadership Skills (Out of 10)", "Typing Speed (WPM)"]
    ws_skill.append(skill_headers)
    for idx, s in enumerate(INVENTED_STUDENTS, 1):
        if idx <= 5:
            comm, anal, prob, lead = 9.0, 9.0, 8.5, 9.0
        elif idx <= 15:
            comm, anal, prob, lead = 8.0, 7.5, 7.5, 8.0
        elif idx <= 24:
            comm, anal, prob, lead = 7.0, 6.5, 6.5, 7.0
        elif idx <= 27:
            comm, anal, prob, lead = 5.5, 5.0, 5.0, 5.5
        else:
            comm, anal, prob, lead = 3.5, 3.5, 3.0, 3.5
        ws_skill.append([idx, s["name"], comm, anal, prob, lead, s["typing"]])

    # 4. Attendance Sheet (50 days of P/A)
    ws_att = wb.create_sheet(title="Attendance")
    att_headers = ["S.No", "Student Name"] + [f"Day {d}" for d in range(1, 51)]
    ws_att.append(att_headers)
    for idx, s in enumerate(INVENTED_STUDENTS, 1):
        if idx <= 20:
            absent_count = 1 if idx % 3 == 0 else 0
        elif idx <= 27:
            absent_count = 5
        else:
            absent_count = 14
        days = []
        for d in range(1, 51):
            if d <= absent_count:
                days.append("A")
            else:
                days.append("P")
        ws_att.append([idx, s["name"]] + days)

    # 5. Placement Sheet
    ws_place = wb.create_sheet(title="Placement")
    place_headers = ["S.No", "Student Name", "Designation", "Organization", "Salary / Package"]
    ws_place.append(place_headers)
    for idx, s in enumerate(INVENTED_STUDENTS, 1):
        if s["placed"]:
            ws_place.append([idx, s["name"], s["role"], s["company"], s["salary"]])
        else:
            ws_place.append([idx, s["name"], "", "", ""])

    # 6. Uniform Sheet (Compliance)
    ws_uniform = wb.create_sheet(title="Uniform")
    uni_headers = ["S.No", "Student Name", "Shirt", "Trouser", "Tie", "Shoe Size"]
    ws_uniform.append(uni_headers)
    for idx, s in enumerate(INVENTED_STUDENTS, 1):
        ws_uniform.append([idx, s["name"], s["shirt"], s["trouser"], s["tie"], s["shoe"]])

    wb.save(xlsx_path)
    print(f"Generated synthetic Excel fixture: {xlsx_path}")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(INVENTED_STUDENTS, f, indent=2)
    print(f"Generated synthetic JSON fixture: {json_path}")

if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests", "fixtures")
    generate_fixtures(out_dir)
