import logging
import smtplib
from email.header import Header
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from app.services.runtime_config import get_bool, get_int, get_secret, get_str

logger = logging.getLogger(__name__)


class EmailDeliveryError(ValueError):
    """SMTP 发送失败，消息可直接展示给调用方。"""


def send_email(db: Session, to: str, subject: str, body: str) -> None:
    if not get_bool(db, "email_enabled", False):
        raise EmailDeliveryError("邮件服务未启用")

    host = get_str(db, "smtp_host").strip()
    port = get_int(db, "smtp_port", 465)
    user = get_str(db, "smtp_user").strip()
    password = (get_secret(db, "smtp_password") or "").strip()
    from_addr = (get_str(db, "smtp_from") or user).strip()
    use_tls = get_bool(db, "smtp_use_tls", True)

    if not host:
        raise EmailDeliveryError("未配置 SMTP 主机")
    if not from_addr:
        raise EmailDeliveryError("未配置发件人地址")
    if user and not password:
        raise EmailDeliveryError("未配置 SMTP 密码或授权码")

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = str(Header(subject, "utf-8"))
    msg["From"] = from_addr
    msg["To"] = to

    try:
        if port == 465:
            server: smtplib.SMTP = smtplib.SMTP_SSL(host, port, timeout=20)
        else:
            server = smtplib.SMTP(host, port, timeout=20)
            server.ehlo()
            if use_tls:
                server.starttls()
                server.ehlo()
        try:
            if user:
                server.login(user, password)
            server.sendmail(from_addr, [to], msg.as_string())
        finally:
            try:
                server.quit()
            except Exception:
                pass
    except EmailDeliveryError:
        raise
    except smtplib.SMTPAuthenticationError as exc:
        logger.warning("SMTP auth failed host=%s user=%s: %s", host, user, exc)
        raise EmailDeliveryError("SMTP 认证失败，请检查用户名和授权码") from exc
    except (TimeoutError, OSError, smtplib.SMTPException) as exc:
        logger.exception("send_email failed host=%s port=%s", host, port)
        raise EmailDeliveryError(f"邮件发送失败：{exc}") from exc


def try_send_email(db: Session, to: str, subject: str, body: str) -> bool:
    try:
        send_email(db, to, subject, body)
        return True
    except EmailDeliveryError as exc:
        logger.info("email skipped to=%s: %s", to, exc)
        return False
