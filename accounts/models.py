from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models, transaction

# US-only, like checkout. Shared by saved addresses and ``CheckoutForm``;
# ``accounts`` sits at the bottom of the dependency chain, so both live here.
US_STATES = [
    ("AL", "Alabama"),
    ("AK", "Alaska"),
    ("AZ", "Arizona"),
    ("AR", "Arkansas"),
    ("CA", "California"),
    ("CO", "Colorado"),
    ("CT", "Connecticut"),
    ("DE", "Delaware"),
    ("DC", "District of Columbia"),
    ("FL", "Florida"),
    ("GA", "Georgia"),
    ("HI", "Hawaii"),
    ("ID", "Idaho"),
    ("IL", "Illinois"),
    ("IN", "Indiana"),
    ("IA", "Iowa"),
    ("KS", "Kansas"),
    ("KY", "Kentucky"),
    ("LA", "Louisiana"),
    ("ME", "Maine"),
    ("MD", "Maryland"),
    ("MA", "Massachusetts"),
    ("MI", "Michigan"),
    ("MN", "Minnesota"),
    ("MS", "Mississippi"),
    ("MO", "Missouri"),
    ("MT", "Montana"),
    ("NE", "Nebraska"),
    ("NV", "Nevada"),
    ("NH", "New Hampshire"),
    ("NJ", "New Jersey"),
    ("NM", "New Mexico"),
    ("NY", "New York"),
    ("NC", "North Carolina"),
    ("ND", "North Dakota"),
    ("OH", "Ohio"),
    ("OK", "Oklahoma"),
    ("OR", "Oregon"),
    ("PA", "Pennsylvania"),
    ("RI", "Rhode Island"),
    ("SC", "South Carolina"),
    ("SD", "South Dakota"),
    ("TN", "Tennessee"),
    ("TX", "Texas"),
    ("UT", "Utah"),
    ("VT", "Vermont"),
    ("VA", "Virginia"),
    ("WA", "Washington"),
    ("WV", "West Virginia"),
    ("WI", "Wisconsin"),
    ("WY", "Wyoming"),
]

zip_validator = RegexValidator(
    r"^\d{5}(-\d{4})?$", "Enter a ZIP code like 79016 or 79016-1234."
)


class User(AbstractUser):
    """The store's user model.

    Roles use Django's own vocabulary and nothing else: customers are
    plain users, employees are ``is_staff``, the admin is ``is_superuser``.
    """

    # Nullable per the PRD: an absent job title is unknown, not empty.
    job_title = models.CharField(max_length=150, null=True, blank=True)  # noqa: DJ001


class AddressManager(models.Manager):
    def default_for(self, user, role):
        """The user's default address for ``role``, or ``None``."""
        return self.filter(user=user, **{Address.default_flag(role): True}).first()

    def save_from_checkout(self, user, data, *, role):
        """Save one checkout address section to the user's address book.

        ``data`` is a valid ``CheckoutForm``'s ``cleaned_data``; ``role``
        picks the section (``"shipping"`` or ``"billing"``). An address
        that exactly matches one the user already has is not saved twice.
        Either way, the address fills the user's default for ``role`` if
        that slot is empty — it never displaces an existing default.
        """
        values = {field: data[f"{role}_{field}"] for field in Address.FIELDS}
        address = self.filter(user=user, **values).first()
        if address is None:
            address = self.create(user=user, **values)
        address.fill_empty_defaults(role)
        return address


class Address(models.Model):
    """A saved address in a customer's address book.

    An address is just a place: shipping and billing are roles it plays
    on an order, so any address can fill either. Orders copy the fields
    at checkout — editing or deleting an address never touches an order.
    """

    ROLES = ("shipping", "billing")
    # The fields an order snapshots, named to match ``Order``'s
    # ``shipping_*`` / ``billing_*`` columns.
    FIELDS = ("name", "street", "line2", "city", "state", "zip")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="addresses",
    )
    label = models.CharField(
        "Label (optional)",
        max_length=50,
        blank=True,
        help_text="A nickname like “Home” or “Work”.",
    )
    name = models.CharField("Full name", max_length=100)
    street = models.CharField("Street address", max_length=200)
    line2 = models.CharField("Apt, suite, etc. (optional)", max_length=200, blank=True)
    city = models.CharField("City", max_length=100)
    state = models.CharField("State", max_length=2, choices=US_STATES)
    zip = models.CharField("ZIP code", max_length=10, validators=[zip_validator])
    is_default_shipping = models.BooleanField(default=False)
    is_default_billing = models.BooleanField(default=False)

    objects = AddressManager()

    class Meta:
        ordering = ["pk"]
        verbose_name_plural = "addresses"
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default_shipping=True),
                name="one_default_shipping_per_user",
            ),
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default_billing=True),
                name="one_default_billing_per_user",
            ),
        ]

    def __str__(self):
        return f"{self.label or self.name} — {self.one_line()}"

    def one_line(self):
        street = f"{self.street}, {self.line2}" if self.line2 else self.street
        return f"{street}, {self.city}, {self.state} {self.zip}"

    @staticmethod
    def default_flag(role):
        """The field name holding the default flag for ``role``."""
        if role not in Address.ROLES:
            raise ValueError(f"Unknown address role: {role!r}")
        return f"is_default_{role}"

    @transaction.atomic
    def make_default(self, role):
        """Make this the user's default for ``role``, clearing the old one."""
        flag = self.default_flag(role)
        Address.objects.filter(user=self.user, **{flag: True}).exclude(
            pk=self.pk
        ).update(**{flag: False})
        setattr(self, flag, True)
        self.save(update_fields=[flag])

    def fill_empty_defaults(self, *roles):
        """Become the default for each role that has no default yet."""
        for role in roles:
            if Address.objects.default_for(self.user, role) is None:
                self.make_default(role)

    def as_checkout_initial(self, role):
        """The address as ``CheckoutForm`` initial data for one section."""
        return {f"{role}_{field}": getattr(self, field) for field in self.FIELDS}
