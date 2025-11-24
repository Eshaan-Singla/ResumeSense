"""
Resume insights helper.
Extracts project and achievement/co-curricular highlights from resume text.
"""
import re
from typing import Dict, List, Set


class ResumeInsights:
    """Extract structured information (projects, achievements) from resume text."""

    PROJECT_KEYWORDS = {
        'project', 'projects', 'capstone', 'portfolio', 'application', 'app',
        'tool', 'platform', 'system', 'product', 'prototype', 'solution',
        'hackathon', 'case study', 'research project', 'module', 'feature'
    }

    ACHIEVEMENT_KEYWORDS = {
        'award', 'awarded', 'honor', 'honours', 'recognition', 'recognized',
        'certification', 'certified', 'achievement', 'achievements',
        'winner', 'won', 'finalist', 'runner-up', 'placed', 'scholarship',
        'publication', 'published', 'speaker', 'presented', 'selected'
    }

    CO_CURRICULAR_KEYWORDS = {
        'club', 'society', 'association', 'organization', 'organised',
        'organized', 'volunteer', 'volunteered', 'leadership', 'captain',
        'coach', 'mentor', 'event', 'festival', 'competition', 'contest',
        'sports', 'athletics', 'cultural', 'music', 'dance', 'drama',
        'community', 'campus', 'co-curricular', 'extracurricular'
    }

    TECH_TERMS: Set[str] = {
        # Languages
        'python', 'java', 'javascript', 'typescript', 'c++', 'cpp', 'c#',
        'csharp', 'go', 'golang', 'rust', 'swift', 'kotlin', 'scala',
        'ruby', 'php', 'r', 'matlab', 'sql', 'nosql', 'html', 'css',
        # Frameworks
        'react', 'angular', 'vue', 'django', 'flask', 'spring', 'express',
        'node', 'nodejs', 'fastapi', 'nextjs', 'nuxt', 'laravel', 'rails',
        # Data / ML
        'pandas', 'numpy', 'scikit-learn', 'sklearn', 'tensorflow',
        'pytorch', 'keras', 'matplotlib', 'seaborn', 'spark', 'hadoop',
        'airflow', 'dbt',
        # Cloud / DevOps
        'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'helm', 'terraform',
        'ansible', 'jenkins', 'gitlab', 'github', 'bitbucket', 'ci/cd',
        # Databases
        'mysql', 'postgresql', 'postgres', 'mongodb', 'redis', 'dynamodb',
        'snowflake', 'bigquery', 'redshift', 'elastic', 'elasticsearch'
    }

    PROJECT_SECTION_HEADERS = [
        'project', 'projects', 'project experience', 'technical projects',
        'academic projects', 'capstone', 'portfolio'
    ]

    ACHIEVEMENT_SECTION_HEADERS = [
        'achievement', 'achievements', 'awards', 'honors', 'honours',
        'recognition', 'leadership', 'activities', 'co-curricular',
        'extracurricular', 'volunteer', 'volunteering'
    ]

    @staticmethod
    def extract_insights(resume_text: str) -> Dict[str, List[Dict]]:
        """
        Extract projects and achievements/co-curricular activities.

        Args:
            resume_text: Full resume text.

        Returns:
            Dictionary with projects and achievements lists.
        """
        sentences = ResumeInsights._split_sentences(resume_text)
        projects = ResumeInsights._extract_projects(resume_text, sentences)
        achievements = ResumeInsights._extract_achievements(resume_text, sentences)

        return {
            'projects': projects[:5],
            'achievements': achievements[:5]
        }

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        """Split resume text into sentences/clauses while keeping bullets."""
        # Replace bullet characters with periods for easier splitting
        normalized = re.sub(r'[•▪●◦]', '. ', text)
        normalized = re.sub(r'\s+', ' ', normalized)
        parts = re.split(r'(?<=[\.\!\?])\s+', normalized)
        return [part.strip() for part in parts if len(part.strip()) > 25]

    @staticmethod
    def _extract_projects(resume_text: str, sentences: List[str]) -> List[Dict]:
        projects = []
        seen_titles = set()

        # Prefer explicit project sections
        section_blocks = ResumeInsights._extract_section_blocks(
            resume_text,
            ResumeInsights.PROJECT_SECTION_HEADERS
        )

        for block in section_blocks:
            block_projects = ResumeInsights._parse_project_block(block)
            for project in block_projects:
                title_key = project['title'].lower()
                if title_key in seen_titles:
                    continue
                projects.append(project)
                seen_titles.add(title_key)

        # Fallback to sentence-level extraction only if sections were not found
        if not projects:
            for sentence in sentences:
                lower = sentence.lower()
                indicator_hits = sum(1 for kw in ResumeInsights.PROJECT_KEYWORDS if kw in lower)
                has_delimiters = '|' in sentence or ' - ' in sentence or ':' in sentence
                if indicator_hits == 0 or not has_delimiters:
                    continue

                tech_stack = ResumeInsights._extract_tech_stack(lower)
                if not tech_stack:
                    continue

                title = ResumeInsights._infer_project_title(sentence)
                if title.lower() in seen_titles:
                    continue

                confidence = min(1.0, 0.4 + min(len(sentence) / 300, 0.3))
                projects.append({
                    'title': title,
                    'summary': sentence.strip(),
                    'tech_stack': tech_stack,
                    'confidence': round(confidence, 2)
                })
                seen_titles.add(title.lower())

        projects.sort(key=lambda item: item['confidence'], reverse=True)
        return projects

    @staticmethod
    def _extract_achievements(resume_text: str, sentences: List[str]) -> List[Dict]:
        achievements = []
        seen = set()

        section_blocks = ResumeInsights._extract_section_blocks(
            resume_text,
            ResumeInsights.ACHIEVEMENT_SECTION_HEADERS
        )

        for block in section_blocks:
            block_items = ResumeInsights._parse_achievement_block(block)
            for item in block_items:
                key = item['title'].lower()
                if key in seen:
                    continue
                achievements.append(item)
                seen.add(key)

        if not achievements:
            for sentence in sentences:
                lower = sentence.lower()
                achievement_hits = sum(1 for kw in ResumeInsights.ACHIEVEMENT_KEYWORDS if kw in lower)
                co_curricular_hit = any(kw in lower for kw in ResumeInsights.CO_CURRICULAR_KEYWORDS)

                if achievement_hits == 0 and not co_curricular_hit:
                    continue

                title = ResumeInsights._infer_achievement_title(sentence)
                if title.lower() in seen:
                    continue

                category = 'Co-curricular' if co_curricular_hit else 'Achievement'
                impact_keywords = ResumeInsights._extract_impact_keywords(lower)

                achievements.append({
                    'title': title,
                    'details': sentence.strip(),
                    'category': category,
                    'impact_keywords': impact_keywords
                })
                seen.add(title.lower())

        achievements.sort(key=lambda item: 0 if item['category'] == 'Co-curricular' else 1)
        return achievements

    @staticmethod
    def _extract_tech_stack(text_lower: str) -> List[str]:
        stack = []
        for term in ResumeInsights.TECH_TERMS:
            normalized = term.lower()
            if re.search(r'\b{}\b'.format(re.escape(normalized)), text_lower):
                stack.append(term.upper() if term.isalpha() and len(term) <= 4 else term.title())
            elif normalized in text_lower and re.search(r'[^\w]', normalized):
                stack.append(term.upper() if term.isalpha() and len(term) <= 4 else term.title())
        return stack[:8]

    @staticmethod
    def _infer_project_title(sentence: str) -> str:
        match = re.search(r'(?:project|application|platform|system)\s*[:\-]\s*([A-Za-z0-9 ,&()\/\-]+)', sentence, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            return ResumeInsights._trim_title(candidate)

        # Use first clause as fallback
        clause = sentence.split(',')[0]
        clause = clause.split(' - ')[0]
        clause = clause.split('. ')[0]
        return ResumeInsights._trim_title(clause)

    @staticmethod
    def _infer_achievement_title(sentence: str) -> str:
        match = re.search(r'(?:awarded|won|received|recognized for)\s+([A-Za-z0-9 ,&()\/\-]+)', sentence, re.IGNORECASE)
        if match:
            return ResumeInsights._trim_title(match.group(1))

        clause = sentence.split('. ')[0]
        return ResumeInsights._trim_title(clause)

    @staticmethod
    def _trim_title(text: str) -> str:
        cleaned = re.sub(r'[^A-Za-z0-9 ,&()\/\-]', '', text).strip()
        if not cleaned:
            return "Highlighted Project"
        words = cleaned.split()
        return ' '.join(words[:10])

    @staticmethod
    def _extract_impact_keywords(text_lower: str) -> List[str]:
        impact_terms = [
            'led', 'organized', 'increased', 'reduced', 'boosted',
            'improved', 'mentored', 'trained', 'volunteered',
            'collaborated', 'presented', 'coordinated', 'hosted'
        ]
        hits = [term for term in impact_terms if term in text_lower]
        return hits[:5]

    @staticmethod
    def _extract_section_blocks(text: str, header_keywords: List[str]) -> List[str]:
        sections = []
        current_heading = None
        current_lines: List[str] = []

        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                if current_lines and current_lines[-1] != '':
                    current_lines.append('')
                continue

            if ResumeInsights._looks_like_heading(stripped):
                # Close previous section
                if current_heading and current_lines:
                    heading_lower = current_heading.lower()
                    sections.append((heading_lower, "\n".join(current_lines).strip()))
                current_heading = stripped
                current_lines = []
                continue

            if current_heading:
                current_lines.append(stripped)

        if current_heading and current_lines:
            sections.append((current_heading.lower(), "\n".join(current_lines).strip()))

        matched_sections = [
            content for heading, content in sections
            if any(keyword in heading for keyword in header_keywords)
        ]
        return matched_sections

    @staticmethod
    def _looks_like_heading(line: str) -> bool:
        if len(line) < 3 or len(line.split()) > 8:
            return False
        if line.endswith(':'):
            return True
        if line.isupper():
            return True
        return bool(re.match(r'^[A-Za-z0-9 &/+-]+$', line)) and line == line.title()

    @staticmethod
    def _parse_project_block(block: str) -> List[Dict]:
        projects = []
        entries = ResumeInsights._split_block_entries(block)

        for entry in entries:
            title = ResumeInsights._infer_project_title(entry)
            lower = entry.lower()
            tech_stack = ResumeInsights._extract_tech_stack(lower)
            metrics_present = bool(re.search(r'\b\d+(\.\d+)?%|\$\d+|\d+\+\b', entry))
            length_factor = min(len(entry) / 300, 1)

            confidence = 0.4
            if tech_stack:
                confidence += 0.2
            if metrics_present:
                confidence += 0.2
            confidence += 0.2 * length_factor

            projects.append({
                'title': title,
                'summary': entry.strip(),
                'tech_stack': tech_stack,
                'confidence': round(min(confidence, 0.99), 2)
            })

        return projects

    @staticmethod
    def _parse_achievement_block(block: str) -> List[Dict]:
        achievements = []
        entries = ResumeInsights._split_block_entries(block)

        for entry in entries:
            lower = entry.lower()
            category = 'Co-curricular' if any(kw in lower for kw in ResumeInsights.CO_CURRICULAR_KEYWORDS) else 'Achievement'
            title = ResumeInsights._infer_achievement_title(entry)
            impact_keywords = ResumeInsights._extract_impact_keywords(lower)

            achievements.append({
                'title': title,
                'details': entry.strip(),
                'category': category,
                'impact_keywords': impact_keywords
            })

        return achievements

    @staticmethod
    def _split_block_entries(block: str) -> List[str]:
        cleaned = block.replace('\r', '\n')
        cleaned = re.sub(r'[\u2022\u2023\u25E6\u2043]', '-', cleaned)
        lines = [line.rstrip() for line in cleaned.splitlines()]

        entries: List[str] = []
        current: List[str] = []

        def commit_entry():
            if current:
                merged = " ".join(part.strip() for part in current if part.strip())
                if len(merged.split()) >= 6:
                    entries.append(merged)
            return []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                current = commit_entry()
                continue

            if re.match(r'^[-*]\s+', stripped):
                current.append(stripped.lstrip('-* ').strip())
                continue

            starts_new_entry = ResumeInsights._starts_new_entry(stripped)
            if current and starts_new_entry:
                current = commit_entry()
                current = [stripped]
            elif not current:
                current = [stripped]
            else:
                current.append(stripped)

        commit_entry()
        return entries

    @staticmethod
    def _starts_new_entry(line: str) -> bool:
        if not line or re.match(r'^[-*]\s+', line):
            return False
        lower = line.lower()
        if '|' in line or line.isupper():
            return True
        if any(keyword in lower for keyword in (
            'project', 'capstone', 'hackathon', 'award', 'achievement',
            'leadership', 'club', 'society', 'competition'
        )):
            return True
        if re.search(r'\b20\d{2}\b', line):
            return True
        return False

