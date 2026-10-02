"""Create synthetic .eml fixtures for tests (sanitized — no real data)."""

from email.message import EmailMessage
from email.policy import SMTP
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent

HTML_TEMPLATE = """\
<html><body>
<p>A trav&eacute;s de nuestro sistema de alertas le informamos el siguiente movimiento.</p>
<ul>
<li>Tipo de Movimiento: <b>{tipo}</b></li>
<li>Comercio: <b>{comercio}</b></li>
<li>Importe: <b>{importe}</b></li>
<li>Moneda: <b>{moneda}</b></li>
<li>Fecha: <b>{fecha}</b></li>
<li>Hora: <b>{hora}</b></li>
<li>Cantidad cuotas: <b>01</b></li>
<li>Estado: <b>APROBADA</b></li>
<li>&Uacute;ltimos 4 d&iacute;gitos de la tarjeta: <b>0000</b></li>
<li>Ubicaci&oacute;n: <b>Argentina</b></li>
</ul>
</body></html>
"""


def make_eml(
    *,
    tipo: str = "COMPRA",
    comercio: str = "TEST*MERCHANT",
    importe: str = "1.234,56",
    moneda: str = "PESOS",
    fecha: str = "02/10/2026",
    hora: str = "13:36",
    message_id: str = "<test-0001@example.com>",
) -> bytes:
    msg = EmailMessage(policy=SMTP)
    msg["From"] = "alertas@misconsultas.com.ar"
    msg["To"] = "test@example.com"
    msg["Subject"] = "Aviso de consumo con tarjeta"
    msg["Date"] = "Fri, 02 Oct 2026 13:36:43 -0300"
    msg["Message-ID"] = message_id
    msg.set_content("Plain text fallback")
    msg.add_alternative(
        HTML_TEMPLATE.format(
            tipo=tipo,
            comercio=comercio,
            importe=importe,
            moneda=moneda,
            fecha=fecha,
            hora=hora,
        ),
        subtype="html",
    )
    return msg.as_bytes()


def write_fixtures() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    (FIXTURES_DIR / "consumo_1.eml").write_bytes(make_eml())
    (FIXTURES_DIR / "consumo_2.eml").write_bytes(
        make_eml(
            comercio="OTHER*STORE",
            importe="9.876,54",
            message_id="<test-0002@example.com>",
        )
    )
    (FIXTURES_DIR / "consumo_dolares.eml").write_bytes(
        make_eml(
            comercio="FOREIGN*SHOP",
            importe="50,00",
            moneda="DÓLARES",
            message_id="<test-0003@example.com>",
        )
    )


if __name__ == "__main__":
    write_fixtures()
    print(f"Fixtures written to {FIXTURES_DIR}")
