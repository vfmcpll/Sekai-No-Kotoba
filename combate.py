# ============================================================
#  SISTEMA DE COMBATE - ZONAS Y MONSTRUOS
#  Aqui se editan las zonas del continente, los monstruos de
#  cada una, sus recompensas y las formulas de combate.
#  No depende de discord: solo datos y calculos, para poder
#  probarlo sin conectar el bot.
# ============================================================
import random
from razas import RAZAS, beneficios_etapa

# ---------------- Estadisticas del jugador segun su raza ----------------
def vida_maxima(raza_id, etapa):
    """Vida maxima del jugador. Las resistencias de su raza suman vida extra."""
    r = RAZAS[raza_id]
    _, res = beneficios_etapa(raza_id, etapa)
    return 100 + r["dificultad"] * 40 + etapa * 60 + sum(res.values())


def energia_maxima(raza_id, etapa):
    """Energia maxima del jugador. El dano de su raza suma energia extra."""
    r = RAZAS[raza_id]
    dano, _ = beneficios_etapa(raza_id, etapa)
    return 60 + r["dificultad"] * 25 + etapa * 35 + sum(dano.values())


def ataque_base_jugador(raza_id, etapa):
    r = RAZAS[raza_id]
    return 14 + r["dificultad"] * 4 + etapa * 9


def multiplicador_dano(raza_id, etapa):
    """Cuanto mas % de dano tenga la raza, mas fuerte golpea (tope orientativo)."""
    dano, _ = beneficios_etapa(raza_id, etapa)
    return 1 + sum(dano.values()) / 200


def reduccion_dano(raza_id, etapa, bonus_extra=0):
    """Cuanto mas % de resistencia (de raza + habilidades) tenga, menos dano recibe (tope 60%)."""
    _, res = beneficios_etapa(raza_id, etapa)
    return min((sum(res.values()) + bonus_extra) / 300, 0.6)


# ---------------- Monstruos ----------------
MONSTRUOS = {}


def _m(mid, nombre, emoji, vida, energia, ataque, especial_nombre, especial_costo,
       exp, ep, materiales, gif=None):
    MONSTRUOS[mid] = {
        "nombre": nombre, "emoji": emoji,
        "vida_max": vida, "energia_max": energia, "ataque": ataque,
        "especial_nombre": especial_nombre, "especial_costo": especial_costo,
        "exp": exp, "ep": ep, "materiales": materiales,  # [(nombre, probabilidad 0-1), ...]
        "gif": gif,  # URL opcional de gif/imagen para este monstruo (tu la agregas si quieres)
    }


# --- Tier 1: Linde del Bosque de Jura ---
_m("slime_salvaje", "Slime Salvaje", "🟢", 70, 30, 8, "Salto Ácido", 10, 40, 30,
   [("Gel de slime", 0.7), ("Núcleo pequeño", 0.15)])
_m("goblin_explorador", "Goblin Explorador", "👺", 90, 35, 10, "Golpe Sucio", 12, 55, 40,
   [("Daga oxidada", 0.4), ("Piel de goblin", 0.6)])
_m("lobezno_jura", "Lobezno de Jura", "🐺", 80, 30, 12, "Mordisco Feroz", 10, 50, 35,
   [("Colmillo de lobo", 0.5), ("Pelaje gris", 0.5)])

# --- Tier 2: Bosque Interior ---
_m("orco_merodeador", "Orco Merodeador", "🐗", 160, 50, 18, "Embestida Brutal", 18, 120, 90,
   [("Colmillo de orco", 0.5), ("Cuero grueso", 0.5)])
_m("arana_gigante_salvaje", "Araña Gigante Salvaje", "🕷️", 140, 55, 16, "Hilo Venenoso", 16, 110, 85,
   [("Seda de araña", 0.6), ("Veneno concentrado", 0.3)])
_m("lobo_colmillos_salvaje", "Lobo de Colmillos Salvaje", "🐕", 150, 50, 20, "Aullido de Caza", 18, 130, 95,
   [("Colmillo afilado", 0.5), ("Pelaje plateado", 0.4)])

