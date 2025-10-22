from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from typing import Dict, Any
import os
from datetime import datetime


class PDFReportGenerator:
    """Generates PDF reports for Rasch model analysis results"""
    
    def __init__(self, output_dir: str = "data/results"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
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
        
        # Add individual person statistics table
        story.append(Paragraph("Individual Person Statistics", heading_style))
        
        person_stats = results.get('person_statistics', {})
        individual_data = person_stats.get('individual', [])
        
        if individual_data:
            # Sort by T-Score in descending order (highest first)
            individual_data_sorted = sorted(
                individual_data, 
                key=lambda x: x['t_score'] if not np.isnan(x['t_score']) else -999,
                reverse=True
            )
            
            # Create table header with rank
            person_table_data = [['Rank', 'ID', 'Raw Score', 'Ability (θ)', 'Z-Score', 'T-Score', 'SE']]
            
            # Add data for each person with rank
            for rank, person in enumerate(individual_data_sorted, start=1):
                person_table_data.append([
                    str(rank),
                    str(person['person_id']),
                    str(person['raw_score']),
                    f"{person['ability']:.3f}" if not np.isnan(person['ability']) else "N/A",
                    f"{person['z_score']:.3f}" if not np.isnan(person['z_score']) else "N/A",
                    f"{person['t_score']:.1f}" if not np.isnan(person['t_score']) else "N/A",
                    f"{person['se']:.3f}" if not np.isnan(person['se']) else "N/A"
                ])
            
            person_table = Table(person_table_data, colWidths=[0.5*inch, 0.5*inch, 0.85*inch, 0.95*inch, 0.85*inch, 0.85*inch, 0.65*inch])
            person_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E74C3C')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ECF0F1')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')])
            ]))
            story.append(person_table)
            
            # Add legend/explanation
            story.append(Spacer(1, 0.2 * inch))
            legend_text = (
                "<b>Tushuntirish:</b><br/>"
                "• <b>Rank:</b> O'rin (T-Score bo'yicha tartiblangan, eng yuqoridan boshlab)<br/>"
                "• <b>ID:</b> Talabgor raqami<br/>"
                "• <b>Raw Score:</b> To'g'ri javoblar soni<br/>"
                "• <b>Ability (θ):</b> Qobiliyat darajasi (logit o'lchovi)<br/>"
                "• <b>Z-Score:</b> Standart ball (o'rtacha=0, standart og'ish=1)<br/>"
                "• <b>T-Score:</b> T-ball (o'rtacha=50, standart og'ish=10)<br/>"
                "• <b>SE:</b> Standart xato (ability baholashning aniqlik darajasi)"
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
            "Report generated using Rasch Model Analysis (MML Estimation)",
            footer_style
        ))
        
        doc.build(story)
        
        return filepath
