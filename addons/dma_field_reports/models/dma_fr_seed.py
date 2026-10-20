"""Built-in translations from the words operators use to the values IMSMA stores.

Arabic labels come from the DMA EORE Word form (Sep 2026); targets are the exact
texts IMSMA NG has stored for these custom fields (2025-03-02 backup). Choices
IMSMA has never stored ("Free Business", "Shepherds"...) are left for a person to
map once in the fix dialog.

Created by code, not XML, so an upgrade never fails on a text a user has
already mapped (the mapping is unique per field and text).
"""
from ..services import text

ACTIVITY = "c0a8-00a2-1307eaec3d1-37d76cff-6c-66b"
AWARENESS = "c0a8-429c-1524042ff34-acafed6d-e89-45"
MRE_TYPE = "7f00-0001-13f7a2fa1c2-3963ba9f-39-b37"
MRE_SUBTYPE = "7f00-0001-13f7a2f797a-7f9d8df5-b-99ae"
AUDIENCE = "7f00-0001-13f7a2f8f6a-74bbbd46-28-907"
REMOTE = "c0a7-f58e-17744186186-c50dcf38-a-7b29"
MAC = "c0a7-f58e-1773eacedb7-ef3a9ab4-10-dff"

SEEDS = [
    (ACTIVITY, "توعية ضمن شؤون الألغام", "Mine Action Risk Education"),
    (ACTIVITY, "إعادة تأهيل البنى التحتية", "Infrastructure Rehabilitation"),
    (ACTIVITY, "توعية بعد أعمال المسح والإزالة (الاطمئنان الشخصي)", "Post Survey and Clearance RE (Self-confidence)"),
    (ACTIVITY, "عودة لاجئين/مرحلين/ اعادة توطين", "Refugee/Returnee/IDP/Resettlement"),
    (AWARENESS, "قنابل عنقودية", "Cluster Munitions"),
    (AWARENESS, "مخلفات حربية", "ERW"),
    (AWARENESS, "عبوات ناسفة", "IED"),
    (AWARENESS, "حقول الغام", "Landmine"),
    (MRE_TYPE, "عرض توضيحي", "Presentation"),
    (MRE_TYPE, "تدريب", "Training"),
    (MRE_TYPE, "الاعلام", "Media"),
    (MRE_TYPE, "أداء شعبي", "Public Performance"),
    (MRE_TYPE, "إتصال مجتمعي", "Community liaison"),
    (MRE_TYPE, "تعليم", "Education"),
    (MRE_SUBTYPE, "الإعلام", "Media"),
    (MRE_SUBTYPE, "الراديو", "Radio"),
    (MRE_SUBTYPE, "فيديو", "Video"),
    (MRE_SUBTYPE, "توزيع مواد", "Material distribution"),
    (MRE_SUBTYPE, "نصب أوصيانة العلامات واللوحات", "Marking maintenance"),
    (MRE_SUBTYPE, "تدريب المتطوعين", "Volunteers"),
    (MRE_SUBTYPE, "خريطة المجتمع", "Community mapping"),
    (MRE_SUBTYPE, "من صديق الى صديق", "Peer-to-peer"),
    (MRE_SUBTYPE, "تسليم الأرض المطهرة", "Minefield handover"),
    (MRE_SUBTYPE, "اجراءات السلامة", "Safety briefing"),
    (MRE_SUBTYPE, "الموسيقى", "Music"),
    (MRE_SUBTYPE, "محاضرات / صفوف/ ندوات تثقيفية", "Lecture/Classroom/Educational Seminars"),
    (MRE_SUBTYPE, "Lecture/Classroom/Educational seminars", "Lecture/Classroom/Educational Seminars"),
    (MRE_SUBTYPE, "من طفل الى طفل", "Child-to-child"),
    (MRE_SUBTYPE, "التلفزيون", "TV"),
    (MRE_SUBTYPE, "دعم لإزالة الألغام والمسح", "Support to demining"),
    (MRE_SUBTYPE, "تأهيل قادة المجتمع", "Community mobilisation"),
    (MRE_SUBTYPE, "المدرسة", "School"),
    (MRE_SUBTYPE, "مسرح", "Theater"),
    (MRE_SUBTYPE, "الفعاليات والأنشطة الرياضية المختلفة", "Sport Activities"),
    (MRE_SUBTYPE, "مواقع التواصل الاجتماعي", "Social Media"),
    (MRE_SUBTYPE, "أخرى", "Other"),
    (AUDIENCE, "اشخاص عرضة للخطر", "At risk population"),
    (AUDIENCE, "عاملين في النفط", "Oil filed Companies"),
    (AUDIENCE, "مجموعة النساء", "Women's group"),
    (AUDIENCE, "عاملين في الصحة", "Health worker"),
    (AUDIENCE, "مدارس/جامعات", "School/Collage"),
    (AUDIENCE, "School/college", "School/Collage"),
    (AUDIENCE, "المنظمات غير الدولية", "NGO"),
    (AUDIENCE, "ممثلي المجتمع", "Community representative"),
    (AUDIENCE, "Representatives of society", "Community representative"),
    (AUDIENCE, "موظفين الشباب والرياضة", "Youth Center"),
    (AUDIENCE, "عاملين في مجال الألغام", "Mine action personnel"),
    (AUDIENCE, "غير ذلك", "Other"),
    (AUDIENCE, "موظف حكومي", "Government official"),
    (AUDIENCE, "مختلط", "Mixed"),
    (AUDIENCE, "جيش", "Military"),
    (AUDIENCE, "المتطوعين", "Volunteer"),
    (AUDIENCE, "Volunteers", "Volunteer"),
    (REMOTE, "النشاط الإعلامي السمعي", "Audio"),
    (REMOTE, "النشاط الإعلامي المرئي", "Visual"),
    (REMOTE, "الرسائل النصية", "SMS"),
    (MAC, "RMAC-North", "RMAC-N"),
    (MAC, "RMAC-South", "RMAC-S"),
    (MAC, "RMAC-Central", "RMAC-C"),
]


def seed_value_maps(env):
    """Create the built-in mappings that are not there yet (never overwrites a person's mapping)."""
    Map = env["dma.fr.value.map"].with_context(active_test=False)
    existing = {(m.scope, m.source_norm) for m in Map.search([])}
    new = []
    for scope, source, target in SEEDS:
        key = (scope, text.norm(source))
        if key not in existing:
            existing.add(key)
            new.append({"scope": scope, "source_value": source, "target_value": target, "origin": "seeded"})
    return Map.create(new)
