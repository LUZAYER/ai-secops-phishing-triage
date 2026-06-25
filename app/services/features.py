from app.models.alert import EmailAlert

class FeatureExtractor:
    def extract(self, alert: EmailAlert) -> dict:
        return {
            "spf_fail":          alert.headers.spf.lower()  == "fail",
            "dkim_fail":         alert.headers.dkim.lower() == "fail",
            "dmarc_fail":        alert.headers.dmarc.lower()== "fail",
            "url_count":         len(alert.urls),
            "attachment_count":  len(alert.attachments),
            "contains_password": "password"  in alert.body_text.lower(),
            "contains_invoice":  "invoice"   in alert.body_text.lower(),
            "contains_urgent":   "urgent"    in alert.body_text.lower(),
            "contains_payment":  "payment"   in alert.body_text.lower(),
        }
