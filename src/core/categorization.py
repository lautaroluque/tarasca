"""Rule-based categorization engine with Spanish keywords."""

from typing import Any

# Default categories with Spanish keywords
DEFAULT_CATEGORIES = [
    {
        "name": "Vivienda",
        "color": "#FF6B6B",
        "icon": "🏠",
        "keywords": [
            "alquiler",
            "hipoteca",
            "prestamo",
            "mantenimiento",
            "reparacion",
            "hogar",
            "muebles",
            "decoracion",
            "jardin",
            "limpieza",
        ],
    },
    {
        "name": "Alimentación",
        "color": "#4ECDC4",
        "icon": "🍽️",
        "keywords": [
            "supermercado",
            "restaurante",
            "comida",
            "alimento",
            "verduleria",
            "carniceria",
            "panaderia",
            "pizzeria",
            "hamburguesa",
            "sushi",
            "cafe",
            "bar",
            "pub",
            "mercado",
            "coto",
            "carrefour",
            "walmart",
            "dia",
            "jumbo",
            "pedidosya",
            "uber eats",
            "rappi",
            "mostaza",
            "burger",
            "mcdonalds",
            "mc donalds",
            "starbucks",
            "heladeria",
            "rotiseria",
            "empanada",
            "pollo",
            "carne",
            "pescado",
            "fruta",
            "verdura",
            "lacteo",
            "queso",
            "vino",
            "cerveza",
            "bebida",
        ],
    },
    {
        "name": "Transporte",
        "color": "#45B7D1",
        "icon": "🚗",
        "keywords": [
            "uber",
            "cabify",
            "taxi",
            "remis",
            "colectivo",
            "bus",
            "subte",
            "metro",
            "tren",
            "avion",
            "vuelo",
            "aerolinea",
            "combustible",
            "nafta",
            "gasoil",
            "estacion",
            "parking",
            "peaje",
            "patente",
            "seguro auto",
            "mecanico",
            "taller",
            "lavado",
            "gomeria",
            "neumatico",
            "auto",
            "moto",
            "bicicleta",
            "monopatin",
            "scooter",
        ],
    },
    {
        "name": "Servicios",
        "color": "#96CEB4",
        "icon": "💡",
        "keywords": [
            "luz",
            "electricidad",
            "gas",
            "agua",
            "cloaca",
            "internet",
            "wifi",
            "telefono",
            "celular",
            "movil",
            "cable",
            "tv",
            "streaming",
            "apple",
            "google",
            "microsoft",
            "software",
            "suscripcion",
            "club",
            "gimnasio",
            "fitness",
            "yoga",
            "pilates",
            "natacion",
            "medico",
            "consulta",
            "farmacia",
            "remedio",
            "hospital",
            "clinica",
            "odontologo",
            "laboratorio",
            "analisis",
            "seguro",
            "poliza",
            "impuesto",
            "tasa",
            "multa",
            "banco",
            "comision",
            "mantenimiento cuenta",
        ],
    },
    {
        "name": "Entretenimiento",
        "color": "#FFEAA7",
        "icon": "🎬",
        "keywords": [
            "cine",
            "pelicula",
            "teatro",
            "concierto",
            "show",
            "fiesta",
            "evento",
            "entrada",
            "ticket",
            "netflix",
            "spotify",
            "youtube",
            "disney",
            "hbo",
            "amazon prime",
            "juego",
            "videojuego",
            "steam",
            "playstation",
            "xbox",
            "nintendo",
            "libro",
            "revista",
            "musica",
            "disco",
            "bar",
            "pub",
            "cerveza",
            "cocktail",
            "vacaciones",
            "viaje",
            "turismo",
            "hotel",
            "airbnb",
            "excursion",
            "parque",
            "museo",
            "zoo",
            "acuario",
        ],
    },
    {
        "name": "Salud",
        "color": "#DDA0DD",
        "icon": "🏥",
        "keywords": [
            "medico",
            "doctor",
            "consulta",
            "farmacia",
            "remedio",
            "pastilla",
            "hospital",
            "clinica",
            "emergencia",
            "ambulancia",
            "odontologo",
            "dentista",
            "ortodoncia",
            "laboratorio",
            "analisis",
            "estudio",
            "radiografia",
            "ecografia",
            "resonancia",
            "terapia",
            "psicologo",
            "psiquiatra",
            "fisioterapia",
            "kinesiologia",
            "optica",
            "lentes",
            "gafas",
        ],
    },
    {
        "name": "Compras",
        "color": "#F0E68C",
        "icon": "🛍️",
        "keywords": [
            "ropa",
            "vestido",
            "pantalon",
            "remera",
            "camisa",
            "zapato",
            "zapatilla",
            "bolso",
            "mochila",
            "accesorio",
            "joyeria",
            "reloj",
            "perfume",
            "cosmetico",
            "maquillaje",
            "shampoo",
            "jabon",
            "electrodomestico",
            "celular",
            "computadora",
            "laptop",
            "tablet",
            "auricular",
            "parlante",
            "television",
            "heladera",
            "lavarropas",
            "microondas",
            "licuadora",
            "cafetera",
            "amazon",
            "mercado libre",
            "aliexpress",
            "ebay",
            "zara",
            "h&m",
            "nike",
            "adidas",
            "samsung",
            "apple",
            "lg",
            "philips",
        ],
    },
    {
        "name": "Ingresos",
        "color": "#98D8C8",
        "icon": "💰",
        "keywords": [
            "sueldo",
            "salario",
            "transferencia recibida",
            "deposito",
            "reembolso",
            "devolucion",
            "premio",
            "bonus",
            "aguinaldo",
            "vacaciones",
            "indemnizacion",
            "alquiler",
            "rendimiento",
            "interes",
            "dividendo",
            "venta",
            "ganancia",
        ],
    },
    {
        "name": "Transferencias",
        "color": "#C0C0C0",
        "icon": "🔄",
        "keywords": [
            "transferencia",
            "envio",
            "pago",
            "debito",
            "credito",
            "conversion",
            "conversión",
            "retiro",
            "fiwind",
            "mercado pago",
            "uala",
            "brubank",
            "nubank",
            "personal",
            "galicia",
            "santander",
            "bbva",
            "macro",
            "hsbc",
            "itau",
            "patagonia",
        ],
    },
    {
        "name": "Otros",
        "color": "#808080",
        "icon": "📦",
        "keywords": [],
    },
]