# --- Tier 3: Pantano de las Sombras ---
_m("serpiente_negra_salvaje", "Serpiente Negra Salvaje", "🐍", 220, 70, 26, "Mordisco Ponzoñoso", 22, 220, 170,
   [("Colmillo venenoso", 0.5), ("Escama negra", 0.4)])
_m("lagarto_pantanero", "Lagarto Pantanero", "🦎", 260, 65, 24, "Latigazo de Cola", 20, 210, 160,
   [("Escama de lagarto", 0.5), ("Cuero pantanoso", 0.4)])
_m("insectoide_gigante", "Insectoide Gigante", "🐜", 240, 75, 28, "Carga Perforante", 24, 230, 180,
   [("Caparazón duro", 0.5), ("Mandíbula quitinosa", 0.4)])

# --- Tier 4: Cuevas Heladas ---
_m("tigre_cuchilla_salvaje", "Tigre Cuchilla Salvaje", "🐅", 380, 90, 38, "Zarpazo Relámpago", 28, 400, 320,
   [("Garra afilada", 0.5), ("Pelaje rayado", 0.4)])
_m("armorsaurio_salvaje", "Armorsaurio Salvaje", "🦖", 520, 80, 34, "Embestida Blindada", 26, 420, 340,
   [("Placa blindada", 0.5), ("Núcleo terrestre", 0.3)])
_m("no_muerto_errante", "No-muerto Errante", "💀", 400, 100, 36, "Toque Marchito", 30, 440, 350,
   [("Hueso maldito", 0.5), ("Esencia oscura", 0.3)])

# --- Tier 5: Guarida Oscura ---
_m("vampiro_renegado", "Vampiro Renegado", "🧛", 650, 130, 55, "Golpe Sanguinario", 36, 800, 650,
   [("Colmillo vampírico", 0.5), ("Sangre oscura", 0.3)])
_m("demonio_menor_salvaje", "Demonio Menor Salvaje", "😈", 700, 140, 58, "Ráfaga Sombría", 38, 850, 700,
   [("Fragmento demoníaco", 0.5), ("Esencia oscura densa", 0.3)])
_m("ent_corrupto", "Ent Corrupto", "🌲", 900, 110, 50, "Raíces Aplastantes", 34, 820, 680,
   [("Madera corrupta", 0.5), ("Savia negra", 0.3)])

# --- Tier 6: Cordillera de los Dragones ---
_m("dragon_joven_salvaje", "Dragón Joven Salvaje", "🐲", 1600, 200, 90, "Aliento Draconiano", 50, 2500, 2200,
   [("Escama de dragón", 0.4), ("Colmillo de dragón", 0.3), ("Núcleo draconiano", 0.1)])
_m("arcangel_caido", "Arcángel Caído", "🕊️", 1500, 220, 95, "Juicio Celestial", 55, 2600, 2300,
   [("Pluma corrupta", 0.4), ("Fragmento sagrado", 0.2)])
_m("archidemonio_salvaje", "Archidemonio Salvaje", "👿", 1700, 210, 100, "Abismo Sombrío", 55, 2700, 2400,
   [("Núcleo demoníaco", 0.3), ("Cristal oscuro", 0.2)])

# --- Tier 7: Fosa Abisal ---
_m("kraken_juvenil", "Kraken Juvenil", "🐙", 2600, 250, 120, "Abrazo Tentacular", 55, 4200, 3700,
   [("Tinta abisal", 0.5), ("Ventosa gigante", 0.3)])
_m("serpiente_marina_ancestral", "Serpiente Marina Ancestral", "🌊", 2900, 240, 128, "Torbellino Acuático", 58, 4400, 3900,
   [("Escama marina", 0.5), ("Veneno abisal", 0.3)])
_m("horror_profundidades", "Horror de las Profundidades", "👁️", 3100, 260, 135, "Mirada del Abismo", 60, 4600, 4100,
   [("Ojo abisal", 0.4), ("Esencia del abismo", 0.25)])

