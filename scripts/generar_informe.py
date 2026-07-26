from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "informe-reflexion-cicd.pdf"

NAVY = colors.HexColor("#172554")
BLUE = colors.HexColor("#2563EB")
PALE_BLUE = colors.HexColor("#EFF6FF")
GREEN = colors.HexColor("#15803D")
PALE_GREEN = colors.HexColor("#F0FDF4")
INK = colors.HexColor("#172033")
MUTED = colors.HexColor("#5B6475")
LINE = colors.HexColor("#D8DEE9")
PAPER = colors.HexColor("#F8FAFC")


def footer(canvas, doc):
    canvas.saveState()
    width, _ = A4
    canvas.setStrokeColor(LINE)
    canvas.line(18 * mm, 14 * mm, width - 18 * mm, 14 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(18 * mm, 9 * mm, "Sistemas Distribuidos - inventario-app")
    canvas.drawRightString(width - 18 * mm, 9 * mm, f"Página {doc.page}")
    canvas.restoreState()


def metric_card(value, label, color):
    value_style = ParagraphStyle(
        "MetricValue",
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=19,
        textColor=color,
        alignment=TA_CENTER,
    )
    label_style = ParagraphStyle(
        "MetricLabel",
        fontName="Helvetica",
        fontSize=7.8,
        leading=9.5,
        textColor=MUTED,
        alignment=TA_CENTER,
    )
    return Table(
        [[Paragraph(value, value_style)], [Paragraph(label, label_style)]],
        colWidths=[50 * mm],
        rowHeights=[10 * mm, 10 * mm],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.7, LINE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        ),
    )


styles = getSampleStyleSheet()
title = ParagraphStyle(
    "TitleCustom",
    parent=styles["Title"],
    fontName="Helvetica-Bold",
    fontSize=23,
    leading=27,
    textColor=NAVY,
    alignment=TA_LEFT,
    spaceAfter=4,
)
subtitle = ParagraphStyle(
    "Subtitle",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=10,
    leading=13,
    textColor=MUTED,
    spaceAfter=9,
)
heading = ParagraphStyle(
    "HeadingCustom",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=13,
    leading=16,
    textColor=NAVY,
    spaceBefore=7,
    spaceAfter=5,
)
body = ParagraphStyle(
    "BodyCustom",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=9.2,
    leading=12.3,
    textColor=INK,
    alignment=TA_LEFT,
    spaceAfter=5,
)
small = ParagraphStyle(
    "Small",
    parent=body,
    fontSize=7.7,
    leading=9.5,
    spaceAfter=0,
)
table_header = ParagraphStyle(
    "TableHeader",
    parent=small,
    fontName="Helvetica-Bold",
    textColor=colors.white,
)
callout = ParagraphStyle(
    "Callout",
    parent=body,
    fontSize=9,
    leading=12,
    textColor=NAVY,
    leftIndent=8,
    rightIndent=8,
    spaceBefore=5,
    spaceAfter=5,
)


def paragraph(text, style=body):
    return Paragraph(text, style)


OUTPUT.parent.mkdir(parents=True, exist_ok=True)
doc = SimpleDocTemplate(
    str(OUTPUT),
    pagesize=A4,
    rightMargin=18 * mm,
    leftMargin=18 * mm,
    topMargin=15 * mm,
    bottomMargin=19 * mm,
    title="Informe de reflexión - Pipeline CI/CD de inventario-app",
    author="Alex Chuquipoma",
    subject="Sistemas Distribuidos",
)

story = [
    paragraph("INFORME DE REFLEXIÓN", ParagraphStyle(
        "Eyebrow", parent=subtitle, fontName="Helvetica-Bold",
        fontSize=8.5, textColor=BLUE, spaceAfter=2
    )),
    paragraph("Pipeline CI/CD de inventario-app", title),
    paragraph(
        "Sistemas Distribuidos · Alex Chuquipoma · 26 de julio de 2026<br/>"
        "github.com/AlexChuquipoma/inventario-app",
        subtitle,
    ),
]

summary_box = Table(
    [[paragraph(
        "<b>Resultado.</b> Pipeline fail-fast con pruebas, Docker multi-stage, "
        "publicación en GHCR, RollingUpdate, Blue-Green y los tres componentes "
        "adicionales: Secret, Trivy y readiness con arranque lento.",
        callout,
    )]],
    colWidths=[174 * mm],
    style=TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, -1), PALE_BLUE),
            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#BFDBFE")),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]
    ),
)
story.extend(
    [
        summary_box,
        paragraph("Estrategia elegida: Blue-Green", heading),
        paragraph(
            "Elegí Blue-Green porque <b>/version</b> expone versión, color y "
            "hostname. Esto permite validar Green antes del corte y comprobar "
            "de forma determinista qué versión recibe el tráfico. El Service "
            "cambia su selector entre <b>slot: blue</b> y <b>slot: green</b>; "
            "el cambio y el rollback son inmediatos y usan solo Deployment y "
            "Service nativos de Kubernetes."
        ),
        paragraph(
            "Para esta app, Canary habría hecho la evidencia probabilística y "
            "más difícil de interpretar porque cada pod mantiene su propio "
            "archivo JSON. El costo de ejecutar temporalmente dos ambientes es "
            "aceptable en Minikube."
        ),
        paragraph("Métricas DORA propias", heading),
    ]
)

