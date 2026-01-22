from django import forms
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django_summernote.widgets import SummernoteWidget


class LookupWidget(forms.TextInput):
    def render(self, name, value, attrs=None, renderer=None):
        attrs = attrs or {}
        attrs.update({
            'readonly': 'readonly',
            'size': '20',
            'style': 'width: 200px;',
            'onmouseover': 'showMagnifier(this);',
            'onmouseout': 'hideMagnifier();'
        })
        html = super().render(name, value, attrs, renderer)

        lookup_icon = '''
        <a href="#" onclick="associateTest()" style="margin-left:5px;">
            <i class="fas fa-search" style="cursor:pointer;"></i>
        </a>
        '''

        # magnifier CSS and JS
        magnifier_js_css = '''
        <style>
            .magnifier {
                position: absolute;
                background: #fff;
                border: 2px solid #333;
                padding: 10px;
                font-size: 20px; 
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
                display: none;
                z-index: 1000;
                pointer-events: none; 
                border-radius: 8px;
                max-height: 300px; 
                max-width: 400px; 
                overflow-y: auto;
                white-space: pre-wrap; 
            }
        </style>
        <script>
            (function() {
                if (!window.magnifier) {
                    window.magnifier = document.createElement('div');
                    window.magnifier.className = 'magnifier';
                    document.body.appendChild(window.magnifier);
                }
            })();

            // Show magnifier with scroll for large content
            function showMagnifier(input) {
                window.magnifier.innerText = input.value || 'No content';
                window.magnifier.style.display = 'block';

                document.addEventListener('mousemove', moveMagnifier);
            }

            // Move magnifier with cursor
            function moveMagnifier(e) {
                window.magnifier.style.left = e.pageX + 20 + 'px';
                window.magnifier.style.top = e.pageY + 20 + 'px';
            }

            // Hide magnifier
            function hideMagnifier() {
                window.magnifier.style.display = 'none';
                document.removeEventListener('mousemove', moveMagnifier);
            }
        </script>
        '''
        reset_icon = '''
                <a href="#" onclick="resetAssociateTest()" style="margin-left:5px;" title="Reset">
                    <i class="fas fa-times" style="cursor:pointer; color:red;"></i>
                </a>
                '''

        return mark_safe(f'''
            {magnifier_js_css}
            <span style="display: inline-flex; align-items: center;">
                {html} {lookup_icon} {reset_icon}
            </span>
        ''')


class NextLinkWidget(forms.Widget):
    def __init__(self, next_tab=None, *args, **kwargs):
        self.next_tab = next_tab
        super().__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, renderer=None):
        next_tab = self.next_tab if self.next_tab else ''
        return format_html(
            '<div class="object-tools">'
            '<a id="next-sample-btn" class="btn btn-block btn-secondary btn-sm" '
            'style="padding: 6px 12px; font-size: 14px; width: 120px; height: 32px; display: inline-block; text-align: center;" '
            'href="#" onclick="moveToNextTab(\'{}\')">Next</a>'
            '</div>',
            next_tab
        )


class PrevLinkNextLinkWidget(forms.Widget):
    def __init__(self, prev_tab=None, next_tab=None, *args, **kwargs):
        self.prev_tab = prev_tab
        self.next_tab = next_tab
        super().__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, renderer=None):
        prev_tab = self.prev_tab if self.prev_tab else ''
        next_tab = self.next_tab if self.next_tab else ''
        return format_html(
            '<div class="object-tools" style="display: flex; gap: 10px; align-items: center;">'
            '<a id="prev-sample-btn" class="btn btn-secondary btn-sm" '
            'style="padding: 6px 12px; font-size: 14px; width: 120px; height: 32px; display: inline-block; text-align: center;" '
            'href="#" onclick="moveToPrevTab(\'{}\')">Prev</a>'
            '<a id="next-sample-btn" class="btn btn-secondary btn-sm" '
            'style="padding: 6px 12px; font-size: 14px; width: 120px; height: 32px; display: inline-block; text-align: center;" '
            'href="#" onclick="moveToNextTab(\'{}\')">Next</a>'
            '</div>',
            prev_tab,
            next_tab
        )


