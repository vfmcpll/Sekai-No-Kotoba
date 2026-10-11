# ============================================================
#  HABILIDADES DE TENSURA
#  Nombres y tematica basados en el canon (novela ligera / anime):
#  Comunes y Extras son skills genericas que existen en la obra
#  (manipulacion de elementos, resistencias, percepcion, etc.).
#  Unicas y Definitivas usan nombres reales de Skills Unicas y de
#  Habilidades Ultimate (Gluttony/Beelzebuth, Uriel, Raphael, la
#  serie de Pecados/Virtudes de Guy Crimson, etc).
#  Los NUMEROS de juego (multiplicador, % de resistencia, costo de
#  energia, enfriamiento) son un balance propio: la obra no es un
#  juego y no trae esas cifras exactas.
#
#  tipo == "ofensiva"   -> golpe con multiplicador propio (gasta energia)
#  tipo == "anulacion"  -> bloquea por completo el siguiente golpe recibido (gratis)
#  tipo == "resistencia"-> pasiva: reduce el dano recibido durante todo el combate
# ============================================================
import random

RAREZA_NOMBRE = {"comun": "Común", "extra": "Extra", "unica": "Única", "definitiva": "Definitiva"}
RAREZA_EMOJI = {"comun": "⚪", "extra": "🔵", "unica": "🟣", "definitiva": "🟡"}
RAREZA_COLOR = {"comun": 0xB0B0B0, "extra": 0x3498DB, "unica": 0x9B59B6, "definitiva": 0xF1C40F}

HABILIDADES = {}


def _of(hid, nombre, rareza, descripcion, multiplicador, costo_energia, cooldown_rondas):
    HABILIDADES[hid] = {
        "nombre": nombre, "rareza": rareza, "tipo": "ofensiva", "descripcion": descripcion,
        "multiplicador": multiplicador, "costo_energia": costo_energia, "cooldown_rondas": cooldown_rondas,
    }


def _anu(hid, nombre, rareza, descripcion, cooldown_rondas):
    HABILIDADES[hid] = {
        "nombre": nombre, "rareza": rareza, "tipo": "anulacion", "descripcion": descripcion,
        "cooldown_rondas": cooldown_rondas,
    }


def _res(hid, nombre, rareza, descripcion, elemento, porcentaje):
    HABILIDADES[hid] = {
        "nombre": nombre, "rareza": rareza, "tipo": "resistencia", "descripcion": descripcion,
        "elemento": elemento, "porcentaje": porcentaje,
    }


# ---------------- COMUNES ----------------
_res("deteccion_presencia", "Detección de Presencia", "comun",
     "Percibe la energía vital y mágica cercana, anticipando el golpe enemigo.",
     "todo tipo de daño", 5)
_res("resistencia_dolor", "Resistencia al Dolor", "comun",
     "Reduce el dolor y el impacto de los golpes recibidos.",
     "todo tipo de daño", 8)
_res("autorregeneracion", "Autorregeneración", "comun",
     "Cierra heridas leves de forma natural durante el combate.",
     "todo tipo de daño", 6)
_res("sentidos_agudizados", "Sentidos Agudizados", "comun",
     "Agudiza los sentidos para reaccionar mejor a los ataques.",
     "todo tipo de daño", 6)
_anu("camuflaje", "Camuflaje", "comun",
     "Se mimetiza con el entorno, esquivando el próximo ataque.", 3)
_anu("salto_mejorado", "Salto Mejorado", "comun",
     "Un salto explosivo que esquiva por completo el siguiente golpe.", 3)
_of("fuerza_mejorada", "Fuerza Mejorada", "comun",
    "Aumenta la fuerza física por un instante para golpear más fuerte.",
    1.3, 10, 2)
_of("comunicacion_telepatica", "Comunicación Telepática", "comun",
    "Coordina cuerpo y mente para golpear con más precisión.",
    1.25, 8, 2)

# ---------------- EXTRAS ----------------
_of("manipulacion_termica", "Manipulación Térmica", "extra",
    "Controla el calor a voluntad, una habilidad absorbida de un espíritu de fuego.",
    1.7, 20, 2)
_of("manipulacion_agua", "Manipulación del Agua", "extra",
    "Controla el agua circundante para golpear con fuerza.",
    1.6, 18, 2)
_of("manipulacion_viento", "Manipulación del Viento", "extra",
    "Controla ráfagas de viento cortante contra el objetivo.",
    1.65, 19, 2)
_of("lanzamiento_multiple", "Lanzamiento Múltiple", "extra",
    "Lanza varios proyectiles o golpes encadenados a gran velocidad.",
    1.75, 20, 2)
_of("manipulacion_gravedad", "Manipulación de la Gravedad", "extra",
    "Distorsiona la gravedad alrededor del objetivo para aplastarlo.",
    1.9, 25, 3)
_anu("barrera_magica", "Barrera Mágica", "extra",
     "Una barrera de energía que anula por completo un ataque entrante.", 3)
_res("resistencia_corrosion", "Resistencia a la Corrosión", "extra",
     "Vuelve el cuerpo resistente a venenos y ácidos corrosivos.",
     "veneno y corrosión", 15)
_res("resistencia_fisica", "Resistencia Física", "extra",
     "Endurece el cuerpo frente a los golpes físicos.",
     "ataques físicos", 15)

