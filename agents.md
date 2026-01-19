# Agents Policy

This system uses AI agents for assistance only.

## What AI Can Do
- OCR labels and markings
- Identify resistor values from colour bands
- Suggest categories and fields
- Detect duplicates (similar images/text)
- Scrape public datasheets and product literature when confidence is high
- Normalise spelling, units, and formatting

## What AI Cannot Do
- Commit changes without human review and approval
- Override human decisions
- Delete inventory data
- Hide or silently modify fields

## Auditability and Transparency
All AI-generated and AI-scraped fields must be:
- Marked explicitly (`AI_GENERATED` or `AI_SCRAPED`)
- Logged with field-level before/after values
- Linked to evidence (PDF snapshot, datasheet, or source reference)
- Reversible by the user

## Conflicts
If AI proposes a change that conflicts with an existing human-confirmed value:
- AI must provide a justification and evidence
- The change remains pending until explicitly approved by the user

AI exists to assist, not replace judgement.
