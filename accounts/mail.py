"""The default email backend: Django's console backend, made copy-pasteable.

Python's default email policy wraps lines at 78 characters, so a message
holding a long link goes out quoted-printable, with the link chopped into
``=``-terminated pieces. Real mail clients decode that invisibly, but in
the dev server's terminal the link can't be copied. Rendering with the
RFC 5322 line limit instead keeps every body line intact.
"""

import email.policy

from django.core.mail.backends import console

POLICY = email.policy.default.clone(max_line_length=998)


class ConsoleEmailBackend(console.EmailBackend):
    def write_message(self, message):
        msg = message.message(policy=POLICY)
        self.stream.write(f"{msg.as_bytes().decode()}\n")
        self.stream.write("-" * 79)
        self.stream.write("\n")
