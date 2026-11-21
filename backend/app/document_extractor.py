"""Intelligent Document Classifier and Information Extractor for Orqentra.

Automatically inspects document text and extracts 50+ applicant profile attributes
from Indian and international documents (Aadhaar, PAN, Voter ID, Passport, Driving License,
Educational Certificates, Mark Sheets, Salary Slips, Resumes, etc.).
"""
from __future__ import annotations

import re
from typing import Any

INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa",
    "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala",
    "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland",
    "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal", "Delhi", "Jammu and Kashmir",
    "Puducherry", "Chandigarh", "Ladakh"
]


def classify_document_content(filename: str, text: str) -> dict[str, str]:
    """Classify document type with human-readable label and category."""
    sample = (filename + " " + text[:3000]).lower()

    if any(k in sample for k in ["aadhaar", "uidai", "unique identification", "enrolment no", "mera aadhaar", "helpdesk: 1947"]):
        return {"type": "aadhaar_card", "label": "Aadhaar Card", "category": "identity"}
    if re.search(r"\b[a-z]{5}[0-9]{4}[a-z]\b", sample) or any(k in sample for k in ["permanent account number", "income tax department", "pan card"]):
        return {"type": "pan_card", "label": "PAN Card", "category": "identity"}
    if any(k in sample for k in ["election commission", "elector photo identity", "voter id", "epic no", "electoral"]):
        return {"type": "voter_id", "label": "Voter ID Card", "category": "identity"}
    if any(k in sample for k in ["passport", "republic of india passport", "given name", "place of issue"]):
        return {"type": "passport", "label": "Passport", "category": "identity"}
    if any(k in sample for k in ["driving licence", "driving license", "motor vehicles department", "form 7"]):
        return {"type": "driving_licence", "label": "Driving Licence", "category": "identity"}
    if any(k in sample for k in ["mark sheet", "marksheet", "degree certificate", "convocation", "statement of marks", "grade card", "board of intermediate", "board of secondary"]):
        return {"type": "education_certificate", "label": "Educational Certificate / Mark Sheet", "category": "education"}
    if any(k in sample for k in ["salary slip", "payslip", "income certificate", "pay slip", "form 16", "annual income"]):
        return {"type": "income_proof", "label": "Income Proof / Salary Slip", "category": "income"}
    if any(k in sample for k in ["caste certificate", "community certificate"]):
        return {"type": "community_certificate", "label": "Community / Caste Certificate", "category": "personal"}
    if any(k in sample for k in ["birth certificate", "certificate of birth"]):
        return {"type": "birth_certificate", "label": "Birth Certificate", "category": "personal"}
    if any(k in sample for k in ["curriculum vitae", "resume", "work experience", "technical skills", "projects", "education summary"]):
        return {"type": "resume", "label": "Resume / CV", "category": "employment"}
    if any(k in sample for k in ["bank statement", "passbook", "account statement"]):
        return {"type": "bank_statement", "label": "Bank Statement / Passbook", "category": "bank"}

    return {"type": "general_document", "label": "General Document", "category": "general"}


