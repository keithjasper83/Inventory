# AI Agents Policy & Permissions

This system uses AI agents for assistance only. **AI agents are explicitly encouraged and permitted to suggest improvements** to code, architecture, documentation, and workflows for human review and decision.

## What AI Can Do

### Operational Tasks
- OCR labels and markings from images
- Identify resistor values from colour bands
- Suggest categories and fields for inventory items
- Detect duplicates (similar images/text)
- Scrape public datasheets and product literature when confidence is high (≥95%)
- Normalize spelling, units, and formatting
- Auto-apply high-confidence suggestions (≥95% confidence)

### Improvement Suggestions (EXPLICITLY ALLOWED)
**AI agents are encouraged to suggest:**
- Code improvements and refactoring opportunities
- Performance optimizations
- Security enhancements
- Architecture improvements
- Documentation enhancements
- Testing improvements
- Workflow optimizations
- Best practice implementations
- Bug fixes and corrections

**All suggestions must be:**
- Clearly marked as AI suggestions
- Presented for human review and approval
- Accompanied by rationale and expected benefits
- Reversible if accepted

## What AI Cannot Do
- Commit changes without human review and approval (except auto-approved high-confidence data)
- Override human decisions
- Delete inventory data without explicit approval
- Hide or silently modify fields
- Make breaking changes without documentation
- Remove existing functionality without justification

## Auditability and Transparency

All AI-generated and AI-scraped fields must be:
- Marked explicitly (`AI_GENERATED` or `AI_SCRAPED`)
- Logged with field-level before/after values
- Linked to evidence (PDF snapshot, datasheet, or source reference)
- Reversible by the user
- Tracked with confidence scores

## Confidence-Based Workflows

### High Confidence (≥95%)
- Auto-apply changes
- Mark as `AI_SCRAPED`
- Create audit log with evidence
- Notify user of changes

### Medium Confidence (80-95%)
- Create pending suggestion
- Mark as `AI_GENERATED` (pending)
- Require manual review
- Provide evidence and rationale

### Low Confidence (<80%)
- Create suggestion for review
- Mark as `AI_GENERATED` (needs_review)
- Flag for attention
- Provide multiple options if available

## Conflicts

If AI proposes a change that conflicts with an existing human-confirmed value:
- AI must provide a justification and evidence
- The change remains pending until explicitly approved by the user
- User can see both values and choose which to keep
- Audit trail maintains history of all changes

## Continuous Improvement

AI agents should:
- Learn from user feedback on suggestions
- Track acceptance/rejection rates
- Improve suggestion quality over time
- Report metrics on suggestion accuracy

## Philosophy

**AI exists to assist, not replace judgement.**

The system is designed with the principle that:
- AI excels at pattern recognition and data processing
- Humans excel at context, judgement, and decision-making
- The best results come from AI-human collaboration
- All AI actions should be transparent and reversible
