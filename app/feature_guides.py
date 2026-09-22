"""Reviewed live feature guides. No arbitrary selectors or record-write steps."""

import re
from .lead_guide_extensions import EXTRA_FEATURES

FEATURES = {
    "status": ("Lead status", [
        "The lead's Status section is open. These are the record's update controls, not the list's status filters.",
        "The available status choices are highlighted. Choose the stage that matches the customer. The options depend on your organisation and this lead's current state. Some choices require a reason, notes or a date.",
        "Review the required fields before using the save controls shown here. I have not selected an arbitrary status or saved this lead."], [
        "लीड का स्टेटस सेक्शन खुल गया है। यहाँ रिकॉर्ड का स्टेटस बदलते हैं। यह लिस्ट का स्टेटस फ़िल्टर नहीं है।",
        "उपलब्ध स्टेटस विकल्प यहाँ हैं। ग्राहक की स्थिति के हिसाब से सही विकल्प चुनते हैं। आपके संगठन और लीड की मौजूदा स्थिति के अनुसार विकल्प बदल सकते हैं। कुछ विकल्पों में कारण, नोट्स या तारीख जरूरी होते हैं।",
        "सेव करने से पहले जरूरी फ़ील्ड जाँचें। मैंने कोई मनमाना स्टेटस नहीं चुना है और लीड सेव नहीं की है।"]),
    "meeting": ("Schedule meeting", [
        "The lead's Status section is open. We will use its meeting scheduling option.",
        "Schedule Meeting is selected in the unsaved form. The appointment date and time field is highlighted. Choose the intended time and complete any required reason or notes. Nothing is scheduled until saved.",
        "Review the meeting details and the required fields before saving. This demo has left an unsaved selection; no meeting was created. Close the form without saving to discard it."], [
        "लीड का स्टेटस सेक्शन खुल गया है। अब मीटिंग शेड्यूल करने वाला विकल्प दिखाऊँगा।",
        "फ़ॉर्म में शेड्यूल मीटिंग चुना गया है। तारीख और समय वाला फ़ील्ड हाइलाइट है। सही समय चुनें और जरूरी कारण या नोट्स भरें। अभी कुछ सेव नहीं हुआ है।",
        "मीटिंग की जानकारी जाँचने के बाद ही सेव करें। डेमो ने मीटिंग नहीं बनाई है। नमूना चयन हटाने के लिए फ़ॉर्म बिना सेव किए बंद कर दें।"]),
    "site_visit": ("Schedule site visit", [
        "The lead's Status section is open. We will use its site visit scheduling option.",
        "Schedule Site Visit is selected in the unsaved form. Set the intended date and time here. Complete the project, property, reason or notes fields that your organisation requires.",
        "Review the visit details before saving. This demo did not create a site visit. The form contains an unsaved selection; close it without saving to discard it."], [
        "लीड का स्टेटस सेक्शन खुल गया है। अब साइट विज़िट शेड्यूल करने वाला विकल्प दिखाऊँगा।",
        "फ़ॉर्म में शेड्यूल साइट विज़िट चुना गया है। यहाँ तारीख और समय भरते हैं। आपके संगठन के अनुसार जरूरी प्रोजेक्ट, प्रॉपर्टी, कारण या नोट्स भी भरें।",
        "विज़िट की जानकारी जाँचकर ही सेव करें। डेमो ने साइट विज़िट नहीं बनाई है। नमूना चयन हटाने के लिए फ़ॉर्म बिना सेव किए बंद कर दें।"]),
    "notes": ("Lead notes", [
        "The lead's Notes section is open. It keeps conversation details and observations with this record.",
        "Write a nonblank note in the highlighted text area. The tick control posts it. We are identifying the input without entering or posting customer information.",
        "Note history shows existing entries with author and time. Posting needs Update Notes permission, and an unclaimed pool lead can hide the input. No note was posted."], [
        "लीड का नोट्स सेक्शन खुल गया है। ग्राहक से हुई बातचीत और जरूरी बातें यहाँ लिखते हैं।",
        "हाइलाइट किए गए बॉक्स में नोट लिखते हैं। खाली नोट मान्य नहीं है। टिक बटन से नोट पोस्ट होता है। अभी कोई जानकारी नहीं भरी या पोस्ट की गई है।",
        "पुराने नोट्स में लिखने वाले का नाम और समय देखें। नोट जोड़ने की अनुमति जरूरी है। अनक्लेम्ड पूल लीड में बॉक्स छिपा हो सकता है। कोई नोट पोस्ट नहीं हुआ है।"]),
    "history": ("Lead history", [
        "The lead's History section is open.", "Review the visible history entries to understand changes to this record. The entries and details available depend on your permissions.", "This is a read-only walkthrough. No history entry or customer record was changed."], [
        "लीड का हिस्ट्री सेक्शन खुल गया है।", "यहाँ उपलब्ध एंट्री देखकर रिकॉर्ड में हुए बदलाव समझें। दिखाई देने वाली जानकारी आपकी अनुमति पर निर्भर है।", "यह सिर्फ जानकारी देखने का डेमो है। कोई रिकॉर्ड नहीं बदला गया है।"]),
    "documents": ("Lead documents", [
        "The lead's Documents section is open.", "Review the document area and available upload controls. Document visibility and editing depend on your permissions and the lead's state.", "I have not uploaded, downloaded or deleted any document. Use only the controls available for your account."], [
        "लीड का डॉक्यूमेंट सेक्शन खुल गया है।", "यहाँ डॉक्यूमेंट और उपलब्ध अपलोड कंट्रोल देखें। देखने और बदलने की सुविधा अनुमति और लीड की स्थिति पर निर्भर है।", "मैंने कोई डॉक्यूमेंट अपलोड, डाउनलोड या डिलीट नहीं किया है।"]),
    "reassign": ("Lead assignment", [
        "The lead's ownership area is open in Overview.", "The assignment form is expanded. Select an eligible primary owner here. A secondary owner may be available when dual ownership is enabled.", "Review ownership before saving. Pool claim, dropping to pool and assigning are different actions. None of them was performed by this demo."], [
        "लीड के ओवरव्यू में जिम्मेदार व्यक्ति वाला हिस्सा खुल गया है।", "असाइनमेंट फ़ॉर्म खुल गया है। यहाँ उपलब्ध जिम्मेदार व्यक्ति चुनते हैं। ड्यूल ओनरशिप चालू हो तो दूसरा व्यक्ति भी चुन सकते हैं।", "सेव करने से पहले जिम्मेदारी जाँचें। पूल से क्लेम करना, पूल में भेजना और असाइन करना अलग काम हैं। डेमो ने इनमें से कोई बदलाव सेव नहीं किया है।"]),
}