class FinishLinkWidget(forms.Widget):
    def __init__(self, prev_tab=None, next_tab=None, *args, **kwargs):
        self.prev_tab = prev_tab
        self.next_tab = next_tab
        super().__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, renderer=None):
        prev_tab = self.prev_tab if self.prev_tab else ''
        next_tab = self.next_tab if self.next_tab else ''
        return format_html(
            '<div class="object-tools" style="display: flex; gap: 10px; align-items: center;">'
            '<a id="prev-sample-btn" class="btn btn-secondary btn-sm" '
            'style="padding: 6px 12px; font-size: 14px; height: 32px; display: inline-block; text-align: center;" '
            'href="#" onclick="moveToPrevTab(\'{}\')">Prev</a>'
            '<a id="next-sample-btn" class="btn btn-secondary btn-sm" '
            'style="padding: 6px 12px; font-size: 14px; height: 32px; display: inline-block; text-align: center;" '
            'href="#" onclick="createSample()">Create Sample</a>'
            '</div>',
            prev_tab,
            next_tab
        )


# for magnifying effect on mouse hover

class MagnifyingTextInput(forms.TextInput):
    def render(self, name, value, attrs=None, renderer=None):
        attrs = attrs or {}
        attrs.update({
            'readonly': 'readonly',
            'onmouseover': 'showMagnifier(this);',
            'onmouseout': 'hideMagnifier();'
        })

        input_html = super().render(name, value, attrs, renderer)

        magnifier_js_css = '''
        <style>
            /* Magnifier Box Styling */
            .magnifier {
                position: absolute;
                background: #fff;
                border: 2px solid #333;
                padding: 10px;
                font-size: 20px; 
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
                display: none;
                z-index: 1000;
                pointer-events: none; 
                border-radius: 8px; 
                max-height: 300px; 
                max-width: 400px; 
                overflow-y: auto; 
                white-space: pre-wrap;
            }
        </style>

        <script>
            // Create magnifier only once
            (function() {
                if (!window.magnifier) {
                    window.magnifier = document.createElement('div');
                    window.magnifier.className = 'magnifier';
                    document.body.appendChild(window.magnifier);
                }
            })();

            // Show magnifier box on hover
            function showMagnifier(input) {
                window.magnifier.innerText = input.value || 'No content';
                window.magnifier.style.display = 'block';
                document.addEventListener('mousemove', moveMagnifier);
            }

            // Move magnifier with mouse
            function moveMagnifier(event) {
                window.magnifier.style.left = event.pageX + 20 + 'px';
                window.magnifier.style.top = event.pageY + 20 + 'px';
            }

            // Hide magnifier box on mouse out
            function hideMagnifier() {
                window.magnifier.style.display = 'none';
                document.removeEventListener('mousemove', moveMagnifier);
            }
        </script>
        '''

        return mark_safe(magnifier_js_css + input_html)


class PartNoInputWidget(forms.TextInput):
    def __init__(self, attrs=None):
        default_attrs = {
            'onkeypress': 'return validatePartNoInput(event)',
            'onchange': 'onchangePartNo()',
            'id': 'id_part_no',
            'maxlength': '10',
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)


class CustomSummernoteWidget(SummernoteWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, renderer=None):
        final_attrs = self.build_attrs(self.attrs, attrs or {})

        # Extract the attributes you want to preserve
        ta_id = final_attrs.pop("data-ta-id", "")
        dropdown_lookups = final_attrs.pop("data-dropdown-lookups", "")
        css_class = final_attrs.get("class", "")

        render_args = inspect.signature(super().render).parameters
        if 'renderer' in render_args:
            summernote_html = super().render(name, value, final_attrs, renderer)
        else:
            summernote_html = super().render(name, value, final_attrs)

        # Wrap with span for reliable access to data attributes
        wrapped = f'''
            <span class="analyte-value-wrapper" 
                  data-ta-id="{ta_id}" 
                  data-dropdown-lookups="{dropdown_lookups}">
                {summernote_html}
            </span>
        '''
        return mark_safe(wrapped)
