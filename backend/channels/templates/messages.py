"""Message templates for omnichannel notifications."""

from backend.channels.base.types import NotificationEvent

TEMPLATES: dict[NotificationEvent, dict[str, str]] = {
    NotificationEvent.OCR_COMPLETED: {
        "title": "OCR Completed",
        "body": "Document '{document_name}' has been processed. {field_count} fields extracted with {confidence}% confidence.",
        "email_subject": "Mahakosh: OCR Processing Complete — {document_name}",
    },
    NotificationEvent.APPROVAL_REQUIRED: {
        "title": "Approval Required",
        "body": "Action needed: {title}. Please approve, reject, or request review.",
        "email_subject": "Mahakosh: Approval Required — {title}",
    },
    NotificationEvent.WORKFLOW_FAILED: {
        "title": "Workflow Failed",
        "body": "Workflow '{workflow_name}' failed at step '{failed_step}'. Error: {error}",
        "email_subject": "Mahakosh: Workflow Failed — {workflow_name}",
    },
    NotificationEvent.REPORT_READY: {
        "title": "Report Ready",
        "body": "Your report '{report_name}' is ready for review.",
        "email_subject": "Mahakosh: Report Ready — {report_name}",
    },
    NotificationEvent.SYNC_COMPLETE: {
        "title": "Sync Complete",
        "body": "Accounting sync completed for {company_name}. {records_synced} records updated.",
        "email_subject": "Mahakosh: Sync Complete — {company_name}",
    },
    NotificationEvent.WORKFLOW_COMPLETED: {
        "title": "Workflow Completed",
        "body": "Workflow '{workflow_name}' completed successfully in {duration}.",
        "email_subject": "Mahakosh: Workflow Complete — {workflow_name}",
    },
}


def render_notification(event: NotificationEvent, channel: str, **kwargs: str) -> dict[str, str]:
    template = TEMPLATES.get(event, {"title": "Mahakosh", "body": "{message}"})
    result = {}
    for key, value in template.items():
        try:
            result[key] = value.format(**kwargs)
        except KeyError:
            result[key] = value
    if channel == "telegram" or channel == "whatsapp":
        result["text"] = f"*{result.get('title', 'Mahakosh')}*\n{result.get('body', '')}"
    return result
