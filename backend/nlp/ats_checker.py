"""
ATS (Applicant Tracking System) Compliance Checker
Flags common ATS issues in resumes.
"""
import re
from typing import Dict, List


class ATSChecker:
    """Check resume for ATS compliance issues"""
    
    # Required sections for ATS compliance
    REQUIRED_SECTIONS = [
        'education', 'experience', 'skills', 'contact', 'summary', 'objective'
    ]
    
    @staticmethod
    def check_compliance(resume_text: str) -> Dict:
        """
        Check resume for ATS compliance issues.
        
        Args:
            resume_text: Resume text to check
            
        Returns:
            Dictionary with ATS compliance report
        """
        text_lower = resume_text.lower()
        
        # Check for required sections
        section_checks = ATSChecker._check_sections(resume_text, text_lower)
        
        # Check for contact information
        contact_check = ATSChecker._check_contact_info(resume_text)
        
        # Check for problematic formatting (tables, images, etc.)
        formatting_checks = ATSChecker._check_formatting(resume_text)
        
        # Calculate overall ATS score
        ats_score = ATSChecker._calculate_ats_score(
            section_checks, contact_check, formatting_checks
        )
        
        return {
            'ats_score': ats_score,
            'section_checks': section_checks,
            'contact_check': contact_check,
            'formatting_checks': formatting_checks,
            'issues': ATSChecker._get_issues(section_checks, contact_check, formatting_checks),
            'recommendations': ATSChecker._get_recommendations(section_checks, contact_check, formatting_checks)
        }
    
    @staticmethod
    def _check_sections(raw_text: str, text_lower: str) -> Dict[str, bool]:
        """
        Check if required sections are present.
        
        Args:
            raw_text: Original resume text (with line structure)
            text_lower: Lowercase resume text
            
        Returns:
            Dictionary mapping section names to presence boolean
        """
        sections = {}
        headings = ATSChecker._find_headings(raw_text)

        def _has_section(keywords):
            keyword_patterns = [re.compile(rf'\b{kw}\b', re.IGNORECASE) for kw in keywords]
            for heading in headings:
                if any(pattern.search(heading) for pattern in keyword_patterns):
                    return True
            return any(pattern.search(text_lower) for pattern in keyword_patterns)
        
        # Check for education section
        education_keywords = ['education', 'academic', 'degree', 'university', 'college', 'school']
        sections['education'] = _has_section(education_keywords)
        
        # Check for experience section
        experience_keywords = ['experience', 'employment', 'work history', 'professional experience', 'career']
        sections['experience'] = _has_section(experience_keywords)
        
        # Check for skills section
        skills_keywords = ['skills', 'technical skills', 'competencies', 'proficiencies', 'tech stack']
        sections['skills'] = _has_section(skills_keywords)
        
        # Check for contact section
        contact_keywords = ['contact', 'contact information', 'contact details']
        sections['contact'] = _has_section(contact_keywords) or ATSChecker._check_contact_info(raw_text)['complete']
        
        # Check for summary/objective
        summary_keywords = ['summary', 'objective', 'profile', 'about', 'overview']
        sections['summary'] = _has_section(summary_keywords)
        
        return sections
    
    @staticmethod
    def _check_contact_info(text: str) -> Dict[str, bool]:
        """
        Check for presence of contact information.
        
        Args:
            text: Resume text
            
        Returns:
            Dictionary with contact info checks
        """
        # Check for email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
        has_email = bool(re.search(email_pattern, text))
        
        # Check for phone number
        phone_patterns = [
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # US format
            r'\(\d{3}\)\s?\d{3}[-.]?\d{4}',    # (123) 456-7890
            r'\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}'  # International
        ]
        has_phone = any(re.search(pattern, text) for pattern in phone_patterns)
        
        # Check for address patterns (number + street)
        address_pattern = r'\b\d{1,5}\s+[A-Za-z0-9]+\s+(Street|St|Avenue|Ave|Road|Rd|Lane|Ln|Drive|Dr|Boulevard|Blvd)\b'
        city_state_pattern = r'\b[A-Za-z]+\s*,\s*[A-Za-z]{2}\b'
        has_address = bool(re.search(address_pattern, text, re.IGNORECASE) or re.search(city_state_pattern, text))
        
        return {
            'has_email': has_email,
            'has_phone': has_phone,
            'has_address': has_address,
            'complete': has_email and has_phone
        }
    
    @staticmethod
    def _check_formatting(text: str) -> Dict[str, bool]:
        """
        Check for problematic formatting that ATS systems may not parse well.
        
        Args:
            text: Resume text
            
        Returns:
            Dictionary with formatting checks
        """
        # Check for table-like structures (multiple spaces or tabs in a row)
        lines = text.split('\n')
        multi_space_lines = sum(1 for line in lines if re.search(r' {4,}', line))
        has_tabs = '\t' in text
        has_pipes = sum(1 for line in lines if '|' in line) >= 3
        has_tables = has_tabs or has_pipes or multi_space_lines >= 4
        
        # Check for excessive special characters (might indicate images or complex formatting)
        special_char_ratio = len(re.findall(r'[^\w\s]', text)) / max(len(text), 1)
        excessive_formatting = special_char_ratio > 0.3
        
        # Check for headers/footers (repeated text)
        has_headers_footers = False
        if len(lines) > 10:
            header_signature = " ".join(line.strip() for line in lines[:3])
            footer_signature = " ".join(line.strip() for line in lines[-3:])
            repeated_header = header_signature and text.count(header_signature) > 1
            repeated_footer = footer_signature and text.count(footer_signature) > 1
            has_headers_footers = repeated_header or repeated_footer
        
        # Check for bullet points (good for ATS)
        has_bullets = bool(re.search(r'[•\-\*]\s', text))
        
        return {
            'has_tables': has_tables,
            'excessive_formatting': excessive_formatting,
            'has_headers_footers': has_headers_footers,
            'has_bullets': has_bullets
        }
    
    @staticmethod
    def _calculate_ats_score(section_checks: Dict, contact_check: Dict, formatting_checks: Dict) -> float:
        """
        Calculate overall ATS compliance score (0-100).
        
        Args:
            section_checks: Section presence checks
            contact_check: Contact info checks
            formatting_checks: Formatting checks
            
        Returns:
            ATS score (0-100)
        """
        score = 0.0
        max_score = 100.0
        
        # Section checks (40 points)
        section_score = sum(section_checks.values()) / len(section_checks) * 40
        score += section_score
        
        # Contact info (30 points)
        if contact_check['complete']:
            contact_score = 30
        elif contact_check['has_email'] or contact_check['has_phone']:
            contact_score = 15
        else:
            contact_score = 0
        score += contact_score
        
        # Formatting (30 points)
        formatting_score = 30
        if formatting_checks['has_tables']:
            formatting_score -= 10
        if formatting_checks['excessive_formatting']:
            formatting_score -= 10
        if formatting_checks['has_headers_footers']:
            formatting_score -= 5
        if not formatting_checks['has_bullets']:
            formatting_score -= 5
        
        formatting_score = max(0, formatting_score)
        score += formatting_score
        
        return round(min(100.0, max(0.0, score)), 2)
    
    @staticmethod
    def _get_issues(section_checks: Dict, contact_check: Dict, formatting_checks: Dict) -> List[str]:
        """
        Generate list of ATS issues found.
        
        Args:
            section_checks: Section presence checks
            contact_check: Contact info checks
            formatting_checks: Formatting checks
            
        Returns:
            List of issue descriptions
        """
        issues = []
        
        # Missing sections
        for section, present in section_checks.items():
            if not present:
                issues.append(f"Missing {section.capitalize()} section")
        
        # Contact info issues
        if not contact_check['has_email']:
            issues.append("Missing email address")
        if not contact_check['has_phone']:
            issues.append("Missing phone number or phone format not detected")
        
        # Formatting issues
        if formatting_checks['has_tables']:
            issues.append("Contains table-like formatting (may not parse well in ATS)")
        if formatting_checks['excessive_formatting']:
            issues.append("Excessive special characters (may indicate complex formatting)")
        if formatting_checks['has_headers_footers']:
            issues.append("Contains headers/footers (may confuse ATS parsing)")
        if not formatting_checks['has_bullets']:
            issues.append("No bullet points found (bullets improve ATS readability)")
        
        return issues
    
    @staticmethod
    def _get_recommendations(section_checks: Dict, contact_check: Dict, formatting_checks: Dict) -> List[str]:
        """
        Generate recommendations for improving ATS compliance.
        
        Args:
            section_checks: Section presence checks
            contact_check: Contact info checks
            formatting_checks: Formatting checks
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Section recommendations
        if not section_checks['education']:
            recommendations.append("Add an Education section with your academic background")
        if not section_checks['experience']:
            recommendations.append("Add an Experience section detailing your work history")
        if not section_checks['skills']:
            recommendations.append("Add a Skills section listing your technical and soft skills")
        
        # Contact recommendations
        if not contact_check['has_email']:
            recommendations.append("Include a professional email address")
        if not contact_check['has_phone']:
            recommendations.append("Include a phone number")
        
        # Formatting recommendations
        if formatting_checks['has_tables']:
            recommendations.append("Avoid using tables or multi-column layouts; use simple text formatting instead")
        if not formatting_checks['has_bullets']:
            recommendations.append("Use bullet points to improve readability and ATS parsing")
        
        recommendations.append("Use standard fonts (Arial, Times New Roman, Calibri)")
        recommendations.append("Save as PDF to preserve formatting")
        recommendations.append("Use keywords from the job description naturally throughout your resume")
        
        return recommendations

    @staticmethod
    def _find_headings(text: str) -> List[str]:
        headings = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if ATSChecker._looks_like_heading(stripped):
                headings.append(stripped)
        return headings

    @staticmethod
    def _looks_like_heading(line: str) -> bool:
        if len(line.split()) > 8:
            return False
        if line.endswith(':'):
            return True
        if line.isupper() and len(line) >= 3:
            return True
        return bool(re.match(r'^[A-Za-z0-9 &/+-]+$', line)) and line == line.title()


