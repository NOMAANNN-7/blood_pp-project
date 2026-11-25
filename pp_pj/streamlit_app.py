import sys
import os
from pathlib import Path
from datetime import datetime, date

# Ensure root directory is on Python path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import streamlit as st
import pandas as pd

from backend.app.database import SessionLocal, engine, Base
from backend.app.models.donor import Donor
from backend.app.models.camp import DonationCamp
from backend.app.schemas.donor import DonorCreate, DonorUpdate, DonationRecordCreate
from backend.app.schemas.camp import CampCreate
from backend.app.services.donor_service import (
    register_donor,
    get_donors,
    get_donor_by_id,
    update_donor,
    soft_delete_donor,
    record_donation
)
from backend.app.services.camp_service import (
    create_camp,
    get_camps,
    get_camp_by_id,
    delete_camp
)
from backend.app.services.analytics_service import (
    compute_blood_group_analytics,
    compute_dashboard_summary
)
from backend.app.services.import_export_service import (
    parse_and_validate_csv,
    execute_csv_import,
    export_donors_csv,
    export_report_markdown,
    generate_pdf_report
)
from backend.app.services.backup_service import create_json_backup
from backend.app.config import ALLOWED_BLOOD_GROUPS
from backend.app.utils.validators import calculate_age

# Ensure tables exist
Base.metadata.create_all(bind=engine)

