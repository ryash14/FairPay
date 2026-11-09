"""Fill a message template from config whatever placeholder style it uses.

The templates live in config/config.py, which this project does not own. A
template may use positional ``{}`` / ``{0}`` placeholders or named ones; this
helper fills either, so the code never depends on how a message was written.
"""
import string


def fill_template(template, *values, **named):
    fields = [field for _, field, _, _ in string.Formatter().parse(template) if field is not None]
    if not fields:
        return template
    positional = list(values)
    keyword = dict(named)
    next_value = iter(values)
    for field in fields:
        name = field.split(".")[0].split("[")[0]
        if name == "" or name.isdigit() or name in keyword:
            continue
        try:
            keyword[name] = next(next_value)
        except StopIteration:
            keyword[name] = ""
    return template.format(*positional, **keyword)
