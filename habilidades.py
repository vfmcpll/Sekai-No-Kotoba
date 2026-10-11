# ============================================================
#  HABILIDADES
#  Catalogo de habilidades, rarezas y las tiradas (Roll y Ruleta).
#  No depende de discord: solo datos. Aqui se editan/agregan habilidades.
#
#  Tipos de habilidad:
#   - "ofensiva":  ataca. Usa "multiplicador", "costo_energia" y "cooldown_rondas".
#   - "anulacion": anula por completo el proximo golpe recibido. Usa "cooldown_rondas".
#   - "pasiva":    siempre activa, suma puntos de resistencia. Usa "resistencia".
# ============================================================
import random

# El orden importa: de la rareza mas comun a la mas rara.
RAREZA_NOMBRE = {
    "comun": "Común",
    "extra": "Extra",
    "unica": "Única",
    "definitiva": "Definitiva",
}
RAREZA_EMOJI = {"comun": "⚪", "extra": "🔵", "unica": "🟣", "definitiva": "🟡"}
RAREZA_COLOR = {"comun": 0x95A5A6, "extra": 0x3498DB, "unica": 0x9B59B6, "definitiva": 0xF1C40F}

HABILIDADES = {}


def _ofensiva(hid, nombre, rareza, desc, multiplicador, costo_energia, cooldown_rondas):
    HABILIDADES[hid] = {
        "nombre": nombre, "rareza": rareza, "tipo": "ofensiva", "descripcion": desc,
        "multiplicador": multiplicador, "costo_energia": costo_energia,
        "cooldown_rondas": cooldown_rondas,
    }


def _anulacion(hid, nombre, rareza, desc, cooldown_rondas):
    HABILIDADES[hid] = {
        "nombre": nombre, "rareza": rareza, "tipo": "anulacion", "descripcion": desc,
        "cooldown_rondas": cooldown_rondas,
    }


def _pasiva(hid, nombre, rareza, desc, resistencia):
    HABILIDADES[hid] = {
        "nombre": nombre, "rareza": rareza, "tipo": "pasiva", "descripcion": desc,
        "resistencia": resistencia,
    }


# ---------------- Comunes ----------------
_ofensiva("golpe_potenciado", "Golpe Potenciado", "comun", "Un golpe cargado con todo el cuerpo.", 1.5, 10, 2)
_ofensiva("lanzamiento_roca", "Lanzamiento de Roca", "comun", "Arroja una roca enorme al enemigo.", 1.6, 12, 3)
_pasiva("piel_dura", "Piel Dura", "comun", "Tu piel se endurece frente a los golpes.", 10)
_pasiva("resistencia_fisica", "Resistencia Física", "comun", "Resistes mejor el dolor y el cansancio.", 8)

# ---------------- Extra ----------------
_ofensiva("bola_fuego", "Bola de Fuego", "extra", "Una esfera ardiente que explota al impactar.", 2.0, 20, 3)
_ofensiva("ataque_relampago", "Ataque Relámpago", "extra", "Un golpe veloz cargado de rayo.", 2.2, 22, 3)
_anulacion("barrera_menor", "Barrera Menor", "extra", "Una barrera ligera que anula el próximo golpe.", 6)
_pasiva("piel_acorazada", "Piel Acorazada", "extra", "Una capa dura cubre tu cuerpo.", 20)

# ---------------- Unicas ----------------
_ofensiva("cuchilla_viento", "Cuchilla de Viento", "unica", "Un tajo de viento que corta casi todo.", 2.8, 28, 3)
_ofensiva("corte_dimensional", "Corte Dimensional", "unica", "Un corte que atraviesa el espacio.", 3.2, 35, 4)
_anulacion("barrera_absoluta", "Barrera Absoluta", "unica", "Anula por completo el próximo golpe recibido.", 5)
_pasiva("resistencia_magica", "Resistencia Mágica", "unica", "La magia hostil apenas te afecta.", 40)

# ---------------- Definitivas ----------------
_ofensiva("predador", "Predador", "definitiva", "Devoras la fuerza de tu enemigo con cada golpe.", 4.0, 45, 4)
_ofensiva("tormenta_abisal", "Tormenta Abisal", "definitiva", "Desatas una tormenta que arrasa con todo.", 5.0, 60, 5)
_anulacion("muro_universal", "Muro Universal", "definitiva", "Un muro imposible de atravesar.", 4)
_pasiva("gran_sabio", "Gran Sabio", "definitiva", "Tu mente anticipa cada ataque.", 70)


# ---------------- Funciones usadas por el bot ----------------
def resistencia_total(habilidades_ids):
    """Suma los puntos de resistencia de todas las habilidades pasivas (cuenta repetidas)."""
    total = 0
    for hid in habilidades_ids:
        h = HABILIDADES.get(hid)
        if h and h["tipo"] == "pasiva":
            total += h.get("resistencia", 0)
    return total


def habilidades_activas(habilidades_ids):
    """Las habilidades que se pueden usar en combate (ofensivas y de anulacion)."""
    return [hid for hid in habilidades_ids if hid in HABILIDADES and HABILIDADES[hid]["tipo"] in ("ofensiva", "anulacion")]


# ---------------- Tiradas ----------------
COSTO_ROLL = 500
COSTO_RULETA = 5000

# Probabilidad relativa de cada rareza
PESOS_ROLL = {"comun": 70, "extra": 25, "unica": 4.5, "definitiva": 0.5}
PESOS_RULETA = {"comun": 30, "extra": 40, "unica": 25, "definitiva": 5}


def tirar_habilidad(pesos):
    """Elige una rareza segun los pesos y despues una habilidad al azar de esa rareza. Devuelve su id."""
    rarezas = [r for r in RAREZA_NOMBRE if pesos.get(r, 0) > 0 and any(h["rareza"] == r for h in HABILIDADES.values())]
    rareza = random.choices(rarezas, weights=[pesos[r] for r in rarezas])[0]
    return random.choice([hid for hid, h in HABILIDADES.items() if h["rareza"] == rareza])


def texto_habilidad(h):
    """Descripcion corta de lo que hace una habilidad."""
    if h["tipo"] == "ofensiva":
        return f'Ataque x{h["multiplicador"]} · {h["costo_energia"]} de energía · enfriamiento {h["cooldown_rondas"]}t'
    if h["tipo"] == "anulacion":
        return f'Anula el próximo golpe recibido · enfriamiento {h["cooldown_rondas"]}t'
    return f'Pasiva: +{h["resistencia"]} puntos de resistencia'
