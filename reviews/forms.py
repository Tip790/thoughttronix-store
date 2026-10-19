"""The review form — owns every rule on what a customer may post.

The comment is trimmed before its length is checked, so padding never
counts toward the 10–2,000 limits. ``max_length`` also puts ``maxlength``
on the textarea, so the browser stops typing at the limit.
"""

from django import forms

from .models import Review

COMMENT_MIN = 10
COMMENT_MAX = 2000


class ReviewForm(forms.ModelForm):
    rating = forms.TypedChoiceField(
        choices=[(n, f"{n} star{'s' if n > 1 else ''}") for n in range(1, 6)],
        coerce=int,
        widget=forms.RadioSelect,
        error_messages={
            "required": "Pick a rating from 1 to 5 stars.",
            "invalid_choice": "Pick a rating from 1 to 5 stars.",
        },
    )
    comment = forms.CharField(
        strip=True,
        min_length=COMMENT_MIN,
        max_length=COMMENT_MAX,
        widget=forms.Textarea(attrs={"rows": 4, "class": "textarea w-full"}),
        error_messages={
            "required": "Write a comment to go with your rating.",
            "min_length": (
                f"Your comment needs at least {COMMENT_MIN} characters "
                "(it has %(show_value)d)."
            ),
            "max_length": (
                f"Your comment can be at most {COMMENT_MAX:,} characters "
                "(it has %(show_value)d)."
            ),
        },
    )

    class Meta:
        model = Review
        fields = ["rating", "comment"]