st.set_page_config(
    page_title="LIFEPOINT - Blood Donation Camp Register & Management",
    page_icon="🩸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Deep Crimson Theme #B91C1C)
st.markdown("""
<style>
    .main-header {
        color: #B91C1C;
        font-weight: 900;
        font-size: 2.2rem;
        letter-spacing: -0.5px;
        margin-bottom: 0px;
    }
    .sub-header {
        color: #64748B;
        font-size: 0.95rem;
        margin-bottom: 24px;
    }
    .kpi-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 18px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        margin-bottom: 12px;
    }
    .kpi-title {
        color: #64748B;
        font-size: 0.8rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .kpi-value {
        color: #0F172A;
        font-size: 1.8rem;
        font-weight: 800;
        margin-top: 4px;
    }
    .stButton>button {
        background-color: #B91C1C;
        color: white;
        border-radius: 10px;
        font-weight: 700;
        border: none;
    }
    .stButton>button:hover {
        background-color: #991B1B;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Helper DB Session
def get_db():
    return SessionLocal()

# Sidebar Navigation
st.sidebar.markdown("""
<div style="display: flex; align-items: center; gap: 10px; margin-bottom: 20px;">
    <span style="font-size: 32px;">🩸</span>
    <div>
        <h2 style="margin: 0; color: #B91C1C; font-weight: 900; font-size: 22px;">LIFEPOINT</h2>
        <span style="font-size: 11px; color: #64748B;">Blood Camp Register & Management</span>
    </div>
</div>
""", unsafe_allow_html=True)

menu = st.sidebar.radio(
    "Navigation",
    [
        "📊 Executive Dashboard",
        "🩸 Blood Group Analytics",
        "✍️ Volunteer Registration",
        "👥 Donor Management",
        "⛺ Donation Camps",
        "📥 Bulk CSV Import",
        "📑 Reports & Data Exports",
        "📜 Activity & Audit Logs"
    ]
)

st.sidebar.markdown("---")
st.sidebar.info("💡 **Local-First Platform:** 100% offline-ready SQLite database. No external API keys required.")

# ==============================================================================
# 1. EXECUTIVE DASHBOARD
# ==============================================================================
if menu == "📊 Executive Dashboard":
    st.markdown('<p class="main-header">Executive Operations Dashboard</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Real-time clinical metrics & volunteer classification directly from local SQLite database</p>', unsafe_allow_html=True)

    db = get_db()
    try:
        summary = compute_dashboard_summary(db)
        analytics = compute_blood_group_analytics(db)

        # KPI Row 1
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Volunteers", summary.total_volunteers)
        c1.caption("Registered in camp registry")
        c2.metric("Eligible Donors", summary.eligible_donors, f"{(summary.eligible_donors/(summary.total_volunteers or 1)*100):.0f}% of total")
        c2.caption("Passed preliminary screening")
        c3.metric("Temporarily Deferred", summary.temporarily_deferred)
        c3.caption("Weight/travel/recovery deferrals")
        c4.metric("Permanently Deferred", summary.permanently_deferred)
        c4.caption("Medical questionnaire flags")

        # KPI Row 2
        c5, c6, c7, c8 = st.columns(4)
        c5.metric("Completed Donations", summary.completed_donations)
        c5.caption("Total units collected")
        c6.metric("Active Camps", summary.active_camps)
        c6.caption(f"{summary.upcoming_camps} upcoming camp(s)")
        c7.metric("New This Month", summary.new_registrations_this_month)
        c7.caption("Registered this calendar month")
        c8.metric("Most Common Group", summary.most_common_blood_group or "N/A")
        c8.caption(f"{summary.blood_group_counts.get(summary.most_common_blood_group or '', 0)} donors in pool")

        st.markdown("---")

        # Blood Group Grid Cards
        st.subheader("Blood Group Volunteer Pool (8 Standard Groups)")
        bg_cols = st.columns(8)
        for idx, bg_stat in enumerate(analytics.blood_groups):
            with bg_cols[idx]:
                st.markdown(f"""
                <div style="background: white; border: 1px solid #E2E8F0; border-radius: 12px; padding: 10px; text-align: center;">
                    <div style="font-weight: 900; font-size: 18px; color: #B91C1C;">{bg_stat.blood_group}</div>
                    <div style="font-weight: 800; font-size: 22px; color: #0F172A;">{bg_stat.total_donors}</div>
                    <div style="font-size: 11px; color: #16A34A; font-weight: 600;">{bg_stat.eligible_donors} eligible</div>
                    <div style="font-size: 10px; color: #64748B;">{bg_stat.percentage}% share</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Charts Section
        col_left, col_right = st.columns(2)
        with col_left:
            st.subheader("Blood Group Distribution")
            df_bg = pd.DataFrame([
                {"Blood Group": bg.blood_group, "Total Volunteers": bg.total_donors, "Eligible": bg.eligible_donors}
                for bg in analytics.blood_groups
            ]).set_index("Blood Group")
            st.bar_chart(df_bg)

        with col_right:
            st.subheader("Registration Velocity (Last 14 Days)")
            df_trends = pd.DataFrame(summary.registration_trends).set_index("date")
            st.line_chart(df_trends)

        # Recent registrations table
        st.subheader("Recent Volunteer Registrations")
        if summary.recent_donors:
            df_recent = pd.DataFrame(summary.recent_donors)[["donor_id", "full_name", "blood_group", "city", "screening_status", "registration_date"]]
            df_recent.columns = ["Donor ID", "Full Name", "Blood Group", "City", "Screening Status", "Registered At"]
            st.dataframe(df_recent, use_container_width=True, hide_index=True)
        else:
            st.info("No registered donors yet.")
    finally:
        db.close()

# ==============================================================================
# 2. BLOOD GROUP ANALYTICS
# ==============================================================================
elif menu == "🩸 Blood Group Analytics":
    st.markdown('<p class="main-header">Blood Group Distribution & Inventory Analytics</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Accurate Python collections.Counter classification across all eight standard blood types</p>', unsafe_allow_html=True)

    db = get_db()
    try:
        # Filter controls
        f1, f2, f3 = st.columns(3)
        camps = db.query(DonationCamp).all()
        camp_options = {"All Camps": None}
        for c in camps:
            camp_options[f"{c.name} ({c.city})"] = c.id

        selected_camp_name = f1.selectbox("Filter by Donation Camp", list(camp_options.keys()))
        selected_camp_id = camp_options[selected_camp_name]
        selected_city = f2.text_input("Filter by City", "")
        selected_status = f3.selectbox("Filter by Screening Status", ["All Statuses", "PRELIMINARY_ELIGIBLE", "VERIFIED_ELIGIBLE", "TEMPORARILY_DEFERRED", "PERMANENTLY_DEFERRED"])
        status_filter = None if selected_status == "All Statuses" else selected_status

        analytics = compute_blood_group_analytics(
            db,
            camp_id=selected_camp_id,
            city=selected_city if selected_city.strip() else None,
            screening_status=status_filter
        )

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Filtered Volunteers", analytics.total_registered)
        m2.metric("Most Common Blood Group", analytics.most_common_blood_group or "N/A", f"{analytics.most_common_count} donors")
        m3.metric("Rarest Blood Group", analytics.least_common_blood_group or "N/A", f"{analytics.least_common_count} donors")
        m4.metric("Total Completed Units", sum(bg.completed_donations for bg in analytics.blood_groups))

        st.markdown("---")

        # Table & Breakdown
        data_rows = []
        for bg in analytics.blood_groups:
            data_rows.append({
                "Blood Group": bg.blood_group,
                "Total Volunteers": bg.total_donors,
                "Eligible Donors": bg.eligible_donors,
                "Temporarily Deferred": bg.temporarily_deferred,
                "Permanently Deferred": bg.permanently_deferred,
                "Completed Donations": bg.completed_donations,
                "Distribution Share (%)": f"{bg.percentage}%"
            })
        df_table = pd.DataFrame(data_rows)
        st.dataframe(df_table, use_container_width=True, hide_index=True)

        chart_df = pd.DataFrame([
            {"Blood Group": r["Blood Group"], "Eligible": r["Eligible Donors"], "Deferred": r["Temporarily Deferred"] + r["Permanently Deferred"]}
            for r in data_rows
        ]).set_index("Blood Group")
        st.bar_chart(chart_df)
    finally:
        db.close()

# ==============================================================================
# 3. VOLUNTEER REGISTRATION
# ==============================================================================
elif menu == "✍️ Volunteer Registration":
    st.markdown('<p class="main-header">Volunteer Donor Registration</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Register new blood donation volunteers with automated age calculation and preliminary screening</p>', unsafe_allow_html=True)

    db = get_db()
    try:
        camps = db.query(DonationCamp).filter(DonationCamp.status.in_(["ACTIVE", "UPCOMING"])).all()
        camp_dict = {"General Camp Roster": None}
        for c in camps:
            camp_dict[f"{c.name} ({c.city})"] = c.id

        with st.form("donor_registration_form"):
            st.subheader("1. Personal Details")
            r1c1, r1c2 = st.columns(2)
            full_name = r1c1.text_input("Full Name *", placeholder="e.g. Dr. Rajesh Kumar")
            gender = r1c2.selectbox("Gender", ["Male", "Female", "Other", "Prefer not to say"])

            r2c1, r2c2 = st.columns(2)
            dob = r2c1.date_input("Date of Birth *", min_value=date(1940, 1, 1), max_value=date.today())
            phone = r2c2.text_input("Phone Number (10+ digits) *", placeholder="+919876543210")

            email = st.text_input("Email Address (Optional)", placeholder="volunteer@example.com")

            r3c1, r3c2, r3c3 = st.columns(3)
            address = r3c1.text_input("Address *", placeholder="House/Flat, Street")
            city = r3c2.text_input("City *", placeholder="e.g. Bengaluru")
            state = r3c3.text_input("State *", placeholder="e.g. Karnataka")
            pin_code = st.text_input("PIN Code *", placeholder="560001")

            st.subheader("2. Donation Details")
            d1, d2, d3 = st.columns(3)
            blood_group = d1.selectbox("Blood Group *", ALLOWED_BLOOD_GROUPS)
            weight = d2.number_input("Weight (kg) *", min_value=30.0, max_value=250.0, value=65.0, step=0.5)
            pref_camp = d3.selectbox("Preferred Donation Camp", list(camp_dict.keys()))

            st.subheader("3. Preliminary Medical Checklist")
            st.caption("ℹ️ Final clinical eligibility requires authorized physical examination by a registered camp physician.")
            has_chronic = st.checkbox("Chronic medical condition (cardiac, hepatitis, bleeding disorder, uncontrolled diabetes)")
            has_surgery = st.checkbox("Recent major surgery or dental extraction in past 6 months")
            has_meds = st.checkbox("Currently on active prescription medications (antibiotics/blood thinners)")

            st.subheader("4. Consent")
            consent_store = st.checkbox("I consent to storing my registration information in the local database.", value=True)
            consent_call = st.checkbox("I consent to being contacted for blood donation camps and emergency needs.", value=True)

            submitted = st.form_submit_button("Submit Registration")

            if submitted:
                if not full_name.strip():
                    st.error("Full name cannot be blank.")
                elif not phone.strip() or len(phone.replace(" ", "")) < 10:
                    st.error("Please enter a valid phone number with at least 10 digits.")
                elif not address.strip() or not city.strip() or not state.strip() or not pin_code.strip():
                    st.error("Please fill in all mandatory address fields.")
                elif not consent_store:
                    st.error("Data storage consent is required.")
                else:
                    try:
                        donor_in = DonorCreate(
                            full_name=full_name.strip(),
                            date_of_birth=dob,
                            gender=gender,
                            phone=phone.strip(),
                            email=email.strip() or None,
                            address=address.strip(),
                            city=city.strip(),
                            state=state.strip(),
                            pin_code=pin_code.strip(),
                            blood_group=blood_group,
                            weight_kg=weight,
                            preferred_camp_id=camp_dict[pref_camp],
                            has_chronic_illness=has_chronic,
                            has_recent_surgery=has_surgery,
                            has_medication=has_meds,
                            consent_data_storage=consent_store,
                            consent_contact=consent_call
                        )
                        new_donor = register_donor(db, donor_in)
                        st.success(f"✓ Volunteer '{new_donor.full_name}' registered successfully with ID: {new_donor.donor_id}!")
                        st.info(f"Preliminary Status: **{new_donor.screening_status}** (Calculated Age: {new_donor.age} years)")
                    except Exception as e:
                        st.error(f"Registration error: {str(e)}")
    finally:
        db.close()

# ==============================================================================
# 4. DONOR MANAGEMENT
# ==============================================================================
elif menu == "👥 Donor Management":
    st.markdown('<p class="main-header">Donor Records Directory & Management</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">View, search, update screening verification, and record historical donation events</p>', unsafe_allow_html=True)

    db = get_db()
    try:
        s1, s2, s3 = st.columns(3)
        search_query = s1.text_input("Search (Name, Phone, Donor ID, City)", "")
        bg_filter = s2.selectbox("Filter by Blood Group", ["All Groups"] + ALLOWED_BLOOD_GROUPS)
        status_filter = s3.selectbox("Filter by Status", ["All Statuses", "PRELIMINARY_ELIGIBLE", "VERIFIED_ELIGIBLE", "TEMPORARILY_DEFERRED", "PERMANENTLY_DEFERRED"])

        donors, total = get_donors(
            db,
            search=search_query if search_query.strip() else None,
            blood_group=bg_filter if bg_filter != "All Groups" else None,
            screening_status=status_filter if status_filter != "All Statuses" else None,
            page_size=100
        )

        st.write(f"Showing **{len(donors)}** of **{total}** records")

        if donors:
            donor_list = []
            for d in donors:
                donor_list.append({
                    "Donor ID": d.donor_id,
                    "Name": d.full_name,
                    "Blood Group": d.blood_group,
                    "Age": d.age,
                    "Phone": d.phone,
                    "City": d.city,
                    "Status": d.screening_status,
                    "Total Donations": d.total_donations,
                    "Registered": d.registration_date.strftime("%Y-%m-%d")
                })
            st.dataframe(pd.DataFrame(donor_list), use_container_width=True, hide_index=True)

            st.markdown("---")
            st.subheader("Manage Specific Donor")
            selected_did = st.selectbox("Select Donor ID to manage", [d.donor_id for d in donors])
            target_donor = get_donor_by_id(db, selected_did)

            if target_donor:
                p1, p2 = st.columns(2)
                with p1:
                    st.write(f"**Name:** {target_donor.full_name}")
                    st.write(f"**Blood Group:** {target_donor.blood_group} | **Age:** {target_donor.age}")
                    st.write(f"**Phone:** {target_donor.phone} | **City:** {target_donor.city}")
                    st.write(f"**Current Status:** `{target_donor.screening_status}`")
                    if target_donor.deferral_reason:
                        st.caption(f"Reason: {target_donor.deferral_reason}")

                with p2:
                    action_choice = st.radio("Choose Action", ["Record Completed Donation", "Update Screening Status", "Deactivate Record"], horizontal=True)

                    if action_choice == "Record Completed Donation":
                        with st.form("rec_donation_form"):
                            units = st.number_input("Units Donated", min_value=0.5, max_value=2.0, value=1.0, step=0.5)
                            don_date = st.date_input("Donation Date", value=date.today())
                            if st.form_submit_button("Record Donation Unit"):
                                record_donation(db, target_donor.donor_id, DonationRecordCreate(donation_date=don_date, units_donated=units))
                                st.success("Donation recorded! Total count incremented.")
                                st.rerun()

                    elif action_choice == "Update Screening Status":
                        with st.form("update_status_form"):
                            new_st = st.selectbox("New Verification Status", ["VERIFIED_ELIGIBLE", "PRELIMINARY_ELIGIBLE", "TEMPORARILY_DEFERRED", "PERMANENTLY_DEFERRED"])
                            reason = st.text_input("Clinical Note / Deferral Reason", target_donor.deferral_reason or "")
                            if st.form_submit_button("Save Status"):
                                update_donor(db, target_donor.donor_id, DonorUpdate(screening_status=new_st, deferral_reason=reason or None))
                                st.success("Verification status updated!")
                                st.rerun()

                    elif action_choice == "Deactivate Record":
                        if st.button("Confirm Soft-Deletion"):
                            soft_delete_donor(db, target_donor.donor_id)
                            st.warning(f"Donor {target_donor.donor_id} deactivated.")
                            st.rerun()
    finally:
        db.close()

# ==============================================================================
# 5. DONATION CAMPS
# ==============================================================================
elif menu == "⛺ Donation Camps":
    st.markdown('<p class="main-header">Donation Camp Management</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Schedule blood donation drives, manage capacity, and track volunteer attendance</p>', unsafe_allow_html=True)

    db = get_db()
    try:
        camps = get_camps(db)
        camp_data = []
        for c, donor_cnt, don_cnt in camps:
            fill_pct = (donor_cnt / c.capacity * 100) if c.capacity > 0 else 0
            camp_data.append({
                "Camp Code": c.camp_code,
                "Name": c.name,
                "City": c.city,
                "Venue": c.venue,
                "Dates": f"{c.start_date} to {c.end_date}",
                "Capacity": c.capacity,
                "Registered": donor_cnt,
                "Fill %": f"{fill_pct:.0f}%",
                "Status": c.status
            })
        st.dataframe(pd.DataFrame(camp_data), use_container_width=True, hide_index=True)

        st.markdown("---")
        with st.expander("➕ Schedule New Donation Camp"):
            with st.form("new_camp_form"):
                cn1, cn2 = st.columns(2)
                camp_name = cn1.text_input("Camp Title *", placeholder="e.g. Metro Lifeline Youth Drive")
                camp_venue = cn2.text_input("Venue *", placeholder="e.g. Civic Auditorium")

                cn3, cn4 = st.columns(2)
                camp_city = cn3.text_input("City *", placeholder="e.g. Bengaluru")
                camp_address = cn4.text_input("Address *", placeholder="Street, Area")

                d1, d2, d3 = st.columns(3)
                start_d = d1.date_input("Start Date *", value=date.today())
                end_d = d2.date_input("End Date *", value=date.today())
                cap = d3.number_input("Capacity *", min_value=10, max_value=2000, value=100)

                o1, o2 = st.columns(2)
                org = o1.text_input("Organizer *", placeholder="e.g. Red Cross Society")
                phone = o2.text_input("Contact Phone *", placeholder="+919876543210")

                c_status = st.selectbox("Initial Status", ["UPCOMING", "ACTIVE", "COMPLETED"])

                if st.form_submit_button("Create Camp"):
                    if not camp_name.strip() or not camp_venue.strip() or not camp_city.strip():
                        st.error("Please fill in mandatory camp fields.")
                    elif end_d < start_d:
                        st.error("End date cannot be earlier than start date.")
                    else:
                        c_in = CampCreate(
                            name=camp_name.strip(),
                            venue=camp_venue.strip(),
                            address=camp_address.strip() or camp_venue.strip(),
                            city=camp_city.strip(),
                            start_date=start_d,
                            end_date=end_d,
                            capacity=cap,
                            organizer=org.strip() or "Health NGO",
                            contact_phone=phone.strip(),
                            status=c_status
                        )
                        created = create_camp(db, c_in)
                        st.success(f"✓ Camp '{created.name}' created with code: {created.camp_code}!")
                        st.rerun()
    finally:
        db.close()

# ==============================================================================
# 6. BULK CSV IMPORT
# ==============================================================================
elif menu == "📥 Bulk CSV Import":
    st.markdown('<p class="main-header">Bulk CSV Volunteer Import</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Upload batches of volunteer records with row-by-row validation, duplicate rejection, and error logs</p>', unsafe_allow_html=True)

    db = get_db()
    try:
        uploaded_file = st.file_uploader("Upload CSV File", type=["csv"])
        if uploaded_file is not None:
            content = uploaded_file.getvalue().decode("utf-8")
            res = parse_and_validate_csv(db, content)

            if not res["success"]:
                st.error(res["error"])
            else:
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Rows in File", res["total_rows"])
                col2.metric("Valid Rows (Ready)", res["valid_count"])
                col3.metric("Invalid / Rejected Rows", res["invalid_count"])

                if res["valid_count"] > 0:
                    st.subheader(f"Valid Rows Ready for Ingestion ({res['valid_count']})")
                    df_valid = pd.DataFrame(res["valid_rows"])[["row_number", "full_name", "date_of_birth", "blood_group", "phone", "city", "weight_kg"]]
                    st.dataframe(df_valid, use_container_width=True, hide_index=True)

                    if st.button("Execute Import of Valid Rows"):
                        cnt = execute_csv_import(db, res["valid_rows"])
                        st.success(f"✓ Successfully imported {cnt} volunteer records into SQLite!")
                        st.rerun()

                if res["invalid_count"] > 0:
                    st.subheader(f"Rejected Rows with Detected Issues ({res['invalid_count']})")
                    df_inv = pd.DataFrame(res["invalid_rows"])[["row_number", "full_name", "phone", "errors"]]
                    st.dataframe(df_inv, use_container_width=True, hide_index=True)
                    st.download_button("Download Rejection Error Report (CSV)", res["error_csv"], file_name="import_errors.csv", mime="text/csv")
    finally:
        db.close()

# ==============================================================================
# 7. REPORTS & DATA EXPORTS
# ==============================================================================
elif menu == "📑 Reports & Data Exports":
    st.markdown('<p class="main-header">Reports Center & Data Persistence</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Export audited executive summaries in PDF, CSV, Markdown, or take a full JSON database snapshot</p>', unsafe_allow_html=True)

    db = get_db()
    try:
        r1, r2 = st.columns(2)
        with r1:
            st.subheader("1. Executive PDF Report")
            st.write("Publication-quality styled report generated in native Python via ReportLab.")
            pdf_bytes = generate_pdf_report(db)
            st.download_button("📥 Download Official PDF Report", pdf_bytes, file_name="lifepoint_executive_report.pdf", mime="application/pdf")

        with r2:
            st.subheader("2. Tabular CSV Data")
            st.write("Export active donor records with proper column headers.")
            csv_text = export_donors_csv(db)
            st.download_button("📥 Download Donor Directory (CSV)", csv_text, file_name="lifepoint_donors.csv", mime="text/csv")

        st.markdown("---")

        r3, r4 = st.columns(2)
        with r3:
            st.subheader("3. Markdown Report")
            md_text = export_report_markdown(db)
            st.download_button("📥 Download Markdown Summary (.md)", md_text, file_name="lifepoint_summary.md", mime="text/markdown")
            with st.expander("Preview Markdown Content"):
                st.markdown(md_text)

        with r4:
            st.subheader("4. JSON Database Snapshot (Disaster Recovery)")
            if st.button("Generate Immediate JSON Backup"):
                res_backup = create_json_backup(db)
                st.success(f"✓ Backup saved: `{res_backup['filename']}`")
                st.json(res_backup["metadata"])
    finally:
        db.close()

# ==============================================================================
# 8. ACTIVITY & AUDIT LOGS
# ==============================================================================
elif menu == "📜 Activity & Audit Logs":
    st.markdown('<p class="main-header">Activity & Audit Logs</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Immutable chronological audit trail recording donor registrations, status modifications, and data exports</p>', unsafe_allow_html=True)

    db = get_db()
    try:
        from backend.app.models.audit import AuditLog
        logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(100).all()
        log_rows = []
        for l in logs:
            log_rows.append({
                "Timestamp (UTC)": l.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "Action": l.action,
                "Entity": l.entity_type,
                "Entity ID": l.entity_id or "—",
                "Description": l.description,
                "Activity ID": l.activity_id[:8] + "..."
            })
        st.dataframe(pd.DataFrame(log_rows), use_container_width=True, hide_index=True)
    finally:
        db.close()