FEATURES.update(EXTRA_FEATURES)

FEATURE_NARRATIONS = {language: {f"feature.{key}.{stage}": values[index + 1][stage_index]
    for key, values in FEATURES.items() for stage_index, stage in enumerate(("open", "details", "finish"))}
    for index, language in enumerate(("en", "hi"))}


def allows_feature_demo(query: str) -> bool:
    return not re.search(r"\b(?:don't|do not|only text|text only|no demo|just explain|sirf text|nahi|mat)\b", query.casefold())


def feature_for_query(query: str, previous: str | None = None) -> str | None:
    text = query.casefold()
    if not allows_feature_demo(query):
        return None
    if re.search(r'\b(?:delete|deletion|remove)\b', text):
        return None
    if re.search(r'\b(?:bulk|broadcast)\b', text) and not re.search(r'upload|import', text):
        return None
    if re.fullmatch(r'\s*(?:(?:yes|haan|ok|using|with|kaise)\s+)*(?:templates?|message|send it|show me|demo)\s*[?.!]*', text):
        return 'whatsapp' if previous == 'communications' else previous if previous in ('whatsapp', 'email') else None
    # Communication must be recognised before the generic model can ask circular questions.
    if re.search(r'whats?\s*a?pp|whtsp\w*|watsapp|व्हाट्स', text):
        if re.search(r'\be-?mail\b|ईमेल', text):
            return 'communications'
        return 'whatsapp'
    if re.search(r'\be-?mail\b|ईमेल', text) and not re.search(r'\b(?:address|change|edit|delete)\b', text):
        return 'email'
    for feature, pattern in (
        ('bulk_upload', r'bulk\s*(?:upload|import)|spreadsheet|excel.*(?:upload|import)|import.*leads?'),
        ('integrations', r'facebook|magicbricks|housing|99acres|bayut|dubizzle|webhook|integration|google.*(?:ads|campaign)'),
        ('sources', r'lead.*(?:source|come from|kaha|kahan)|(?:source|origin).*lead|sub.?source'),
        ('saved_filters', r'saved?\s*filters?'), ('date_filter', r'date.*filter|filter.*date'),
        ('filters', r'advanced?.*filter|filter.*leads?|leads?.*filter'),
        ('columns', r'columns?'), ('export', r'export'), ('search', r'(?:search|find|dhund).*leads?|leads?.*search'),
    ):
        if re.search(pattern, text):
            return feature
    if re.search(r"\b(?:bulk|delete|deletion|remove|export)\b", text):
        return None
    if not allows_feature_demo(query):
        return None
    if re.search(r"\b(?:task|project|property|invoice|user)\s+status\b", text):
        return None
    if re.search(r"site\s*visit|sitevis[ti]e?", text) and re.search(r"schedul|plan|book|set|kaise", text):
        return "site_visit"
    if "meeting" in text and re.search(r"schedul|plan|book|set|kaise", text):
        return "meeting"
    if re.search(r"\bstatus\b", text) and re.search(r"chang|updat|badal|kaise", text):
        return "status"
    if re.search(r"\blead\b", text):
        for feature, pattern in (("reassign", r"reassign|assignment|ownership"), ("notes", r"\bnotes?\b"),
                                 ("history", r"history"), ("documents", r"documents?")):
            if re.search(pattern, text):
                return feature
    return None