def get_default_categories() -> list[dict[str, Any]]:
    """Get default categories with keywords."""
    return DEFAULT_CATEGORIES


def categorize_transaction(description: str, categories: list[dict[str, Any]]) -> str | None:
    """Categorize a transaction based on description keywords.

    Args:
        description: Transaction description
        categories: List of categories with keywords

    Returns:
        Category name or None if no match
    """
    description_lower = description.lower()

    # Define priority order for categories (more specific first)
    priority_order = [
        "Alimentación",
        "Transporte",
        "Entretenimiento",
        "Salud",
        "Compras",
        "Vivienda",
        "Servicios",
        "Ingresos",
        "Transferencias",
        "Otros",
    ]

    # Sort categories by priority
    sorted_categories = sorted(
        categories,
        key=lambda c: priority_order.index(c["name"])
        if c["name"] in priority_order
        else 999,
    )

    for category in sorted_categories:
        keywords = category.get("keywords", [])
        for keyword in keywords:
            if keyword.lower() in description_lower:
                return str(category["name"])

    return None


def get_category_keywords(category_name: str) -> list[str]:
    """Get keywords for a specific category."""
    for category in DEFAULT_CATEGORIES:
        if category["name"] == category_name:
            return list(category.get("keywords", []))
    return []


def add_custom_keyword(category_name: str, keyword: str) -> None:
    """Add a custom keyword to a category."""
    for category in DEFAULT_CATEGORIES:
        if category["name"] == category_name:
            keywords = list(category.get("keywords", []))
            if keyword.lower() not in [k.lower() for k in keywords]:
                keywords.append(keyword.lower())
                category["keywords"] = keywords
            break


def remove_custom_keyword(category_name: str, keyword: str) -> None:
    """Remove a custom keyword from a category."""
    for category in DEFAULT_CATEGORIES:
        if category["name"] == category_name:
            category["keywords"] = [
                k for k in category.get("keywords", []) if k.lower() != keyword.lower()
            ]
            break
