import io
import logging
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model
from .models import DocumentRecord

User = get_user_model()
logger = logging.getLogger(__name__)


def render_to_pdf(template_name, context):
    """
    Renders an HTML template to PDF bytes.
    Attempts WeasyPrint first, then falls back to xhtml2pdf if there are
    import or library dependency issues.
    """
    html_string = render_to_string(template_name, context)
    
    # Try WeasyPrint first
    try:
        from weasyprint import HTML
        logger.info("Attempting PDF generation using WeasyPrint")
        pdf_bytes = HTML(string=html_string).write_pdf()
        return pdf_bytes
    except Exception as weasy_err:
        logger.warning(f"WeasyPrint failed or not configured correctly ({str(weasy_err)}). Falling back to xhtml2pdf.")
        
    # Fallback to xhtml2pdf
    try:
        from xhtml2pdf import pisa
        result = io.BytesIO()
        # Encode HTML to bytes to prevent encoding issues in xhtml2pdf
        html_bytes = html_string.encode("utf-8")
        pdf = pisa.pisaDocument(io.BytesIO(html_bytes), result)
        if not pdf.err:
            return result.getvalue()
        else:
            raise Exception(f"xhtml2pdf rendering error code: {pdf.err}")
    except Exception as pisa_err:
        logger.error(f"xhtml2pdf rendering failed: {str(pisa_err)}")
        raise pisa_err


def generate_invoice_pdf(invoice, generated_by=None):
    """
    Generates PDF for an invoice, saves to DocumentRecord, and returns the record.
    """
    # Check if a document record already exists for this invoice
    record = DocumentRecord.objects.filter(invoice=invoice, document_type='invoice_pdf').first()
    if record:
        return record

    context = {
        'invoice': invoice,
        'student': invoice.user,
        'title': f"INVOICE: {invoice.invoice_number}"
    }

    pdf_bytes = render_to_pdf('documents/invoice_pdf.html', context)
    filename = f"invoice_{invoice.invoice_number}.pdf"

    record = DocumentRecord.objects.create(
        user=invoice.user,
        document_type='invoice_pdf',
        invoice=invoice,
        generated_by=generated_by
    )
    record.file.save(filename, ContentFile(pdf_bytes))
    return record


def generate_receipt_pdf(payment, generated_by=None):
    """
    Generates PDF for a payment transaction, saves to DocumentRecord, and returns the record.
    """
    record = DocumentRecord.objects.filter(payment=payment, document_type='receipt_pdf').first()
    if record:
        return record

    invoice = payment.invoice
    context = {
        'payment': payment,
        'invoice': invoice,
        'student': payment.user,
        'title': f"RECEIPT: {payment.reference}"
    }

    pdf_bytes = render_to_pdf('documents/receipt_pdf.html', context)
    filename = f"receipt_{payment.reference}.pdf"

    record = DocumentRecord.objects.create(
        user=payment.user,
        document_type='receipt_pdf',
        payment=payment,
        invoice=invoice,
        generated_by=generated_by
    )
    record.file.save(filename, ContentFile(pdf_bytes))
    return record


def generate_progress_report_pdf(report, generated_by=None):
    """
    Generates PDF for a progress report, saves to DocumentRecord, and returns the record.
    """
    record = DocumentRecord.objects.filter(report=report, document_type='progress_report_pdf').first()
    if record:
        return record

    context = {
        'report': report,
        'student': report.student,
        'course': report.course,
        'title': f"PROGRESS REPORT: {report.student.username} - {report.course.title}"
    }

    pdf_bytes = render_to_pdf('documents/progress_report_pdf.html', context)
    filename = f"progress_report_{report.id}.pdf"

    record = DocumentRecord.objects.create(
        user=report.student,
        document_type='progress_report_pdf',
        report=report,
        generated_by=generated_by
    )
    record.file.save(filename, ContentFile(pdf_bytes))
    return record
