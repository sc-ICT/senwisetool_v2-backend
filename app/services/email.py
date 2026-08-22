"""
Service d'envoi d'emails.

Pour changer de fournisseur, modifie uniquement les variables dans .env :
  MAIL_SERVER, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD, MAIL_STARTTLS, MAIL_SSL_TLS

Fournisseurs courants :
  Gmail      : smtp.gmail.com:587, STARTTLS=true
  Outlook    : smtp.office365.com:587, STARTTLS=true
  Brevo      : smtp-relay.brevo.com:587, STARTTLS=true
  Mailgun    : smtp.mailgun.org:587, STARTTLS=true
  Amazon SES : email-smtp.<region>.amazonaws.com:587, STARTTLS=true
"""

from fastapi_mail import (
    ConnectionConfig,
    FastMail,
    MessageSchema,
    MessageType,
    NameEmail,
)
from pydantic import SecretStr

from app.config import settings


def _get_connection_config() -> ConnectionConfig:
    """
    Construit la configuration SMTP depuis les settings.
    Appelé à chaque envoi pour refléter les changements de .env sans redémarrage.
    """
    return ConnectionConfig(
        MAIL_USERNAME=settings.MAIL_USERNAME,
        MAIL_PASSWORD=SecretStr(settings.MAIL_PASSWORD),  # ← enveloppe en SecretStr
        MAIL_FROM=settings.MAIL_FROM,
        MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
        MAIL_PORT=settings.MAIL_PORT,
        MAIL_SERVER=settings.MAIL_SERVER,
        MAIL_STARTTLS=settings.MAIL_STARTTLS,
        MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True,
    )


class EmailService:
    """
    Service d'envoi d'emails.

    En développement (mail_enabled = False) :
    - les emails ne sont pas envoyés
    - le contenu est affiché dans le terminal

    En production :
    - les emails sont envoyés via le serveur SMTP configuré dans .env
    """

    @staticmethod
    async def _send(subject: str, recipients: list[str], body: str) -> None:
        """
        Méthode interne — envoie un email HTML.
        En dev sans config email → affiche dans le terminal.
        """
        if not settings.mail_enabled:
            print("\n" + "─" * 60)
            print(f"📧 EMAIL (non envoyé — configurer MAIL_* dans .env)")
            print(f"   À      : {', '.join(recipients)}")
            print(f"   Objet  : {subject}")
            print(f"   Corps  : {body[:200]}...")
            print("─" * 60 + "\n")
            return

        message = MessageSchema(
            subject=subject,
            recipients=[NameEmail(name=r, email=r) for r in recipients],
            body=body,
            subtype=MessageType.html,
        )
        mail = FastMail(_get_connection_config())
        await mail.send_message(message)

    # ─── Emails métier ────────────────────────────────────────────────────────

    @staticmethod
    async def send_verification(email: str, name: str, token: str) -> None:
        """Email de vérification de compte."""
        verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"

        subject = f"Vérifiez votre adresse e-mail — {settings.APP_NAME}"
        body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #0B0F1E;">Bonjour {name},</h2>

            <p>Merci de vous être inscrit sur <strong>{settings.APP_NAME}</strong>.</p>

            <p>Cliquez sur le bouton ci-dessous pour vérifier votre adresse e-mail
            et activer votre compte :</p>

            <div style="text-align: center; margin: 32px 0;">
                <a href="{verify_url}"
                   style="background-color: #F2A93B; color: #0B0F1E; padding: 14px 28px;
                          text-decoration: none; border-radius: 8px; font-weight: bold;">
                    Vérifier mon adresse e-mail
                </a>
            </div>

            <p style="color: #6B7280; font-size: 14px;">
                Ce lien est valable <strong>24 heures</strong>.<br>
                Si vous n'avez pas créé de compte, ignorez cet e-mail.
            </p>

            <hr style="border: none; border-top: 1px solid #E5E7EE; margin: 24px 0;">

            <p style="color: #6B7280; font-size: 12px;">
                Ou copiez ce lien dans votre navigateur :<br>
                <a href="{verify_url}" style="color: #6366F1;">{verify_url}</a>
            </p>
        </div>
        """

        await EmailService._send(subject, [email], body)

    @staticmethod
    async def send_reset_password(email: str, name: str, token: str) -> None:
        """Email de réinitialisation de mot de passe."""
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"

        subject = f"Réinitialisation de votre mot de passe — {settings.APP_NAME}"
        body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #0B0F1E;">Bonjour {name},</h2>

            <p>Vous avez demandé la réinitialisation de votre mot de passe
            sur <strong>{settings.APP_NAME}</strong>.</p>

            <div style="text-align: center; margin: 32px 0;">
                <a href="{reset_url}"
                   style="background-color: #F2A93B; color: #0B0F1E; padding: 14px 28px;
                          text-decoration: none; border-radius: 8px; font-weight: bold;">
                    Réinitialiser mon mot de passe
                </a>
            </div>

            <p style="color: #6B7280; font-size: 14px;">
                Ce lien est valable <strong>1 heure</strong>.<br>
                Si vous n'avez pas fait cette demande, ignorez cet e-mail —
                votre mot de passe n'a pas été modifié.
            </p>

            <hr style="border: none; border-top: 1px solid #E5E7EE; margin: 24px 0;">

            <p style="color: #6B7280; font-size: 12px;">
                Ou copiez ce lien dans votre navigateur :<br>
                <a href="{reset_url}" style="color: #6366F1;">{reset_url}</a>
            </p>
        </div>
        """

        await EmailService._send(subject, [email], body)

    @staticmethod
    async def send_request_approved(
        email: str, agent_name: str, form_title: str, form_code: str
    ) -> None:
        """Notifie l'agent que sa demande d'accès à un formulaire a été approuvée."""
        subject = f"Accès approuvé : {form_title}"
        body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #0B0F1E;">Bonjour {agent_name},</h2>

            <p>Votre demande d'accès au formulaire
            <strong>{form_title}</strong> a été <strong>approuvée</strong>.</p>

            <p>Ouvrez l'application <strong>{settings.APP_NAME}</strong>
            et utilisez le code <strong style="font-size: 18px;">{form_code}</strong>
            pour télécharger le formulaire.</p>

            <p style="color: #6B7280; font-size: 14px;">
                Bonne collecte !
            </p>
        </div>
        """

        await EmailService._send(subject, [email], body)

    @staticmethod
    async def send_request_rejected(
        email: str, agent_name: str, form_title: str, note: str | None
    ) -> None:
        """Notifie l'agent que sa demande d'accès a été refusée."""
        subject = f"Demande d'accès refusée : {form_title}"
        note_section = f"<p><strong>Motif :</strong> {note}</p>" if note else ""
        body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #0B0F1E;">Bonjour {agent_name},</h2>

            <p>Votre demande d'accès au formulaire
            <strong>{form_title}</strong> a été <strong>refusée</strong>.</p>

            {note_section}

            <p style="color: #6B7280; font-size: 14px;">
                Pour plus d'informations, contactez votre administrateur.
            </p>
        </div>
        """

        await EmailService._send(subject, [email], body)
