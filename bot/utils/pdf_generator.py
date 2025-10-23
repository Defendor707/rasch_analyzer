from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from typing import Dict, Any, List
import os
from datetime import datetime
import numpy as np


class PDFReportGenerator:
    """Generates PDF reports for Rasch model analysis results"""

    def __init__(self, output_dir: str = "data/results"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def _calculate_section_scores(self, results: Dict[str, Any], section_questions: Dict[str, List[int]]) -> Dict[str, List[Dict]]:
        """
        Calculate T-scores for each section based on question numbers
        Section T-scores are normalized so their sum equals the overall T-score
        
        Args:
            results: Analysis results dictionary
            section_questions: Dict mapping section names to question numbers (1-indexed)
            
        Returns:
            Dict mapping section names to list of person scores
        """
        if not section_questions:
            return {}
        
        # Get the original response data from results
        person_stats = results.get('person_statistics', {})
        individual_data = person_stats.get('individual', [])
        
        if not individual_data:
            return {}
        
        n_persons = len(individual_data)
        n_items = results.get('n_items', 0)
        
        # Get response matrix
        response_matrix = results.get('response_matrix')
        if response_matrix is None:
            return {}
        
        # First pass: collect all section raw scores for each person
        section_names = list(section_questions.keys())
        all_section_data = {section_name: [] for section_name in section_names}
        
        for section_name, question_nums in section_questions.items():
            if not question_nums:
                continue
            
            # Convert 1-indexed to 0-indexed
            question_indices = [q - 1 for q in question_nums if 0 < q <= n_items]
            
            if not question_indices:
                continue
            
            # Calculate raw scores for this section for all persons
            for person_idx in range(n_persons):
                section_responses = response_matrix[person_idx, question_indices]
                section_raw_score = int(np.sum(section_responses))
                
                all_section_data[section_name].append({
                    'person_id': person_idx + 1,
                    'raw_score': section_raw_score,
                    'max_score': len(question_indices),
                    't_score': 0.0  # Will be calculated in second pass
                })
        
        # Second pass: normalize T-scores so they sum to overall T-score
        for person_idx in range(n_persons):
            overall_t_score = individual_data[person_idx]['t_score']
            
            # Collect raw scores from all VALID sections for this person
            valid_sections = []
            section_raw_scores = []
            for section_name in section_names:
                if section_name in all_section_data and person_idx < len(all_section_data[section_name]):
                    valid_sections.append(section_name)
                    section_raw_scores.append(all_section_data[section_name][person_idx]['raw_score'])
            
            # Calculate sum of raw scores
            sum_section_raw = sum(section_raw_scores)
            
            # Normalize: distribute overall T-score proportionally
            if sum_section_raw > 0:
                # Proportional distribution
                for i, section_name in enumerate(valid_sections):
                    section_t = overall_t_score * (section_raw_scores[i] / sum_section_raw)
                    all_section_data[section_name][person_idx]['t_score'] = float(section_t)
            else:
                # All section scores are 0, distribute equally among VALID sections only
                n_valid_sections = len(valid_sections)
                equal_t = overall_t_score / n_valid_sections if n_valid_sections > 0 else 0.0
                for section_name in valid_sections:
                    all_section_data[section_name][person_idx]['t_score'] = float(equal_t)
        
        return all_section_data

    def generate_report(self, results: Dict[str, Any], filename: str = None) -> str:
        """
        Generate PDF report from Rasch analysis results

        Args:
            results: Dictionary containing analysis results
            filename: Optional filename (without extension)

        Returns:
            Path to generated PDF file
        """
        if filename is None:
            filename = f"rasch_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if not filename.endswith('.pdf'):
            filename = filename + '.pdf'

        filepath = os.path.join(self.output_dir, filename)

        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18,
        )

        story = []

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2C3E50'),
            spaceAfter=30,
            alignment=TA_CENTER
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#34495E'),
            spaceAfter=12,
            spaceBefore=12
        )

        story.append(Paragraph("Rasch Model Analysis Report", title_style))
        story.append(Spacer(1, 0.2 * inch))

        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        story.append(Spacer(1, 0.3 * inch))

        story.append(Paragraph("Sample Information", heading_style))
        sample_data = [
            ["Number of Persons:", str(results['n_persons'])],
            ["Number of Items:", str(results['n_items'])],
            ["Reliability:", f"{results['reliability']:.3f}"]
        ]
        sample_table = Table(sample_data, colWidths=[3*inch, 2*inch])
        sample_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ECF0F1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2C3E50')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        story.append(sample_table)
        story.append(Spacer(1, 0.3 * inch))

        story.append(Paragraph("Item Difficulty Parameters", heading_style))

        item_data = [['Item', 'Difficulty', 'Mean Score']]
        for i, item_name in enumerate(results['item_names']):
            difficulty = results['item_difficulty'][i]
            mean = results['descriptive_stats']['item_means'][item_name]
            item_data.append([
                str(item_name),
                f"{difficulty:.3f}",
                f"{mean:.3f}"
            ])

        item_table = Table(item_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
        item_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498DB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ECF0F1')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')])
        ]))
        story.append(item_table)
        story.append(Spacer(1, 0.3 * inch))

        story.append(Paragraph("Person Ability Distribution", heading_style))

        import numpy as np
        abilities = results['person_ability']
        valid_abilities = abilities[~np.isnan(abilities)]

        if len(valid_abilities) > 0:
            ability_stats = [
                ['Statistic', 'Value'],
                ['Mean', f"{np.mean(valid_abilities):.3f}"],
                ['Standard Deviation', f"{np.std(valid_abilities):.3f}"],
                ['Minimum', f"{np.min(valid_abilities):.3f}"],
                ['Maximum', f"{np.max(valid_abilities):.3f}"],
            ]

            ability_table = Table(ability_stats, colWidths=[2.5*inch, 1.5*inch])
            ability_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2ECC71')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ECF0F1')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
            ]))
            story.append(ability_table)
        else:
            story.append(Paragraph("No valid person abilities calculated.", styles['Normal']))

        story.append(Spacer(1, 0.4 * inch))

        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER
        )
        story.append(Paragraph(
            "Report generated using Rasch Model Analysis (MML Estimation)",
            footer_style
        ))

        doc.build(story)

        return filepath

    def generate_person_results_report(self, results: Dict[str, Any], filename: str = None, section_questions: Dict[str, list] = None) -> str:
        """
        Generate separate PDF report for individual person results only

        Args:
            results: Dictionary containing analysis results
            filename: Optional filename (without extension)
            section_questions: Optional dict mapping section names to question numbers

        Returns:
            Path to generated PDF file
        """
        if filename is None:
            filename = f"person_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if not filename.endswith('.pdf'):
            filename = filename + '.pdf'

        filepath = os.path.join(self.output_dir, filename)

        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18,
        )

        story = []

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2C3E50'),
            spaceAfter=30,
            alignment=TA_CENTER
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#34495E'),
            spaceAfter=12,
            spaceBefore=12
        )

        story.append(Paragraph("Talabgorlar Natijalari", title_style))
        story.append(Spacer(1, 0.2 * inch))

        story.append(Paragraph(f"Yaratilgan: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        story.append(Spacer(1, 0.3 * inch))

        # Add person count info
        story.append(Paragraph("Ma'lumotlar", heading_style))
        info_data = [
            ["Talabgorlar soni:", str(results['n_persons'])],
            ["Savollar soni:", str(results['n_items'])]
        ]
        info_table = Table(info_data, colWidths=[3*inch, 2*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ECF0F1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2C3E50')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.4 * inch))

        # Calculate section scores if provided
        section_scores = {}
        if section_questions:
            section_scores = self._calculate_section_scores(results, section_questions)
        
        # Individual person statistics table
        if section_scores:
            story.append(Paragraph("Talabgorlar Natijalari - Bo'limlar bo'yicha (T-Score bo'yicha tartiblangan)", heading_style))
        else:
            story.append(Paragraph("Talabgorlar Natijalari (T-Score bo'yicha tartiblangan)", heading_style))

        person_stats = results.get('person_statistics', {})
        individual_data = person_stats.get('individual', [])

        if individual_data:
            # Sort by T-Score in descending order (highest first)
            individual_data_sorted = sorted(
                individual_data,
                key=lambda x: x['t_score'] if not np.isnan(x['t_score']) else -999,
                reverse=True
            )

            # Create table header dynamically based on whether we have sections
            if section_scores:
                # Create header with section columns
                section_names = list(section_scores.keys())
                header = ['Rank', 'Talabgor', 'Raw Score', 'T-Score Umumiy']
                for section_name in section_names:
                    # Truncate long section names
                    short_name = section_name[:15] + '...' if len(section_name) > 15 else section_name
                    header.append(f"{short_name}\n(T-Score)")
                header.extend(['Foiz', 'Daraja'])
                
                person_table_data = [header]
                
                # Calculate column widths dynamically
                n_sections = len(section_names)
                base_width = 6.5 * inch  # Total available width
                section_col_width = min(0.9*inch, (base_width - 3.5*inch) / (n_sections + 2))
                col_widths = [0.4*inch, 0.9*inch, 0.7*inch, 0.8*inch] + [section_col_width] * n_sections + [0.6*inch, 0.5*inch]
            else:
                # Original header without sections
                person_table_data = [['Rank', 'Talabgor', 'Raw Score', 'Ability (θ)', 'T-Score', 'Foiz', 'Daraja']]
                col_widths = [0.6*inch, 1.1*inch, 0.9*inch, 0.9*inch, 0.9*inch, 0.8*inch, 0.7*inch]

            # Add data for each person with rank
            for rank, person in enumerate(individual_data_sorted, start=1):
                # Calculate percentage from T-Score
                t_score = person['t_score']
                if not np.isnan(t_score):
                    percentage = (t_score / 65) * 100
                    # Cap percentage: below 70% = 0%, above 100% = 100%
                    if percentage > 100:
                        percentage = 100.0
                    elif percentage < 70:
                        percentage = 0.0
                    percentage_str = f"{percentage:.1f}%"
                    
                    # Determine grade based on T-Score (UZBMB standards)
                    if t_score >= 70:
                        grade = "A+"
                    elif t_score >= 65:
                        grade = "A"
                    elif t_score >= 60:
                        grade = "B+"
                    elif t_score >= 55:
                        grade = "B"
                    elif t_score >= 50:
                        grade = "C+"
                    elif t_score >= 46:
                        grade = "C"
                    else:
                        grade = "NC"
                else:
                    percentage_str = "N/A"
                    grade = "N/A"
                
                if section_scores:
                    # Row with section T-scores
                    row = [
                        str(rank),
                        f"Talabgor {person['person_id']}",
                        str(person['raw_score']),
                        f"{person['t_score']:.1f}" if not np.isnan(person['t_score']) else "N/A"
                    ]
                    
                    # Add section T-scores for this person
                    person_id = person['person_id']
                    for section_name in section_names:
                        section_data = section_scores[section_name]
                        # Find this person's data in the section
                        person_section = next((p for p in section_data if p['person_id'] == person_id), None)
                        if person_section:
                            row.append(f"{person_section['t_score']:.1f}")
                        else:
                            row.append("N/A")
                    
                    row.extend([percentage_str, grade])
                else:
                    # Original row format
                    row = [
                        str(rank),
                        f"Talabgor {person['person_id']}",
                        str(person['raw_score']),
                        f"{person['ability']:.3f}" if not np.isnan(person['ability']) else "N/A",
                        f"{person['t_score']:.1f}" if not np.isnan(person['t_score']) else "N/A",
                        percentage_str,
                        grade
                    ]
                
                person_table_data.append(row)

            person_table = Table(person_table_data, colWidths=col_widths)
            person_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E74C3C')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),


    def generate_section_results_report(self, results: Dict[str, Any], filename: str = None, section_questions: Dict[str, list] = None) -> str:
        """
        Generate separate PDF report for section-based results only

        Args:
            results: Dictionary containing analysis results
            filename: Optional filename (without extension)
            section_questions: Dict mapping section names to question numbers

        Returns:
            Path to generated PDF file
        """
        if filename is None:
            filename = f"section_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if not filename.endswith('.pdf'):
            filename = filename + '.pdf'

        filepath = os.path.join(self.output_dir, filename)

        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18,
        )

        story = []

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2C3E50'),
            spaceAfter=30,
            alignment=TA_CENTER
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#34495E'),
            spaceAfter=12,
            spaceBefore=12
        )

        story.append(Paragraph("Bo'limlar bo'yicha natijalar", title_style))
        story.append(Spacer(1, 0.2 * inch))

        story.append(Paragraph(f"Yaratilgan: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        story.append(Spacer(1, 0.3 * inch))

        # Add person count info
        story.append(Paragraph("Ma'lumotlar", heading_style))
        info_data = [
            ["Talabgorlar soni:", str(results['n_persons'])],
            ["Savollar soni:", str(results['n_items'])]
        ]
        info_table = Table(info_data, colWidths=[3*inch, 2*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ECF0F1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2C3E50')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.4 * inch))

        # Calculate section scores
        section_scores = {}
        if section_questions:
            section_scores = self._calculate_section_scores(results, section_questions)
        
        if not section_scores:
            story.append(Paragraph("Bo'limlar ma'lumotlari topilmadi.", styles['Normal']))
        else:
            story.append(Paragraph("Bo'limlar bo'yicha natijalar (T-Score bo'yicha tartiblangan)", heading_style))

            person_stats = results.get('person_statistics', {})
            individual_data = person_stats.get('individual', [])

            if individual_data:
                # Sort by overall T-Score in descending order
                individual_data_sorted = sorted(
                    individual_data,
                    key=lambda x: x['t_score'] if not np.isnan(x['t_score']) else -999,
                    reverse=True
                )

                # Create header with section columns
                section_names = list(section_scores.keys())
                header = ['Rank', 'Talabgor', 'T-Score Umumiy']
                for section_name in section_names:
                    # Truncate long section names
                    short_name = section_name[:20] + '...' if len(section_name) > 20 else section_name
                    header.append(f"{short_name}\n(T-Score)")
                
                person_table_data = [header]
                
                # Calculate column widths dynamically
                n_sections = len(section_names)
                base_width = 6.5 * inch  # Total available width
                section_col_width = min(1.2*inch, (base_width - 2.5*inch) / n_sections)
                col_widths = [0.5*inch, 1.0*inch, 1.0*inch] + [section_col_width] * n_sections

                # Add data for each person
                for rank, person in enumerate(individual_data_sorted, start=1):
                    row = [
                        str(rank),
                        f"Talabgor {person['person_id']}",
                        f"{person['t_score']:.1f}" if not np.isnan(person['t_score']) else "N/A"
                    ]
                    
                    # Add section T-scores for this person
                    person_id = person['person_id']
                    for section_name in section_names:
                        section_data = section_scores[section_name]
                        # Find this person's data in the section
                        person_section = next((p for p in section_data if p['person_id'] == person_id), None)
                        if person_section:
                            row.append(f"{person_section['t_score']:.1f}")
                        else:
                            row.append("N/A")
                    
                    person_table_data.append(row)

                person_table = Table(person_table_data, colWidths=col_widths)
                person_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498DB')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ECF0F1')),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('FONTSIZE', (0, 1), (-1, -1), 7),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')])
                ]))
                story.append(person_table)

                # Add section information summary
                story.append(Spacer(1, 0.3 * inch))
                story.append(Paragraph("Bo'limlar ma'lumotlari", heading_style))
                
                section_info_data = [['Bo\'lim', 'Savol raqamlari', 'Savollar soni']]
                for section_name, question_nums in section_questions.items():
                    if question_nums:
                        formatted_questions = format_question_list(question_nums)
                        section_info_data.append([
                            section_name,
                            formatted_questions,
                            str(len(question_nums))
                        ])
                
                section_info_table = Table(section_info_data, colWidths=[2.5*inch, 2.5*inch, 1.0*inch])
                section_info_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2ECC71')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ECF0F1')),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')])
                ]))
                story.append(section_info_table)

                # Add legend/explanation
                story.append(Spacer(1, 0.2 * inch))
                legend_text = (
                    "<b>Tushuntirish:</b><br/>"
                    "• <b>Rank:</b> O'rin (Umumiy T-Score bo'yicha tartiblangan)<br/>"
                    "• <b>Talabgor:</b> Talabgor identifikatori<br/>"
                    "• <b>T-Score Umumiy:</b> Umumiy T-ball (o'rtacha=50, standart og'ish=10)<br/>"
                    "• <b>Bo'lim T-Score:</b> Har bir bo'lim uchun T-ball<br/>"
                    "• Bo'lim T-balllari yig'indisi umumiy T-ballga teng<br/>"
                    "• T-ball formulasi: section_t = overall_t × (section_raw / sum_section_raw)"
                )
                story.append(Paragraph(legend_text, styles['Normal']))

        story.append(Spacer(1, 0.4 * inch))

        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER
        )
        story.append(Paragraph(
            "Rasch Model Tahlili - Bo'limlar bo'yicha natijalar",
            footer_style
        ))

        doc.build(story)

        return filepath

                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ECF0F1')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')])
            ]))
            story.append(person_table)

            # Add legend/explanation
            story.append(Spacer(1, 0.2 * inch))
            if section_scores:
                legend_text = (
                    "<b>Tushuntirish:</b><br/>"
                    "• <b>Rank:</b> O'rin (T-Score umumiy bo'yicha tartiblangan)<br/>"
                    "• <b>Talabgor:</b> Talabgor identifikatori<br/>"
                    "• <b>Raw Score:</b> Umumiy to'g'ri javoblar soni<br/>"
                    "• <b>T-Score Umumiy:</b> Umumiy T-ball (o'rtacha=50, standart og'ish=10)<br/>"
                    "• <b>Bo'lim T-Score:</b> Har bir bo'lim uchun T-ball<br/>"
                    "• <b>Foiz:</b> Natija foizda (T-Score/65 × 100)<br/>"
                    "• <b>Daraja:</b> UZBMB standarti (A+≥70, A≥65, B+≥60, B≥55, C+≥50, C≥46, NC&lt;46)"
                )
            else:
                legend_text = (
                    "<b>Tushuntirish:</b><br/>"
                    "• <b>Rank:</b> O'rin (T-Score bo'yicha tartiblangan, eng yuqoridan boshlab)<br/>"
                    "• <b>Talabgor:</b> Talabgor identifikatori<br/>"
                    "• <b>Raw Score:</b> To'g'ri javoblar soni<br/>"
                    "• <b>Ability (θ):</b> Qobiliyat darajasi (logit o'lchovi)<br/>"
                    "• <b>T-Score:</b> T-ball (o'rtacha=50, standart og'ish=10)<br/>"
                    "• <b>Foiz:</b> Natija foizda (T-Score/65 × 100)<br/>"
                    "• <b>Daraja:</b> UZBMB standarti (A+≥70, A≥65, B+≥60, B≥55, C+≥50, C≥46, NC&lt;46)"
                )
            story.append(Paragraph(legend_text, styles['Normal']))

        story.append(Spacer(1, 0.4 * inch))

        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER
        )
        story.append(Paragraph(
            "Rasch Model Tahlili - Talabgorlar Natijalari",
            footer_style
        ))

        doc.build(story)

        return filepath