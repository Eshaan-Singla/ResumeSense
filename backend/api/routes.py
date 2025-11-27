"""
Flask API Routes for ResumeSense
Handles resume upload, analysis, and history retrieval.
"""
from flask import Blueprint, request, jsonify, send_from_directory
import os
from werkzeug.utils import secure_filename
from backend.nlp.pdf_parser import PDFParser
from backend.nlp.jd_matcher import JDMatcher
from backend.nlp.ats_checker import ATSChecker
from backend.nlp.power_verbs import PowerVerbSuggester
from backend.nlp.resume_insights import ResumeInsights
from backend.ml.resume_scorer import ResumeScorer
from backend.db.database import Database
from backend.config import Config

# Create blueprint
api_bp = Blueprint('api', __name__)

# Initialize components
db = Database()
resume_scorer = ResumeScorer()


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS


@api_bp.route('/analyze', methods=['POST'])
def analyze_resume():
    """
    Analyze a resume against a job description.
    
    Expected form data:
    - resume_file: PDF file (optional if resume_text provided)
    - resume_text: Plain text resume (optional if resume_file provided)
    - job_description: Job description text
    
    Returns:
        JSON with analysis results
    """
    try:
        # Get resume text
        resume_text = None
        
        # Check if resume file was uploaded
        if 'resume_file' in request.files:
            file = request.files['resume_file']
            if file and file.filename and allowed_file(file.filename):
                # Read PDF bytes
                pdf_bytes = file.read()
                resume_text = PDFParser.extract_text_from_bytes(pdf_bytes)
                
                if not resume_text:
                    return jsonify({
                        'error': 'Failed to extract text from PDF. Please ensure the PDF contains readable text.'
                    }), 400
        
        # Check if resume text was provided directly
        if not resume_text and 'resume_text' in request.form:
            resume_text = request.form['resume_text']
        
        if not resume_text:
            return jsonify({
                'error': 'No resume provided. Please upload a PDF file or provide resume text.'
            }), 400
        
        # Get job description
        jd_text = request.form.get('job_description', '')
        
        # Perform analysis
        results = {}
        
        # JD Matching
        if jd_text:
            match_result = JDMatcher.compute_match_score(resume_text, jd_text)
            results['match_score'] = match_result['match_score']
            results['match_details'] = {
                'common_keywords': match_result['common_keywords'],
                'missing_keywords': match_result['missing_keywords'],
                'important_keywords_matched': match_result['important_keywords_matched'],
                'important_keywords_total': match_result['important_keywords_total'],
                'matched_important_keywords': match_result['matched_important_keywords']
            }
        else:
            results['match_score'] = None
            results['match_details'] = None
        
        # ATS Check
        ats_result = ATSChecker.check_compliance(resume_text)
        results['ats_score'] = ats_result['ats_score']
        results['ats_report'] = {
            'issues': ats_result['issues'],
            'recommendations': ats_result['recommendations'],
            'section_checks': ats_result['section_checks'],
            'contact_check': ats_result['contact_check'],
            'formatting_checks': ats_result['formatting_checks']
        }
        
        # Power Verb Suggestions
        verb_findings = PowerVerbSuggester.find_weak_verbs(resume_text)
        verb_stats = PowerVerbSuggester.get_power_verb_stats(resume_text)
        results['power_verbs'] = {
            'findings': verb_findings[:10],  # Top 10
            'stats': verb_stats
        }
        
        # ML Quality Score
        quality_result = resume_scorer.score_resume(resume_text, jd_text)
        results['quality_score'] = quality_result['quality_score']
        results['quality_details'] = {
            'model_used': quality_result['model_used'],
            'features': quality_result['features']
        }

        # Resume insights (projects & achievements)
        results['resume_insights'] = ResumeInsights.extract_insights(resume_text)
        
        # Store in database
        try:
            resume_id = db.insert_resume(resume_text)
            job_id = None
            
            if jd_text:
                job_id = db.insert_job(jd_text)
            
            analysis_id = db.insert_analysis_result(
                resume_id=resume_id,
                job_id=job_id,
                match_score=results.get('match_score'),
                ats_score=results['ats_score'],
                quality_score=results['quality_score'],
                ats_flags=results['ats_report'],
                power_verb_suggestions=results['power_verbs'],
                match_details=results.get('match_details')
            )
            
            results['analysis_id'] = analysis_id
            results['resume_id'] = resume_id
            results['job_id'] = job_id
        except Exception as e:
            print(f"Error storing analysis in database: {e}")
            # Continue even if database storage fails
            results['analysis_id'] = None
        
        return jsonify(results), 200
        
    except Exception as e:
        print(f"Error in analyze_resume: {e}")
        return jsonify({
            'error': f'An error occurred during analysis: {str(e)}'
        }), 500


