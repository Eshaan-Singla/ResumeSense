"""
Flask API Routes for ResumeSense (PostgreSQL + SQLAlchemy version)
"""

from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from backend.nlp.pdf_parser import PDFParser
from backend.nlp.jd_matcher import JDMatcher
from backend.nlp.ats_checker import ATSChecker
from backend.nlp.power_verbs import PowerVerbSuggester
from backend.nlp.resume_insights import ResumeInsights
from backend.ml.resume_scorer import ResumeScorer

# NEW IMPORTS FOR SQLALCHEMY
from backend.db.database import (
    get_db,
    Resume,
    Job,
    AnalysisResult
)
from backend.config import Config

api_bp = Blueprint("api", __name__)
resume_scorer = ResumeScorer()


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS


# =====================================================
# 🔥 ANALYZE RESUME
# =====================================================
@api_bp.route("/analyze", methods=["POST"])
def analyze_resume():
    try:
        db = next(get_db())

        # ---------------------------------------
        # Extract resume text
        # ---------------------------------------
        resume_text = None

        if "resume_file" in request.files:
            file = request.files["resume_file"]
            if file and allowed_file(file.filename):
                resume_text = PDFParser.extract_text_from_bytes(file.read())
                if not resume_text:
                    return jsonify({"error": "Could not read PDF text"}), 400

        if not resume_text:
            resume_text = request.form.get("resume_text")

        if not resume_text:
            return jsonify({"error": "No resume provided"}), 400

        jd_text = request.form.get("job_description", "")

        # ---------------------------------------
        # Perform analyses
        # ---------------------------------------
        results = {}

        # JD MATCHING
        if jd_text:
            match_result = JDMatcher.compute_match_score(resume_text, jd_text)
            results["match_score"] = match_result["match_score"]
            results["match_details"] = match_result
        else:
            results["match_score"] = None
            results["match_details"] = None

        # ATS CHECK
        ats_result = ATSChecker.check_compliance(resume_text)
        results["ats_score"] = ats_result["ats_score"]
        results["ats_report"] = ats_result

        # POWER VERBS
        results["power_verbs"] = {
            "findings": PowerVerbSuggester.find_weak_verbs(resume_text)[:10],
            "stats": PowerVerbSuggester.get_power_verb_stats(resume_text),
        }

        # QUALITY SCORE (ML)
        quality_result = resume_scorer.score_resume(resume_text, jd_text)
        results["quality_score"] = quality_result["quality_score"]
        results["quality_details"] = quality_result

        # RESUME INSIGHTS
        results["resume_insights"] = ResumeInsights.extract_insights(resume_text)

        # ---------------------------------------
        # Store in DB
        # ---------------------------------------
        # Insert Resume
        new_resume = Resume(resume_text=resume_text)
        db.add(new_resume)
        db.commit()
        db.refresh(new_resume)

        # Insert Job (if exists)
        new_job = None
        if jd_text:
            new_job = Job(job_description=jd_text)
            db.add(new_job)
            db.commit()
            db.refresh(new_job)

        # Insert AnalysisResult
        new_analysis = AnalysisResult(
            resume_id=new_resume.id,
            job_id=new_job.id if new_job else None,
            match_score=results["match_score"],
            ats_score=results["ats_score"],
            quality_score=results["quality_score"],
            ats_flags=results["ats_report"],
            power_verb_suggestions=results["power_verbs"],
            match_details=results["match_details"],
        )

        db.add(new_analysis)
        db.commit()
        db.refresh(new_analysis)

        results["analysis_id"] = new_analysis.id
        results["resume_id"] = new_resume.id
        results["job_id"] = new_job.id if new_job else None

        return jsonify(results), 200

    except Exception as e:
        print("ERROR in /analyze:", e)
        return jsonify({"error": str(e)}), 500


# =====================================================
# 🔥 GET HISTORY
# =====================================================
@api_bp.route("/history", methods=["GET"])
def get_history():
    try:
        db = next(get_db())
        limit = request.args.get("limit", 20, type=int)

        query = (
            db.query(AnalysisResult)
            .order_by(AnalysisResult.created_at.desc())
            .limit(limit)
            .all()
        )

        history = []
        for item in query:
            history.append({
                "id": item.id,
                "resume_id": item.resume_id,
                "job_id": item.job_id,
                "match_score": item.match_score,
                "ats_score": item.ats_score,
                "quality_score": item.quality_score,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "resume_preview": (item.resume.resume_text[:200] + "...") if item.resume and len(item.resume.resume_text) > 200 else item.resume.resume_text,
                "jd_preview": (item.job.job_description[:200] + "...") if item.job and len(item.job.job_description) > 200 else (item.job.job_description if item.job else None)
            })

        return jsonify(history), 200

    except Exception as e:
        print("ERROR in /history:", e)
        return jsonify({"error": str(e)}), 500


# =====================================================
# 🔥 GET RESUME BY ID
# =====================================================
@api_bp.route("/resume/<int:resume_id>", methods=["GET"])
def get_resume(resume_id):
    try:
        db = next(get_db())
        resume = db.query(Resume).filter(Resume.id == resume_id).first()

        if not resume:
            return jsonify({"error": "Resume not found"}), 404

        return jsonify({
            "id": resume.id,
            "resume_text": resume.resume_text,
            "created_at": resume.created_at.isoformat() if resume.created_at else None,
            "updated_at": resume.updated_at.isoformat() if resume.updated_at else None,
        }), 200

    except Exception as e:
        print("ERROR in /resume:", e)
        return jsonify({"error": str(e)}), 500


# =====================================================
# 🔥 GET ANALYSIS BY ID
# =====================================================
@api_bp.route("/analysis/<int:analysis_id>", methods=["GET"])
def get_analysis(analysis_id):
    try:
        db = next(get_db())
        item = (
            db.query(AnalysisResult)
            .filter(AnalysisResult.id == analysis_id)
            .first()
        )

        if not item:
            return jsonify({"error": "Analysis result not found"}), 404

        return jsonify({
            "id": item.id,
            "resume_id": item.resume_id,
            "job_id": item.job_id,
            "match_score": item.match_score,
            "ats_score": item.ats_score,
            "quality_score": item.quality_score,
            "ats_flags": item.ats_flags,
            "power_verb_suggestions": item.power_verb_suggestions,
            "match_details": item.match_details,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "resume_text": item.resume.resume_text if item.resume else None,
            "job_description": item.job.job_description if item.job else None,
        }), 200

    except Exception as e:
        print("ERROR in /analysis:", e)
        return jsonify({"error": str(e)}), 500