def extract_profile_from_text(text: str, filename: str = "") -> dict[str, str]:
    """Extract all recognizable applicant fields from document text."""
    fields: dict[str, str] = {}
    if not text or not text.strip():
        return fields

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # 1. Identity Document Numbers
    # Aadhaar Number (12 digits: 4 4 4)
    aadhaar_match = re.search(r"\b([2-9][0-9]{3}\s?[0-9]{4}\s?[0-9]{4})\b", text)
    if aadhaar_match:
        digits_only = re.sub(r"\D", "", aadhaar_match.group(1))
        if len(digits_only) == 12:
            fields["aadhaar_number"] = f"{digits_only[:4]} {digits_only[4:8]} {digits_only[8:]}"

    # PAN Number (5 letters, 4 digits, 1 letter)
    pan_match = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", text)
    if pan_match:
        fields["pan_number"] = pan_match.group(1).upper()

    # Voter ID (EPIC number: 3 letters, 7 digits)
    voter_match = re.search(r"\b([A-Z]{3}[0-9]{7})\b", text)
    if voter_match:
        fields["voter_id"] = voter_match.group(1).upper()

    # Passport Number (1 letter followed by 7 digits)
    if any(k in (filename + " " + text[:500]).lower() for k in ["passport", "republic of india"]):
        pass_match = re.search(r"\b([A-Z][0-9]{7})\b", text)
        if pass_match:
            fields["passport_number"] = pass_match.group(1).upper()

    # Driving Licence Number
    dl_match = re.search(r"\b([A-Z]{2}[ -]?[0-9]{2}[ -]?[0-9]{11})\b", text) or re.search(r"\b([A-Z]{2}[0-9]{13,15})\b", text)
    if dl_match:
        fields["driving_licence"] = re.sub(r"[\s-]+", "", dl_match.group(1).upper())

    # 2. Email Address
    email_match = re.search(r"\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b", text)
    if email_match:
        fields["email"] = email_match.group(1).lower()

    # 3. Mobile Number (Indian 10-digit starting with 6-9)
    phone_match = re.search(r"(?:(?:\+?91[\s-]?)|\b)([6-9][0-9]{9})\b", text)
    if phone_match:
        fields["phone"] = "+91 " + phone_match.group(1)

    # 4. Date of Birth
    dob_match = re.search(r"(?i)(?:date\s*of\s*birth|dob|d\.o\.b\.?|birth\s*date)[\s:\-]*([0-3]?[0-9][/\-.][0-1]?[0-9][/\-.][12][0-9]{3}|[12][0-9]{3}[/\-.][0-1]?[0-9][/\-.][0-3]?[0-9])", text)
    if dob_match:
        fields["date_of_birth"] = dob_match.group(1).replace("-", "/").replace(".", "/")
    else:
        yob_match = re.search(r"(?i)(?:year\s*of\s*birth|yob)[\s:\-]*([12][0-9]{3})", text)
        if yob_match:
            fields["date_of_birth"] = f"01/01/{yob_match.group(1)}"

    # 5. Gender
    gender_match = re.search(r"(?i)(?:gender|sex)[\s:\-]*\b(male|female|transgender)\b", text)
    if gender_match:
        fields["gender"] = gender_match.group(1).capitalize()
    elif re.search(r"\b(?:/\s*MALE|/\s*FEMALE)\b", text, re.I):
        fields["gender"] = "Male" if "MALE" in text.upper() else "Female"

    # 6. Blood Group
    blood_match = re.search(r"\b(A|B|AB|O)[+-]\b(?:\s*(?:ve|positive|negative))?", text, re.I)
    if blood_match:
        bg = blood_match.group(1).upper()
        sign = "+" if "+" in blood_match.group(0) or "pos" in blood_match.group(0).lower() else "-"
        fields["blood_group"] = f"{bg}{sign}"

    # 7. PIN / Postal Code (6 digits in India)
    pin_match = re.search(r"(?i)(?:pin\s*(?:code)?|postal\s*code|pincode)[\s:\-]*([1-9][0-9]{5})\b", text)
    if pin_match:
        fields["postal_code"] = pin_match.group(1)
    else:
        general_pin = re.search(r"\b([1-9][0-9]{5})\b", text)
        if general_pin:
            fields["postal_code"] = general_pin.group(1)

    # 8. State & Nationality
    for state in INDIAN_STATES:
        if re.search(r"\b" + re.escape(state) + r"\b", text, re.I):
            fields["state"] = state
            fields["country"] = "India"
            fields["nationality"] = "Indian"
            break

    # 9. Full Name
    # Check explicit label
    name_match = re.search(r"(?im)^\s*(?:applicant\s+|elector's\s+|cardholder's\s+)?name\s*[:\-]\s*([A-Za-z][A-Za-z .]{2,40})\s*$", text)
    if name_match:
        name_val = name_match.group(1).strip()
        if not any(stop in name_val.lower() for stop in ["income", "father", "department", "government", "india"]):
            fields["full_name"] = name_val.title()
    elif "pan" in filename.lower() or "permanent account" in text.lower():
        # In PAN cards, Name is typically before Father's Name
        for i, line in enumerate(lines[:10]):
            if line.upper() in ["NAME", "NAME:"]:
                if i + 1 < len(lines):
                    fields["full_name"] = lines[i + 1].strip().title()
                    break
            elif line.isupper() and len(line.split()) >= 2 and not any(w in line for w in ["INCOME", "TAX", "GOVT", "INDIA", "PERMANENT", "ACCOUNT", "DEPARTMENT"]):
                fields["full_name"] = line.title()
                break
    elif "aadhaar" in filename.lower() or "unique identification" in text.lower():
        # Check "To:\nName"
        for i, line in enumerate(lines[:12]):
            if line.lower() in ["to:", "to"]:
                if i + 1 < len(lines):
                    cand = lines[i + 1].strip()
                    if not any(w in cand.lower() for w in ["government", "unique", "uidai", "s/o", "d/o", "w/o"]):
                        fields["full_name"] = cand.title()
                        break
            elif any(line.lower().startswith(p) for p in ["s/o:", "d/o:", "w/o:", "c/o:"]):
                # The line before S/O is often the full name
                if i > 0 and len(lines[i - 1].split()) in [2, 3, 4]:
                    cand = lines[i - 1].strip()
                    if not any(w in cand.lower() for w in ["government", "unique", "uidai", "to:"]):
                        fields["full_name"] = cand.title()
                        break

    # If full_name is present, also populate given_name and surname
    if "full_name" in fields:
        parts = fields["full_name"].split()
        if len(parts) >= 2:
            fields["given_name"] = parts[0]
            fields["surname"] = parts[-1]
            if len(parts) > 2:
                fields["middle_name"] = " ".join(parts[1:-1])
        elif len(parts) == 1:
            fields["given_name"] = parts[0]
            fields["surname"] = parts[0]

    # 10. Father's / Mother's / Spouse's Name (stop before newline!)
    father_match = re.search(r"(?i)(?:father's?\s*name|father\s*name|s/o|son\s*of)[\s:\-]+([A-Za-z][A-Za-z .]{2,40})", text)
    if father_match:
        f_name = father_match.group(1).strip()
        if len(f_name) >= 3 and not any(w in f_name.lower() for w in ["government", "income", "india"]):
            fields["father_name"] = f_name.title()

    mother_match = re.search(r"(?i)(?:mother's?\s*name|mother\s*name)[\s:\-]+([A-Za-z][A-Za-z .]{2,40})", text)
    if mother_match:
        m_name = mother_match.group(1).strip()
        if len(m_name) >= 3:
            fields["mother_name"] = m_name.title()

    spouse_match = re.search(r"(?i)(?:spouse's?\s*name|husband's?\s*name|wife's?\s*name|w/o|h/o)[\s:\-]+([A-Za-z][A-Za-z .]{2,40})", text)
    if spouse_match:
        s_name = spouse_match.group(1).strip()
        if len(s_name) >= 3:
            fields["spouse_name"] = s_name.title()

    # 11. Address extraction
    addr_match = re.search(r"(?is)(?:address|permanent\s*address|residential\s*address)[\s:\-]+(.*?)(?:pin|pincode|postal|state|\n\n|$)", text)
    if addr_match:
        raw_addr = addr_match.group(1).strip()
        clean_addr = re.sub(r"\s+", " ", raw_addr)
        if len(clean_addr) >= 10:
            fields["address_line_1"] = clean_addr[:150]

    # 12. Education Fields
    degree_match = re.search(r"\b(B\.?Tech|M\.?Tech|B\.?E\.?|M\.?E\.?|B\.?Sc|M\.?Sc|B\.?Com|M\.?Com|B\.?A\.?|M\.?A\.?|BCA|MCA|MBA|BBA|Ph\.?D|Diploma|10th|12th|HSC|SSLC)\b", text, re.I)
    if degree_match:
        fields["course"] = degree_match.group(1).upper().replace(".", "")
        if fields["course"] in ["BTECH", "BE", "BSC", "BCOM", "BA", "BCA", "BBA"]:
            fields["education_level"] = "Undergraduate"
        elif fields["course"] in ["MTECH", "ME", "MSC", "MCOM", "MA", "MCA", "MBA"]:
            fields["education_level"] = "Postgraduate"
        elif fields["course"] in ["10TH", "SSLC"]:
            fields["education_level"] = "10th"
        elif fields["course"] in ["12TH", "HSC"]:
            fields["education_level"] = "12th"
        elif fields["course"] == "DIPLOMA":
            fields["education_level"] = "Diploma"

    inst_match = re.search(r"(?i)([A-Za-z .&-]+(?:University|Institute\s*of\s*Technology|College|Engineering\s*College|School|Vidyalaya))", text)
    if inst_match:
        inst_name = inst_match.group(1).strip()
        if 8 <= len(inst_name) <= 100:
            fields["institution"] = inst_name.title()

    year_match = re.search(r"(?i)(?:year\s*of\s*passing|passing\s*year|graduation\s*year)[\s:\-]*([12][0-9]{3})", text)
    if year_match:
        fields["graduation_year"] = year_match.group(1)

    cgpa_match = re.search(r"(?i)(?:cgpa|gpa|percentage|marks\s*obtained)[\s:\-]*([0-9]{1,2}(?:\.[0-9]{1,2})?\s*%?|[0-9]\.[0-9]{1,2}\s*/\s*10)", text)
    if cgpa_match:
        fields["grade"] = cgpa_match.group(1).strip()

    roll_match = re.search(r"(?i)(?:roll\s*(?:no|number)|reg(?:istration)?\s*(?:no|number)|enrollment\s*(?:no|number))[\s:\-]*([A-Za-z0-9\-_]{5,25})", text)
    if roll_match:
        fields["student_id"] = roll_match.group(1).upper()

    # 13. Income / Salary
    income_match = re.search(r"(?i)(?:annual\s*income|total\s*income|gross\s*salary|ctc)[\s:\-]*(?:rs\.?|inr|₹)?\s*([0-9,]{4,12})", text)
    if income_match:
        fields["annual_income"] = income_match.group(1).replace(",", "").strip()

    # 14. Skills (from Resumes)
    skills_match = re.search(r"(?is)(?:technical\s*skills|skills|key\s*skills)[\s:\-]+(.*?)(?:experience|education|projects|certifications|\n\n|$)", text)
    if skills_match:
        raw_skills = skills_match.group(1).strip()
        clean_skills = re.sub(r"\s+", " ", raw_skills)[:200]
        if len(clean_skills) >= 5:
            fields["skills"] = clean_skills

    # 15. Bank Details
    ifc_match = re.search(r"\b([A-Z]{4}0[A-Z0-9]{6})\b", text)
    if ifc_match:
        fields["bank_ifsc"] = ifc_match.group(1).upper()

    acc_match = re.search(r"(?i)(?:account\s*number|a/c\s*no\.?)[\s:\-]*([0-9]{9,18})\b", text)
    if acc_match:
        fields["bank_account_number"] = acc_match.group(1)

    return fields