# ---------------- UNICAS (nacen de una emocion o deseo fuerte, una por persona) ----------------
_of("gluttony", "Gluttony (Glotonería)", "unica",
    "Skill Única que devora al objetivo, analizándolo y absorbiendo parte de su poder.",
    2.1, 35, 2)
_of("berserker", "Berserker", "unica",
    "Libera una furia de combate que multiplica la fuerza de los golpes.",
    2.3, 30, 2)
_of("absolute_severance", "Absolute Severance (Corte Absoluto)", "unica",
    "Un corte capaz de separar cualquier cosa, sin importar su dureza.",
    2.4, 38, 3)
_of("starved", "Starved (Hambriento)", "unica",
    "Nacida del hambre extrema, devora al enemigo para saciarse.",
    2.2, 35, 2)
_anu("usurper", "Usurper (Usurpador)", "unica",
     "Arrebata la ventaja al rival, anulando por completo su ataque.", 3)
_anu("infinity_prison", "Infinity Prison (Prisión Infinita)", "unica",
     "Aprisiona el golpe entrante en un espacio aislado antes de que impacte.", 4)
_res("great_sage", "Great Sage (Gran Sabio)", "unica",
     "Calcula y analiza el combate al detalle, anticipando cada ataque.",
     "todo tipo de daño", 22)
_res("commander", "Commander (Comandante)", "unica",
     "El instinto de mando fortalece al usuario en pleno combate.",
     "todo tipo de daño", 20)
_res("creator", "Creator (Creador)", "unica",
     "Moldea y refuerza la materia, incluyendo el propio cuerpo del usuario.",
     "todo tipo de daño", 25)
_res("chef", "Chef", "unica",
     "Nacida del amor por cocinar, nutre y sostiene el cuerpo del usuario.",
     "todo tipo de daño", 18)

# ---------------- DEFINITIVAS (Habilidades Ultimate, las mas raras) ----------------
_of("beelzebuth", "Beelzebuth, Señor de la Gula", "definitiva",
    "Evolución de Gluttony: devora materia, energía e incluso espacio sin dejar rastro.",
    3.0, 65, 3)
_of("lucifer", "Lucifer, Señor del Orgullo", "definitiva",
    "Una de las Habilidades del Pecado: un poder abrumador nacido del orgullo del usuario.",
    2.9, 60, 3)
_of("satanael", "Satanael, Señor de la Ira", "definitiva",
    "Una de las Habilidades del Pecado: canaliza una ira devastadora en un solo golpe.",
    3.2, 68, 3)
_of("leviathan", "Leviathan, Señor de la Envidia", "definitiva",
    "Una de las Habilidades del Pecado: arrebata parte del poder del objetivo al golpearlo.",
    2.8, 58, 3)
_of("mammon", "Mammon, Señor de la Avaricia", "definitiva",
    "Una de las Habilidades del Pecado: acumula todo el poder que consume, sin devolver nada.",
    2.7, 55, 3)
_anu("uriel", "Uriel, Señor del Juramento", "definitiva",
     "Evolución de Infinity Prison: una guardia absoluta que anula cualquier ataque entrante.", 4)
_anu("michael", "Michael, Señor de la Justicia", "definitiva",
     "Una de las Habilidades Angelicales: domina la voluntad ajena, deteniendo el ataque rival.", 5)
_res("raphael", "Raphael, Señor de la Sabiduría", "definitiva",
     "Evolución de Great Sage: calcula y gestiona el combate con precisión casi perfecta.",
     "todo tipo de daño", 40)


LISTA_POR_RAREZA = {r: [hid for hid, h in HABILIDADES.items() if h["rareza"] == r] for r in RAREZA_NOMBRE}

COSTO_ROLL = 100
COSTO_RULETA = 1000

# Pesos relativos por rareza (no hace falta que sumen 100)
PESOS_ROLL = {"comun": 60, "extra": 30, "unica": 9, "definitiva": 1}
PESOS_RULETA = {"comun": 20, "extra": 35, "unica": 35, "definitiva": 10}


def tirar_habilidad(pesos, excluir):
    """Elige una habilidad al azar que el jugador (en 'excluir') no tenga todavia.
    Devuelve None si ya tiene las 34 habilidades posibles."""
    candidatos = {r: [hid for hid in ids if hid not in excluir] for r, ids in LISTA_POR_RAREZA.items()}
    disponibles = [r for r in candidatos if candidatos[r]]
    if not disponibles:
        return None
    pesos_filtrados = [pesos[r] for r in disponibles]
    rareza = random.choices(disponibles, weights=pesos_filtrados, k=1)[0]
    return random.choice(candidatos[rareza])


def resistencia_total(habilidades_ids):
    """Suma el % de resistencia pasiva de todas las habilidades de tipo 'resistencia' que se tengan."""
    total = 0
    for hid in habilidades_ids:
        h = HABILIDADES.get(hid)
        if h and h["tipo"] == "resistencia":
            total += h["porcentaje"]
    return total


def habilidades_activas(habilidades_ids):
    """Habilidades que se pueden elegir y usar durante un turno de combate."""
    return [hid for hid in habilidades_ids if hid in HABILIDADES and HABILIDADES[hid]["tipo"] in ("ofensiva", "anulacion")]