cards = Table(
    [[
        metric_card("00:11:48", "Lead time promedio<br/>(5 cambios)", BLUE),
        metric_card("7 / día", "Frecuencia<br/>(7 éxitos, 1 día)", GREEN),
        metric_card("12,5 %", "Change failure rate<br/>(1 de 8 intentos)", colors.HexColor("#B45309")),
    ]],
    colWidths=[58 * mm, 58 * mm, 58 * mm],
    style=TableStyle(
        [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]
    ),
)
story.extend([cards, Spacer(1, 4 * mm)])

lead_rows = [
    ["Commit", "Cambio", "Commit UTC", "Clúster UTC", "Lead time"],
    ["0568410", "Pipeline e imagen inicial", "17:08:05", "17:36:52", "00:28:47"],
    ["117567a", "Rolling deployment", "17:58:11", "18:02:16.297", "00:04:05.297"],
    ["1077675", "Arranque lento y probes", "18:40:20", "18:50:19.821", "00:09:59.821"],
    ["99d4de3", "Secret API_KEY", "18:58:22", "19:03:31", "00:05:09"],
    ["30fb843", "Trivy y runtime seguro", "19:24:37", "19:35:36", "00:10:59"],
]
lead_table = Table(
    [
        [
            paragraph(str(cell), table_header if row_index == 0 else small)
            for cell in row
        ]
        for row_index, row in enumerate(lead_rows)
    ],
    colWidths=[22 * mm, 53 * mm, 31 * mm, 33 * mm, 34 * mm],
    repeatRows=1,
)
lead_table.setStyle(
    TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, LINE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PAPER]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
    )
)
story.extend(
    [
        lead_table,
        paragraph(
            "<b>Metodología.</b> Se normalizaron a UTC los timestamps de Git y "
            "los momentos observados o registrados por Kubernetes. La "
            "frecuencia cuenta siete promociones exitosas que crearon o "
            "actualizaron Deployments. Los cortes del Service Blue-Green no "
            "crean revisiones y se registraron aparte. El único intento fallido "
            "fue el primer Deployment base; requirió una corrección. El rollback "
            "Blue-Green fue planificado y no se clasificó como fallo.",
            small,
        ),
        PageBreak(),
        paragraph("Persistencia y comportamiento distribuido", heading),
        paragraph(
            "El producto <b>POD-001</b>, creado directamente en un pod, "
            "desapareció al eliminar ese pod y esperar su reemplazo. "
            "<b>data/products.json</b> vive en la capa efímera de cada "
            "contenedor: no es almacenamiento compartido y dos réplicas pueden "
            "mostrar catálogos diferentes. En producción se necesitaría una "
            "base externa o una estrategia de almacenamiento compatible con "
            "múltiples réplicas; aumentar réplicas por sí solo no soluciona la "
            "persistencia."
        ),
        paragraph("Problemas reales y soluciones", heading),
    ]
)

issues = [
    (
        "1. Identidad non-root",
        "El primer rollout quedó en <b>CreateContainerConfigError</b>. Aunque "
        "la imagen usaba <b>USER node</b>, Kubernetes no podía comprobar un "
        "usuario no numérico. Se mantuvo <b>runAsNonRoot: true</b> y se "
        "declararon <b>runAsUser/runAsGroup: 1000</b>.",
    ),
    (
        "2. Vulnerabilidad crítica",
        "Trivy encontró <b>CVE-2026-59873</b> en <b>tar 7.5.15</b>, arrastrado "
        "por el npm global del runtime. npm/npx se conservaron en build para "
        "instalar, probar y podar dependencias, y se eliminaron del runtime. "
        "El reescaneo terminó con código 0 y la app siguió respondiendo 200.",
    ),
    (
        "3. Selectores superpuestos",
        "<b>kubectl exec deployment/inventario-app</b> podía seleccionar un "
        "pod Blue-Green por compartir <b>app=inventario-app</b>. Las "
        "verificaciones del Deployment base pasaron a usar "
        "<b>app=inventario-app,!slot</b>, haciendo inequívoca la evidencia.",
    ),
]
for label, text in issues:
    issue_table = Table(
        [[paragraph(f"<b>{label}</b><br/>{text}", body)]],
        colWidths=[174 * mm],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        ),
    )
    story.extend([KeepTogether([issue_table, Spacer(1, 2.5 * mm)])])

story.extend(
    [
        paragraph("Tres buenas prácticas implementadas", heading),
        Table(
            [
                [
                    paragraph("<b>Secret</b><br/>API_KEY por secretKeyRef; Git no contiene el valor.", small),
                    paragraph("<b>Trivy</b><br/>CRITICAL bloquea los push de commit y latest.", small),
                    paragraph("<b>Readiness realista</b><br/>503 inicial, startupProbe y tráfico solo al estar listo.", small),
                ]
            ],
            colWidths=[58 * mm, 58 * mm, 58 * mm],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), PALE_GREEN),
                    ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#BBF7D0")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BBF7D0")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            ),
        ),
        paragraph("Reflexión final", heading),
        paragraph(
            "La automatización útil no termina cuando una imagen compila. Las "
            "pruebas reducen errores funcionales; Trivy evita publicar una "
            "imagen crítica; los probes impiden enviar tráfico a procesos aún "
            "no listos; el Secret separa la credencial del código; y "
            "Blue-Green limita el riesgo del cambio de versión. DORA hizo "
            "visible el tiempo completo hasta el clúster, no solo la duración "
            "del workflow. El aprendizaje principal fue poder reproducir tanto "
            "los éxitos como los fallos y explicar por qué ocurrieron."
        ),
    ]
)

doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUTPUT)