# --- Tier 8: Ciudadela en Ruinas ---
_m("golem_ancestral", "Gólem Ancestral", "🗿", 5000, 260, 170, "Puño de Piedra Ancestral", 65, 7500, 6800,
   [("Núcleo de gólem", 0.4), ("Piedra rúnica", 0.3)])
_m("espectro_real", "Espectro Real", "👑", 4700, 300, 175, "Grito del Rey Caído", 70, 7800, 7100,
   [("Corona quebrada", 0.3), ("Esencia real", 0.3)])
_m("guardian_piedra", "Guardián de Piedra", "🛡️", 5600, 250, 165, "Muro Quebrantador", 65, 7700, 7000,
   [("Fragmento de guardián", 0.4), ("Piedra rúnica", 0.3)])

# --- Tier 9: Corazón del Volcán ---
_m("senor_llamas", "Señor de las Llamas", "🔥", 9000, 340, 250, "Erupción Infernal", 80, 13500, 12500,
   [("Núcleo ígneo", 0.4), ("Ceniza ardiente", 0.3)])
_m("fenix_corrupto", "Fénix Corrupto", "🦅", 8700, 360, 255, "Alas de Ceniza", 82, 13800, 12800,
   [("Pluma en llamas", 0.3), ("Esencia corrupta", 0.25)])
_m("titan_magma", "Titán de Magma", "🌋", 10500, 320, 270, "Colapso de Magma", 85, 14200, 13200,
   [("Roca de magma", 0.4), ("Corazón de titán", 0.15)])

# --- Tier 10: Abismo Demoníaco ---
_m("general_demoniaco", "General Demoníaco", "😈", 16500, 400, 360, "Orden de Destrucción", 95, 24500, 22500,
   [("Insignia demoníaca", 0.3), ("Fragmento de abismo", 0.3)])
_m("bestia_abismo", "Bestia del Abismo", "👹", 18000, 380, 375, "Fauces del Vacío", 100, 25200, 23200,
   [("Colmillo abisal", 0.3), ("Esencia del vacío", 0.25)])
_m("verdugo_sombrio", "Verdugo Sombrío", "🗡️", 17200, 410, 380, "Corte Final", 98, 25500, 23500,
   [("Hoja sombría", 0.3), ("Cristal oscuro puro", 0.2)])

# --- Tier 11: Trono del Apocalipsis ---
_m("heraldo_fin", "Heraldo del Fin", "🌑", 28000, 480, 500, "Anuncio del Fin", 115, 43000, 40000,
   [("Fragmento del fin", 0.3), ("Ceniza eterna", 0.2)])
_m("dragon_ancestral_supremo", "Dragón Ancestral Supremo", "🐉", 32000, 500, 530, "Aliento del Apocalipsis", 120, 46000, 43000,
   [("Escama ancestral", 0.3), ("Núcleo draconiano supremo", 0.1)])
_m("avatar_caos", "Avatar del Caos", "☠️", 30000, 510, 520, "Distorsión del Caos", 118, 45000, 42000,
   [("Fragmento del caos", 0.3), ("Esencia primordial", 0.15)])


# ---------------- Zonas del continente ----------------
ZONAS = {}


def _zona(zid, nombre, emoji, descripcion, ep_min, monstruos, mult_exp, mult_ep, cooldown_min):
    ZONAS[zid] = {
        "nombre": nombre, "emoji": emoji, "descripcion": descripcion,
        "ep_min": ep_min, "monstruos": monstruos,
        "mult_exp": mult_exp, "mult_ep": mult_ep,
        "cooldown_min": cooldown_min,  # minutos reales de espera tras explorar esta zona
    }


_zona("linde_jura", "Linde del Bosque de Jura", "🌳",
   "La entrada del bosque. Criaturas débiles, ideal para empezar.",
   0, ["slime_salvaje", "goblin_explorador", "lobezno_jura"], 1.0, 1.0, 2)

_zona("bosque_interior", "Bosque Interior", "🌲",
   "Más adentro del bosque, donde acechan cazadores más fuertes.",
   250, ["orco_merodeador", "arana_gigante_salvaje", "lobo_colmillos_salvaje"], 1.3, 1.3, 5)

