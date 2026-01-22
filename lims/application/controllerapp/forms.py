from security.forms import JobTypeChangeForm


class AdminJobTypeChangeForm(JobTypeChangeForm):
    required_css_class = "required"