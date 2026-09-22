"""Reviewed product explanations for workflows where exact wording matters."""

from .crm_knowledge import tokens

ANSWERS = {
    "notes": {
        "en": "Lead notes record conversation details, observations and follow-up information against a lead.\n\n1. Open the lead preview and its Notes area.\n2. Enter your note in the text area with the ‘Type here....’ placeholder. Blank or whitespace-only notes are invalid.\n3. Click the tick button to post the note.\n4. Check the note history, which groups entries by date and shows the author and time.\n\nAdding notes requires the Update Notes permission. The text area is hidden for an unclaimed lead-pool record. Confidential notes require their own viewing permission. The View Lead Source permission controls source-related entries; it does not hide all ordinary notes.\n\nThese are usage instructions; this answer has not posted a note.",
        "hi": "Lead Notes mein customer se hui baat, observations aur follow-up ki details lead ke saath likh sakte hain.\n\n1. Lead ka preview kholkar Notes area par jaayein.\n2. ‘Type here....’ wale text box mein note likhein. Khaali note ya sirf spaces valid nahi hain.\n3. Tick button dabakar note post karein.\n4. History mein note check karein. Entries date ke hisaab se grouped hoti hain aur saath mein likhne wale ka naam aur time dikhta hai.\n\nNote add karne ke liye Update Notes permission chahiye. Unclaimed lead-pool record mein text box hidden rehta hai. Confidential notes dekhne ki permission alag hai. View Lead Source permission sirf source wali entries ko control karti hai, saare normal notes ko nahi.\n\nYeh use karne ke steps hain; is answer ne koi note post nahi kiya hai."
    },
    "bulk": {
        "en": "Bulk upload imports multiple lead rows through a file instead of entering each lead separately. The import screen has Upload file, Map the fields, and Review & Import stages.\n\n1. Download the template from the upload screen.\n2. Replace its dummy data with your lead details. The screen says files above 100,000 rows are unsupported; split larger files.\n3. Select the prepared file and choose Proceed.\n4. Select the sheet, then map its columns to CRM fields. Name and Primary Number are marked required in lead mapping.\n5. Review the mapping and import details before submitting.\n\n‘Push to lead pool’ appears only when importing leads, lead pool is enabled and the user can view the pool. This explanation does not confirm duplicate-handling options or a file-size limit in MB. It has not uploaded or imported any records.",
        "hi": "Bulk upload se ek-ek lead bharne ke bajay file ki multiple rows import kar sakte hain. Screen ke teen stages hain: Upload file, Map the fields aur Review & Import.\n\n1. Upload screen se template download karein.\n2. Sample data ko apni lead details se replace karein. Screen ke mutabik 1,00,000 se zyada rows supported nahi hain; badi file ko split karein.\n3. Taiyar file select karke Proceed karein.\n4. Sheet select karein aur file ke columns ko CRM fields se map karein. Lead mapping mein Name aur Primary Number required dikhte hain.\n5. Submit karne se pehle mapping aur import details review karein.\n\nPush to lead pool tab dikhta hai jab lead import ho raha ho, pool enabled ho aur pool dekhne ki permission ho. Duplicate handling ke options ya MB mein file limit yahan verify nahi hui hai. Is answer ne koi record import nahi kiya hai."
    },
    "priority": {
        "en": "Task priority indicates how urgent a task is.\n\n1. In the Add Task form, find the required Priority field.\n2. Choose a radio option: Low, Medium, High or Critical.\n3. Complete the other task details, including title, assignees and scheduled date/time, then use the form’s save action when ready.\n\nThe task grid displays Low in green, Medium in yellow, High in light orange and Critical in red.\n\nThe reviewed code does not establish that changing priority automatically reassigns tasks or creates reminders. This answer explains the field and has not changed a task.",
        "hi": "Task Priority batati hai ki kaam kitna urgent hai.\n\n1. Add Task form mein required Priority field dekhein.\n2. Radio options mein Low, Medium, High ya Critical chunein.\n3. Title, assignees aur scheduled date/time jaise baaki details complete karein, phir ready hone par form se save karein.\n\nTask grid mein Low green, Medium yellow, High light orange aur Critical red dikhta hai.\n\nReviewed code se yeh confirm nahi hota ki priority badalne par task apne-aap reassign hota hai ya reminder banta hai. Yeh field ka explanation hai; koi task change nahi hua hai."
    },
}


def reviewed_answer(question: str, language: str) -> str | None:
    words = set(tokens(question))
    if words & {"why", "error", "fail", "failed", "permission", "limit", "delete", "deletion", "remove", "edit", "editing", "cannot", "unable", "not"}:
        return None
    # Only these established workflows use a fixed guide. Other questions retain retrieval.
    if {"lead", "note"} <= words and not words & {"delete", "remove", "edit", "bulk", "export"}:
        return ANSWERS["notes"][language]
    if {"bulk", "lead"} <= words and words & {"upload", "import"} and not words & {"error", "fail", "failed", "duplicate", "migration", "export"}:
        return ANSWERS["bulk"][language]
    if {"task", "priority"} <= words and not words & {"filter", "delete", "edit", "update"}:
        return ANSWERS["priority"][language]
    return None