_zona("pantano_sombras", "Pantano de las Sombras", "🐊",
   "Un pantano venenoso lleno de criaturas escurridizas.",
   800, ["serpiente_negra_salvaje", "lagarto_pantanero", "insectoide_gigante"], 1.6, 1.6, 10)

_zona("cuevas_heladas", "Cuevas Heladas", "❄️",
   "Cuevas profundas donde sobreviven depredadores y no-muertos.",
   2500, ["tigre_cuchilla_salvaje", "armorsaurio_salvaje", "no_muerto_errante"], 2.0, 2.0, 15)

_zona("guarida_oscura", "Guarida Oscura", "🌑",
   "Territorio de seres de gran poder oscuro. Muy peligroso.",
   6000, ["vampiro_renegado", "demonio_menor_salvaje", "ent_corrupto"], 2.6, 2.6, 25)

_zona("cordillera_dragones", "Cordillera de los Dragones", "🏔️",
   "Las cumbres más altas del continente conocido. Solo los más fuertes sobreviven.",
   15000, ["dragon_joven_salvaje", "arcangel_caido", "archidemonio_salvaje"], 3.5, 3.5, 35)

_zona("fosa_abisal", "Fosa Abisal", "🌊",
   "Un abismo oceánico donde habitan monstruos marinos colosales.",
   40000, ["kraken_juvenil", "serpiente_marina_ancestral", "horror_profundidades"], 5.0, 5.0, 45)

_zona("ciudadela_ruinas", "Ciudadela en Ruinas", "🏚️",
   "Los restos de un reino olvidado, custodiados por guardianes ancestrales.",
   100000, ["golem_ancestral", "espectro_real", "guardian_piedra"], 7.5, 7.5, 55)

_zona("corazon_volcan", "Corazón del Volcán", "🌋",
   "El núcleo de un volcán activo, hogar de seres de fuego puro.",
   250000, ["senor_llamas", "fenix_corrupto", "titan_magma"], 11.0, 11.0, 60)

_zona("abismo_demoniaco", "Abismo Demoníaco", "🩸",
   "Una grieta hacia el reino demoníaco. Muy pocos regresan intactos.",
   500000, ["general_demoniaco", "bestia_abismo", "verdugo_sombrio"], 16.0, 16.0, 60)

_zona("trono_apocalipsis", "Trono del Apocalipsis", "☠️",
   "El límite del continente conocido. Solo leyendas se atreven a llegar aquí.",
   1000000, ["heraldo_fin", "dragon_ancestral_supremo", "avatar_caos"], 24.0, 24.0, 60)


# Ids de zona ordenados de la mas facil a la mas dificil (se calcula una sola vez)
ZONAS_ORDENADAS = sorted(ZONAS, key=lambda zid: ZONAS[zid]["ep_min"])


def zonas_disponibles(ep):
    """Zonas desbloqueadas solo por EP (sin mirar enfriamiento)."""
    return [zid for zid in ZONAS_ORDENADAS if ep >= ZONAS[zid]["ep_min"]]


def zonas_bloqueadas(ep):
    return [zid for zid in ZONAS_ORDENADAS if ep < ZONAS[zid]["ep_min"]]


def elegir_monstruo(zona_id):
    return random.choice(ZONAS[zona_id]["monstruos"])


def tirar_materiales(monstruo_id):
    ganados = {}
    for nombre, prob in MONSTRUOS[monstruo_id]["materiales"]:
        if random.random() < prob:
            ganados[nombre] = ganados.get(nombre, 0) + 1
    return ganados


# ---------------- Calculo de un golpe (jugador o monstruo) ----------------
PROB_FALLO = 0.08
PROB_CRITICO = 0.15
COOLDOWN_ESPECIAL_TURNOS = 3   # turnos de enfriamiento del ataque especial (jugador y monstruo)
PROB_ESPECIAL_MONSTRUO = 0.6   # probabilidad de que el monstruo use especial si no esta en enfriamiento