@api_bp.route('/history', methods=['GET'])
def get_history():
    """
    Get analysis history.
    
    Query parameters:
    - limit: Maximum number of results (default: 20)
    
    Returns:
        JSON array of analysis results
    """
    try:
        limit = request.args.get('limit', 20, type=int)
        history = db.get_analysis_history(limit=limit)
        
        # Format results for JSON response
        formatted_history = []
        for item in history:
            formatted_history.append({
                'id': item['id'],
                'resume_id': item['resume_id'],
                'job_id': item['job_id'],
                'match_score': float(item['match_score']) if item['match_score'] else None,
                'ats_score': float(item['ats_score']) if item['ats_score'] else None,
                'quality_score': float(item['quality_score']) if item['quality_score'] else None,
                'created_at': item['created_at'].isoformat() if item['created_at'] else None,
                'resume_preview': item['resume_text'][:200] + '...' if item['resume_text'] and len(item['resume_text']) > 200 else item['resume_text'],
                'jd_preview': item['job_description'][:200] + '...' if item['job_description'] and len(item['job_description']) > 200 else item['job_description']
            })
        
        return jsonify(formatted_history), 200
        
    except Exception as e:
        print(f"Error in get_history: {e}")
        return jsonify({
            'error': f'An error occurred retrieving history: {str(e)}'
        }), 500


@api_bp.route('/resume/<int:resume_id>', methods=['GET'])
def get_resume(resume_id):
    """
    Get resume by ID.
    
    Args:
        resume_id: Resume ID
        
    Returns:
        JSON with resume data
    """
    try:
        resume = db.get_resume(resume_id)
        
        if not resume:
            return jsonify({
                'error': 'Resume not found'
            }), 404
        
        return jsonify({
            'id': resume['id'],
            'resume_text': resume['resume_text'],
            'created_at': resume['created_at'].isoformat() if resume['created_at'] else None,
            'updated_at': resume['updated_at'].isoformat() if resume['updated_at'] else None
        }), 200
        
    except Exception as e:
        print(f"Error in get_resume: {e}")
        return jsonify({
            'error': f'An error occurred retrieving resume: {str(e)}'
        }), 500


@api_bp.route('/analysis/<int:analysis_id>', methods=['GET'])
def get_analysis(analysis_id):
    """
    Get analysis result by ID.
    
    Args:
        analysis_id: Analysis result ID
        
    Returns:
        JSON with full analysis result
    """
    try:
        result = db.get_analysis_result(analysis_id)
        
        if not result:
            return jsonify({
                'error': 'Analysis result not found'
            }), 404
        
        return jsonify({
            'id': result['id'],
            'resume_id': result['resume_id'],
            'job_id': result['job_id'],
            'match_score': float(result['match_score']) if result['match_score'] else None,
            'ats_score': float(result['ats_score']) if result['ats_score'] else None,
            'quality_score': float(result['quality_score']) if result['quality_score'] else None,
            'ats_flags': result['ats_flags'],
            'power_verb_suggestions': result['power_verb_suggestions'],
            'match_details': result['match_details'],
            'created_at': result['created_at'].isoformat() if result['created_at'] else None,
            'resume_text': result['resume_text'],
            'job_description': result['job_description']
        }), 200
        
    except Exception as e:
        print(f"Error in get_analysis: {e}")
        return jsonify({
            'error': f'An error occurred retrieving analysis: {str(e)}'
        }), 500

