"""19.0.0.2.0: Arabic column headers for EORE, Arabic list translations.

The template data is noupdate (managers may edit it), so new headers are only written
where the column still has the headers shipped with 19.0.0.1.0.
"""
from odoo import SUPERUSER_ID, api

from odoo.addons.dma_field_reports.models.dma_fr_seed import seed_value_maps

HEADERS = {
    "eore_f01": [
        "Funded by",
        "Funded by\nالجهة الممولة\nاسم الجهة الممولة"
    ],
    "eore_f02": [
        "Date of report",
        "Date of report\nتاريخ التقرير"
    ],
    "eore_f03": [
        "Reported by",
        "Reported by\nأعد التقرير من قبل"
    ],
    "eore_f04": [
        "Position",
        "Position\nالموقع الوظيفي"
    ],
    "eore_f05": [
        "Organization\nOrganisation",
        "Organization\nOrganisation\nالجهة المنفذة"
    ],
    "eore_f06": [
        "Sub-contractor\nSubcontractor",
        "Sub-contractor\nSubcontractor\nالمتعاقد الثانوي"
    ],
    "eore_f07": [
        "Task dossier ID\nTask dossier",
        "Task dossier ID\nTask dossier\nرقم أمر العمل"
    ],
    "eore_f08": [
        "Location / Province\nProvince",
        "Location / Province\nProvince\nالمحافظة"
    ],
    "eore_f09": [
        "Location / District\nDistrict",
        "Location / District\nDistrict\nالقضاء"
    ],
    "eore_f10": [
        "Location / Subdistrict\nSubdistrict\nSub-district",
        "Location / Subdistrict\nSubdistrict\nSub-district\nالناحية"
    ],
    "eore_f11": [
        "Location / City/Town/Village\nCity/Town/Village\nCity",
        "Location / City/Town/Village\nCity/Town/Village\nCity\nالقرية / المدينة\nالمدينة / القرية\nالقرية"
    ],
    "eore_f12": [
        "Location / Location name\nLocation name",
        "Location / Location name\nLocation name\nاسم الموقع\nاسم موقع التوعية بمخاطر الذخائر والمواد المتفجرة"
    ],
    "eore_f13": [
        "Location / MGRS\nMGRS",
        "Location / MGRS\nMGRS\nMGRS Coord"
    ],
    "eore_f14": [
        "Location / Lat\nLat\nLatitude",
        "Location / Lat\nLat\nLatitude\nخطوط العرض\nخط العرض"
    ],
    "eore_f15": [
        "Location / Long\nLong\nLongitude",
        "Location / Long\nLong\nLongitude\nخطوط الطول\nخط الطول"
    ],
    "eore_f16": [
        "Planned start date",
        "Planned start date\nتاريخ المخطط للبدء"
    ],
    "eore_f17": [
        "Planned end date",
        "Planned end date\nتاريخ المخطط للانتهاء"
    ],
    "eore_f18": [
        "Actual start date",
        "Actual start date\nتاريخ البدء الفعلي"
    ],
    "eore_f19": [
        "Actual end date",
        "Actual end date\nتاريخ الانتهاء الفعلي"
    ],
    "eore_f20": [
        "Activity type",
        "Activity type\nنوع النشاط"
    ],
    "eore_f21": [
        "Awareness type for impacted communities",
        "Awareness type for impacted communities\nتوعية المجتمعات المتأثرة من مخاطر"
    ],
    "eore_f22": [
        "EORE type\nMRE type",
        "EORE type\nMRE type\nنوع التوعية بمخاطر الذخائر والمواد المتفجرة"
    ],
    "eore_f23": [
        "EORE Sub Type\nMRE Sub Type",
        "EORE Sub Type\nMRE Sub Type\nالنوع الثانوي للتوعية بمخاطر الذخائر والمواد المتفجرة"
    ],
    "eore_f24": [
        "Number of material distribution / Folders\nFolders",
        "Number of material distribution / Folders\nFolders\nفولدرات"
    ],
    "eore_f25": [
        "Number of material distribution / Bags\nBags",
        "Number of material distribution / Bags\nBags\nالحقائب"
    ],
    "eore_f26": [
        "Number of material distribution / Magazin\nMagazin\nMagazines",
        "Number of material distribution / Magazin\nMagazin\nMagazines\nمجلة\nمجلات"
    ],
    "eore_f27": [
        "Number of material distribution / Posters\nPosters",
        "Number of material distribution / Posters\nPosters\nبوسترات"
    ],
    "eore_f28": [
        "Number of material distribution / Football\nFootball",
        "Number of material distribution / Football\nFootball\nكرة القدم"
    ],
    "eore_f29": [
        "Number of material distribution / School Supplement\nSchool Supplement",
        "Number of material distribution / School Supplement\nSchool Supplement\nملحق المدرسة"
    ],
    "eore_f30": [
        "Number of material distribution / T-Shirts\nT-Shirts",
        "Number of material distribution / T-Shirts\nT-Shirts\nتيشرت"
    ],
    "eore_f31": [
        "Number of material distribution / Snake And Ladder Game\nSnake And Ladder Game",
        "Number of material distribution / Snake And Ladder Game\nSnake And Ladder Game\nلعبة حية ودرج"
    ],
    "eore_f32": [
        "Number of material distribution / Warning Signs(Flexes)\nWarning Signs(Flexes)",
        "Number of material distribution / Warning Signs(Flexes)\nWarning Signs(Flexes)\nلوحات ارشادية تحذيرية"
    ],
    "eore_f33": [
        "Number of material distribution / Booklets\nBooklets",
        "Number of material distribution / Booklets\nBooklets\nكتيبات"
    ],
    "eore_f34": [
        "Number of material distribution / Leaflet\nLeaflet\nLeaflets",
        "Number of material distribution / Leaflet\nLeaflet\nLeaflets\nمنشورات"
    ],
    "eore_f35": [
        "Number of material distribution / Others",
        "Number of material distribution / Others\nمواد اخرى"
    ],
    "eore_f36": [
        "Narrative of the project and Reasons for EORE activity\nNarrative",
        "Narrative of the project and Reasons for EORE activity\nNarrative\nتوضيح للمشروع واسباب نشاط التوعية ضد مخاطر الالغام"
    ],
    "eore_f37": [
        "Audience by Gender with Age Info / Children (5-12) Male\nChildren (5-12) Male",
        "Audience by Gender with Age Info / Children (5-12) Male\nChildren (5-12) Male\nأطفال (5-12) ذكر\nأطفال (12-5) ذكر"
    ],
    "eore_f38": [
        "Audience by Gender with Age Info / Children (5-12) Female\nChildren (5-12) Female",
        "Audience by Gender with Age Info / Children (5-12) Female\nChildren (5-12) Female\nأطفال (5-12) انثى\nأطفال (12-5) انثى"
    ],
    "eore_f39": [
        "Audience by Gender with Age Info / Youth (13-18) Male\nYouth (13-18) Male",
        "Audience by Gender with Age Info / Youth (13-18) Male\nYouth (13-18) Male\nشباب (13-18) ذكر\nشباب (18-13) ذكر"
    ],
    "eore_f40": [
        "Audience by Gender with Age Info / Youth (13-18) Female\nYouth (13-18) Female",
        "Audience by Gender with Age Info / Youth (13-18) Female\nYouth (13-18) Female\nشباب (13-18) انثى\nشباب (18-13) انثى"
    ],
    "eore_f41": [
        "Audience by Gender with Age Info / Adult (19+) Male\nAdult (19+) Male",
        "Audience by Gender with Age Info / Adult (19+) Male\nAdult (19+) Male\nبالغ (19+) ذكر"
    ],
    "eore_f42": [
        "Audience by Gender with Age Info / Adult (19+) Female\nAdult (19+) Female",
        "Audience by Gender with Age Info / Adult (19+) Female\nAdult (19+) Female\nبالغ (19+) انثى"
    ],
    "eore_f43": [
        "Audience type",
        "Audience type\nتصنيف المستفيدون\nتصنيف المستفيدين"
    ],
    "eore_f44": [
        "Comment\nComments",
        "Comment\nComments\nتعليقات\nملاحظات"
    ],
    "eore_f45": [
        "Org Internal Report ID",
        "Org Internal Report ID\nرقم هوية التقرير الخاص بالجهة المنفذة"
    ],
    "eore_f46": [
        "MAC Owner",
        "MAC Owner\nعائدية مركز شؤون الألغام"
    ],
    "eore_f47": [
        "Type of Remote Risk Education\nRemote Risk Education",
        "Type of Remote Risk Education\nRemote Risk Education\nنوع نشاط التوعية عن بعد"
    ],
    "eore_f52": [
        "Number of SMS",
        "Number of SMS\nعدد الرسائل النصية"
    ],
    "eore_f61": [
        "received_date\nReceived date",
        "received_date\nReceived date\nتاريخ الاستلام"
    ],
    "eore_f63": [
        "Received By",
        "Received By\nاستلم التقرير من قبل"
    ]
}


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for xmlid, (old, new) in HEADERS.items():
        field = env.ref("dma_field_reports." + xmlid, raise_if_not_found=False)
        if field and (field.headers or "") == old:
            field.headers = new
    seed_value_maps(env)
