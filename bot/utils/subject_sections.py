"""
Subject sections data structure for Uzbek educational system
Contains subject names and their corresponding sections
"""

SUBJECT_SECTIONS = {
    'Matematika': [
        'Algebra',
        'Geometriya'
    ],
    'Fizika': [
        'Mexanika',
        'Molekulyar fizika va termodinamika',
        'Elektr va magnitizm',
        'Zamonaviy fizika va optika',
        'Amaliy hayot va mantiqiy fikrlashga oid masalalar'
    ],
    'Ona tili': [
        'Tilshunoslik nazariyasi',
        'Adabiyot nazariyasi va adabiyot tarixi',
        'O\'qish savodxonligi',
        'Lingvistika va badiiy tahlil'
    ],
    'Tarix': [
        'Qadimgi davr',
        'O\'rta asrlar davri',
        'Yangi davr',
        'Eng yangi davr'
    ],
    'Kimyo': [
        'Umumiy kimyo',
        'Anorganik kimyo',
        'Organik kimyo',
        'Kimyoviy tahlil'
    ],
    'Biologiya': [
        'Sitologiya',
        'Genetika va seleksiya asoslari',
        'Organizmlarning xilma-xilligi',
        'Evolutsiya ekologiya va biosfera asoslari'
    ],
    'Geografiya': [
        'Tabiiy geografiya',
        'Iqtisodiy-ijtimoiy geografiya',
        'Geografik haritalar',
        'Mantiqiy va hayotiy test topshiriqlari'
    ],
    'Rus tili': [
        'Русский язык',
        'Литературе',
        'Читательская грамотность',
        'Результаты тестовых испытаний',
        'Письменная грамотность'
    ],
    'Qoraqalpoq tili': [
        'Tilshunoslik nazariyasi',
        'Adabiyot nazariyasi va adabiyot tarixi',
        'O\'qish savodxonligi',
        'Lingvistika va badiiy tahlil'
    ]
}

def get_sections(subject: str) -> list:
    """
    Get sections for a given subject
    
    Args:
        subject: Subject name (e.g., 'Matematika', 'Fizika')
        
    Returns:
        List of section names for the subject
    """
    return SUBJECT_SECTIONS.get(subject, [])

def has_sections(subject: str) -> bool:
    """
    Check if a subject has defined sections
    
    Args:
        subject: Subject name
        
    Returns:
        True if subject has sections defined, False otherwise
    """
    return subject in SUBJECT_SECTIONS and len(SUBJECT_SECTIONS[subject]) > 0

def get_all_subjects() -> list:
    """
    Get list of all subjects with defined sections
    
    Returns:
        List of subject names
    """
    return list(SUBJECT_SECTIONS.keys())
