import os
from jinja2 import Environment, FileSystemLoader

class ReportGenerator:
    def __init__(self, template_dir: str = "app/templates", output_dir: str = "reports"):
        self.env = Environment(loader=FileSystemLoader(template_dir))
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate(self, alert_data: dict, analysis: dict) -> str:
        template = self.env.get_template("report.md.j2")
        context = {
            "alert_id":           alert_data.get("alert_id"),
            "reported_by":        alert_data.get("reported_by"),
            "sender_email":       alert_data.get("sender_email"),
            "subject":            alert_data.get("subject"),
            "classification":     analysis.get("classification"),
            "severity":           analysis.get("severity"),
            "confidence":         analysis.get("confidence"),
            "tactics":            analysis.get("social_engineering_tactics", []),
            "rationale":          analysis.get("rationale"),
            "recommended_action": analysis.get("recommended_action"),
        }
        content  = template.render(context)
        filepath = os.path.join(self.output_dir, f"{alert_data['alert_id']}.md")
        with open(filepath, "w") as f:
            f.write(content)
        return filepath