def calcular_golpe(ataque_base, multiplicador, reduccion_objetivo, factor=1.0, defendiendo_objetivo=False):
    """Devuelve {'fallo':bool, 'critico':bool, 'dano':int}.
    'factor' multiplica el dano base: 1.0 para un ataque normal, 1.8 para el
    Especial generico, o el 'multiplicador' propio de una habilidad ofensiva."""
    if random.random() < PROB_FALLO:
        return {"fallo": True, "critico": False, "dano": 0}
    base = ataque_base * factor * multiplicador
    variacion = random.uniform(0.85, 1.15)
    critico = random.random() < PROB_CRITICO
    if critico:
        variacion *= 1.5
    dano = base * variacion * (1 - reduccion_objetivo)
    if defendiendo_objetivo:
        dano *= 0.5
    return {"fallo": False, "critico": critico, "dano": max(1, round(dano))}


# ---------------- Textos narrativos ----------------
ATAQUES_NORMALES = [
    "{atacante} lanza un golpe directo contra {objetivo}.",
    "{atacante} embiste con fuerza a {objetivo}.",
    "{atacante} ataca sin dudar, buscando el punto débil de {objetivo}.",
    "{atacante} se abalanza y golpea a {objetivo}.",
    "{atacante} conecta un ataque rápido sobre {objetivo}.",
]

ATAQUES_ESPECIALES = [
    "¡{atacante} usa **{tecnica}** contra {objetivo}!",
    "{atacante} concentra su energía y libera **{tecnica}** sobre {objetivo}!",
    "¡{atacante} activa **{tecnica}**! El golpe impacta de lleno en {objetivo}.",
]

MENSAJES_FALLO = [
    "{atacante} intenta golpear a {objetivo}, pero falla.",
    "{objetivo} esquiva por poco el ataque de {atacante}.",
    "{atacante} pierde el equilibrio y no logra golpear a {objetivo}.",
]

MENSAJES_CRITICO = "💥 ¡Golpe crítico!"

# Todos los nombres de materiales que existen (para el autocompletado de /admin_material)
TODOS_LOS_MATERIALES = sorted({nombre for m in MONSTRUOS.values() for nombre, _ in m["materiales"]})

# Precio de venta de cada material en la tienda: 20 monedas de base, escalado por lo dificil
# que es la zona donde aparece (si sale en varias zonas, se usa el precio mas alto).
PRECIOS_MATERIALES = {}
for _zid, _z in ZONAS.items():
    for _mid in _z["monstruos"]:
        for _nombre, _prob in MONSTRUOS[_mid]["materiales"]:
            _precio = round(20 * _z["mult_exp"])
            if _precio > PRECIOS_MATERIALES.get(_nombre, 0):
                PRECIOS_MATERIALES[_nombre] = _precio

# Rareza de cada material, para la forja: a que tier de arma/armadura puede aspirar.
# Se agrupan las 11 zonas en 4 bloques de dificultad creciente.
ORDEN_RAREZA_FORJA = {"comun": 0, "extra": 1, "unica": 2, "definitiva": 3}
_TIER_ZONA_MATERIAL = {
    "linde_jura": "comun", "bosque_interior": "comun", "pantano_sombras": "comun",
    "cuevas_heladas": "extra", "guarida_oscura": "extra", "cordillera_dragones": "extra",
    "fosa_abisal": "unica", "ciudadela_ruinas": "unica", "corazon_volcan": "unica",
    "abismo_demoniaco": "definitiva", "trono_apocalipsis": "definitiva",
}
RAREZA_MATERIALES = {}
for _zid, _z in ZONAS.items():
    _tier = _TIER_ZONA_MATERIAL[_zid]
    for _mid in _z["monstruos"]:
        for _nombre, _prob in MONSTRUOS[_mid]["materiales"]:
            _actual = RAREZA_MATERIALES.get(_nombre)
            if _actual is None or ORDEN_RAREZA_FORJA[_tier] > ORDEN_RAREZA_FORJA[_actual]:
                RAREZA_MATERIALES[_nombre] = _tier
